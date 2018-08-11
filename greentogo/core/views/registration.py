from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.template.defaultfilters import pluralize
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.contrib.sites.shortcuts import get_current_site

from core.models import Location, Subscription, LocationTag, User
from core.forms import UserSignupForm


from django.contrib.admin.views.decorators import staff_member_required
from datetime import date




def registration_form(request):
    if request.method == 'POST':
        form = UserSignupForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = True
            user.create_stripe_customer()
            user.email = form.cleaned_data.get('email')
            current_site = get_current_site(request)
            communityBoxesCheckedIn = int((LocationTag.objects.all()).count()/2) + 100
            to_email = form.cleaned_data.get('email')
            message_data = {
                'user': user,
                'communityBoxesCheckedIn': communityBoxesCheckedIn,
                'domain': current_site.domain,
            }
            welcome_message_txt = render_to_string('registration/welcome_message.txt', message_data)
            welcome_message_html = render_to_string('registration/welcome_message.html', message_data)
            user.save()
            email = EmailMultiAlternatives(
                subject='Welcome to GreenToGo!',
                body=welcome_message_txt,
                from_email='greentogo@app.durhamgreentogo.com',
                to=[to_email],
                reply_to=["amy@durhamgreentogo.com"]
            )
            email.attach_alternative(welcome_message_html, "text/html")
            email.send()
            new_user = authenticate(username=form.cleaned_data['username'],
                                    password=form.cleaned_data['password1'],
                                    )
            login(request, new_user)
            messages.add_message(request, messages.INFO, "Your account has been registered successfully, {username}! Now you just need a subscription in order to start using GreenToGo. Your email address is {email}. If this is incorrect, change your email in 'My Settings'".format(username=form.cleaned_data['username'], email=form.cleaned_data['email']))
            return redirect('/subscriptions/new/', {'newly_registered_user':{
                'new':True,
                'username':form.cleaned_data['username'],
                'email':form.cleaned_data['email']
            }})
    else:
        form = UserSignupForm()
    return render(request, "registration/registration_form.html", {'form':form})

@staff_member_required()
def send_the_email(request):
    if request.method == 'POST':
        try:
            dt = date(2018, 8, 15)
            # subscriptions = Subscription.objects.filter(stripe_id__isnull=True, ends_at__month__gte=dt.month)
            subscriptions = Subscription.objects.filter(user_id=38)
            for sub in subscriptions:
                expireDate = sub.ends_at.date()
                print(expireDate)
                message_data = {
                    'expire': expireDate
                }
                txt = render_to_string('registration/sub_expire.txt', message_data)
                html = render_to_string('registration/sub_expire.html', message_data)
                email = EmailMultiAlternatives(
                    subject='GreenToGo Subscription Expiring Soon!',
                    body=txt,
                    from_email='amy@durhamgreentogo.com',
                    to=[sub.user.email],
                    reply_to=["amy@durhamgreentogo.com"]
                )
                email.attach_alternative(html, "text/html")
                email.send()
        except Exception as ex:
            return render(request, "registration/privacy.html")
    return render(request, "registration/send_email.html")

def privacy(request):
    return render(request, "registration/privacy.html")

