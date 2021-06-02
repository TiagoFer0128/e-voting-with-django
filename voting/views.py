from django.shortcuts import render, redirect, reverse
from account.views import account_login
from .models import Position, Candidate, Voter, Votes
from django.http import JsonResponse
from django.utils.text import slugify
from django.contrib import messages
from django.conf import settings
import requests
import json
# Create your views here.


def index(request):
    if not request.user.is_authenticated:
        return account_login(request)
    context = {}
    # return render(request, "voting/login.html", context)


def fetch_ballot(request):
    positions = Position.objects.order_by('priority').all()
    output = ""
    candidates_data = ""
    num = 1
    # return None
    for position in positions:
        name = position.name
        position_name = slugify(name)
        if position.max_vote > 1:
            instruction = "You may select up to " + \
                str(position.max_vote) + " candidates"
            input_box = '<input type="checkbox" class="flat-red ' + \
                position_name+'" name="' + \
                position_name+"[]" + '">'
        else:
            instruction = "Select only one candidate"
            input_box = '<input type="radio" class="flat-red ' + \
                position_name+'" name="'+position_name+'">'
        candidates = Candidate.objects.filter(position=position)
        for candidate in candidates:
            image = "/media/" + str(candidate.photo)
            candidates_data = candidates_data + '<li>' + input_box + '<button class="btn btn-primary btn-sm btn-flat clist"><i class="fa fa-search"></i> Platform</button><img src="' + \
                image+'" height="100px" width="100px" class="clist"><span class="cname clist">' + \
                candidate.fullname+'</span></li>'
        up = ''
        if position.priority == 1:
            up = 'disabled'
        down = ''
        if position.priority == positions.count():
            down = 'disabled'
        output = output + f"""<div class="row">	<div class="col-xs-12"><div class="box box-solid" id="{position.id}">
             <div class="box-header with-border">
            <h3 class="box-title"><b>{name}</b></h3>
           
            <div class="pull-right box-tools">
            <button type="button" class="btn btn-default btn-sm moveup" data-id="{position.id}" {up}><i class="fa fa-arrow-up"></i> </button>
            <button type="button" class="btn btn-default btn-sm movedown" data-id="{position.id}" {down}><i class="fa fa-arrow-down"></i></button>
            </div>
            </div>
            <div class="box-body">
            <p>{instruction}
            <span class="pull-right">
            <button type="button" class="btn btn-success btn-sm btn-flat reset" data-desc="{position_name}"><i class="fa fa-refresh"></i> Reset</button>
            </span>
            </p>
            <div id="candidate_list">
            <ul>
            {candidates_data}
            </ul>
            </div>
            </div>
            </div>
            </div>
            </div>
        """
        position.priority = num
        position.save()
        num = num + 1
        candidates_data = ''
    return JsonResponse(output, safe=False)


def generate_otp():
    """Link to this function
    https://www.codespeedy.com/otp-generation-using-random-module-in-python/
    """
    import random as r
    otp = ""
    for i in range(r.randint(5, 8)):
        otp += str(r.randint(1, 9))
    return otp


def dashboard(request):
    user = request.user
    # * Check if this voter has been verified
    if user.voter.otp is None or user.voter.verified == 0:
        return redirect(reverse('voterVerify'))
    else:
        if user.voter.voted == 1:  # * User has voted
            pass
        else:
            return None


def verify(request):
    voter = request.user.voter
    if voter.otp_sent >= 3:
        messages.error(
            request, "You have requested OTP three times. You cannot do this again! Please enter previously sent OTP")
    else:
        msg = resend_otp(request)
        messages.info(request, msg)
    context = {
        'page_title': 'OTP Verification'
    }
    return render(request, "voting/voter/verify.html", context)


def resend_otp(request):
    """API For SMS
    I used https://www.multitexter.com/ API to send SMS
    You might not want to use this or this service might not be available in your Country
    For quick and easy access, Toggle the SEND_OTP from True to False in settings.py
    """
    user = request.user
    if settings.SEND_OTP:
        voter = user.voter
        phone = voter.phone
        # Now, check if an OTP has been generated previously for this voter
        otp = voter.otp
        if otp is None:
            # Generate new OTP
            otp = generate_otp()
            voter.otp = otp
            voter.save()
        try:
            msg = "Dear " + str(user) + ", kindly use " + \
                str(otp) + " as your OTP"
            message_is_sent = send_sms(phone, msg)
            if message_is_sent:  # * OTP was sent successfully
                # Update how many OTP has been sent to this voter
                # Limited to Three so voters don't exhaust OTP balance
                voter.otp_sent = voter.otp_sent + 1
                voter.save()

                response = "OTP has been sent to your phone number. Please provide it in the box provided below"
            else:
                response = "OTP not sent. Please try again"
        except Exception as e:
            response = "OTP could not be sent." + str(e)

            # * Send OTP
    else:
        #! Update all Voters record and set OTP to 0000
        #! Bypass OTP verification by updating verified to 1
        #! Redirect voters to ballot page
        Voter.objects.all().update(otp="0000", verified=1)
        response = "Kindly cast your vote"
    return response


def send_sms(phone_number, msg):
    """Read More
    https://www.multitexter.com/developers
    """
    import requests
    import os
    import json
    response = ""
    email = os.environ.get('SMS_EMAIL')
    password = os.environ.get('SMS_PASSWORD')
    if email is None or password is None:
        raise Exception("Email/Password cannot be Null")
    url = "https://app.multitexter.com/v2/app/sms"
    data = {"email": email, "password": password, "message": msg,
            "sender_name": "OTP", "recipients": phone_number, "forcednd": 1}
    headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
    r = requests.post(url, data=json.dumps(data), headers=headers)
    response = r.json()
    status = response.get('status', 0)
    if str(status) == '1':
        return True
    else:
        return False
