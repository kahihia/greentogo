from django.conf import settings
from django.contrib.auth import hashers
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.signals import user_logged_in
from django.contrib.sites.models import Site
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.core.mail import EmailMessage
from django.core.validators import RegexValidator
from django.db import models
from django.db.models import Case, Q, Sum, When
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.text import slugify

import shortuuid
from django_geocoder.wrapper import get_cached as geocode

from core.stripe import stripe


def get_plan_price(plan):
    return "${:.02f}".format(plan.amount / 100)


def plan_to_dict(plan):
    return {
        'stripe_id': plan.stripe_id,
        'name': plan.name,
        'amount': plan.amount,
        'display_price': get_plan_price(plan),
        'boxes': plan.number_of_boxes
    }


def get_plans():
    plans = Plan.objects.order_by('amount')
    return [plan_to_dict(plan) for plan in plans]


class User(AbstractUser):
    name = models.CharField(max_length=255, blank=True, null=True)
    email = models.EmailField(
        verbose_name='Email address',
        max_length=255,
        unique=True,
    )

    def __str__(self):
        return self.name or self.username

    def has_active_subscription(self):
        return self.subscriptions.active().count() > 0


class CannotChangeException(Exception):
    """Raise when model field should not change after initial creation."""


class Plan(models.Model):
    name = models.CharField(max_length=255, unique=True)
    available = models.BooleanField(default=True)
    amount = models.PositiveIntegerField(help_text="Amount in cents.")
    number_of_boxes = models.PositiveIntegerField()
    stripe_id = models.CharField(max_length=255, unique=True, blank=True, null=True, editable=False)

    @classmethod
    def from_db(cls, db, field_names, values):
        instance = super().from_db(db, field_names, values)
        instance._loaded_values = dict(zip(field_names, values))
        return instance

    def is_changed(self, field_name):
        old_value = self._loaded_values[field_name]
        new_value = getattr(self, field_name)
        return not old_value == new_value

    def __str__(self):
        return self.name

    def _gen_id(self, force=False):
        if force or not self.stripe_id:
            shortuuid.set_alphabet("23456789ABCDEFGHJKLMNPQRSTUVWXYZ")
            stripe_id = slugify(self.name) + shortuuid.uuid()[:6]
            while Plan.objects.filter(stripe_id=stripe_id).count() > 0:
                stripe_id = slugify(self.name) + "-" + shortuuid.uuid()[:6]
            return stripe_id

    def save(self, *args, **kwargs):
        if self.stripe_id:
            if self.is_changed('amount'):
                raise CannotChangeException({"model": self, "field": "amount"})
            if self.is_changed('name'):
                stripe_plan = stripe.Plan.retrieve(self.stripe_id)
                stripe_plan.name = self.name
                stripe_plan.save()
        else:
            self.stripe_id = self._gen_id()
            plan = stripe.Plan.create(
                name=self.name,
                id=self.stripe_id,
                interval="year",
                currency="usd",
                amount=self.amount,
            )
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        self.available = False
        self.save()


class UnclaimedSubscription(models.Model):
    email = models.EmailField(unique=True)
    plan = models.ForeignKey(Plan)
    claimed = models.BooleanField(default=False)

    def __str__(self):
        return "{} - {}".format(self.email, self.plan)


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def claim_subscriptions(sender, instance, created, **kwargs):
    if created:
        unsub = UnclaimedSubscription.objects.filter(email=instance.email, claimed=False)
        for unsub in unsubs:
            subscription, _ = Subscription.objects.get_or_create(user=instance, plan=unsub.plan)
            unsub.claimed = True
            unsub.save()


@receiver(user_logged_in)
def claim_subscriptions_on_login(sender, user, request, **kwargs):
    unsubs = UnclaimedSubscription.objects.filter(email=user.email, claimed=False)
    for unsub in unsubs:
        subscription, _ = Subscription.objects.get_or_create(user=user, plan=unsub.plan)
        unsub.claimed = True
        unsub.save()


class SubscriptionQuerySet(models.QuerySet):
    def active(self):
        return self.filter(Q(ends_at=None) | Q(ends_at__gt=timezone.now()))

    def owned_by(self, user):
        return self.filter(user=user)


class Subscription(models.Model):
    objects = SubscriptionQuerySet.as_manager()

    name = models.CharField(max_length=255, null=True, blank=True)
    user = models.ForeignKey(User, related_name="subscriptions")
    plan = models.ForeignKey(Plan, null=True)
    starts_at = models.DateTimeField(default=timezone.now)
    ends_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return "{} - {}".format(self.user.name, self.display_name)

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('subscription', kwargs={"sub_id": self.id})

    @property
    def display_name(self):
        return self.name or self.plan_display()

    def plan_display(self):
        if self.plan:
            return self.plan.name
        return "None"

    @property
    def number_of_boxes(self):
        if self.plan:
            return self.plan.number_of_boxes

        return 0

    @property
    def max_boxes(self):
        return self.number_of_boxes

    @property
    def available_boxes(self):
        boxes_checked_out = LocationTag.objects.filter(subscription=self).aggregate(
            checked_out=Sum(
                Case(
                    When(location__service=Location.CHECKOUT, then=1),
                    When(location__service=Location.CHECKIN, then=-1),
                    default=1,
                    output_field=models.IntegerField()
                )
            )
        )['checked_out']
        return self.number_of_boxes - (boxes_checked_out or 0)

    def boxes_checked_out(self):
        return self.number_of_boxes - self.available_boxes

    def can_checkout(self):
        return self.available_boxes > 0

    def can_checkin(self):
        return self.available_boxes < self.number_of_boxes

    def can_tag_location(self, location):
        if location.service == Location.CHECKIN:
            return self.can_checkin()
        else:
            return self.can_checkout()

    def tag_location(self, location):
        tag = LocationTag.objects.create(subscription=self, location=location)
        return tag


class Location(models.Model):
    CHECKIN = 'IN'
    CHECKOUT = 'OUT'
    SERVICE_CHOICES = ((CHECKIN, 'Check in'), (CHECKOUT, 'Check out'), )

    code = models.CharField(max_length=6, unique=True)
    service = models.CharField(max_length=25, choices=SERVICE_CHOICES)
    name = models.CharField(max_length=255)
    address = models.CharField(max_length=1023)
    latitude = models.FloatField(blank=True, null=True)
    longitude = models.FloatField(blank=True, null=True)

    def __str__(self):
        return "{} - {}".format(self.name, self.service)

    def save(self, *args, **kwargs):
        self._set_code()
        self._geocode()
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('location', kwargs={"location_code": self.code})

    def _set_code(self, force=False):
        if force or not self.code:
            shortuuid.set_alphabet("23456789ABCDEFGHJKLMNPQRSTUVWXYZ")
            code = shortuuid.uuid()[:6]
            while Location.objects.filter(code=code).count() > 0:
                code = shortuuid.uuid()[:6]
            self.code = code

    def _geocode(self):
        if self.address and self.latitude is None or self.longitude is None:
            result = geocode(self.address, provider='google')
            if result.latlng:
                lat, lng = result.latlng
                self.latitude = lat
                self.longitude = lng

    def add_qrcode_to_pdf(self, pdf):
        import qrcode
        from reportlab.lib.units import inch

        width, height = pdf._pagesize

        qr = qrcode.QRCode(box_size=10)
        qr.add_data(settings.URL + self.get_absolute_url())
        qr.make(fit=True)
        img = qr.make_image(fill_color="white", back_color="black")

        image_y = 11 * inch - img.pixel_size
        text_y = image_y + 15
        font_size = 14

        pdf.drawInlineImage(img, x=(width - img.pixel_size) / 2, y=image_y)
        pdf.setFont("Helvetica-Bold", font_size)
        pdf.drawCentredString(width / 2, text_y, self.code)
        pdf.setFont("Helvetica", font_size)
        pdf.drawCentredString(
            width / 2, text_y - (font_size + 2), "{} - {}".format(self.name, self.service)
        )
        pdf.showPage()
        return pdf


class LocationTag(models.Model):
    subscription = models.ForeignKey(Subscription)
    location = models.ForeignKey(Location)
    created_at = models.DateTimeField(auto_now_add=True)


class Restaurant(models.Model):
    name = models.CharField(max_length=255)
    address = models.CharField(max_length=1023)
    latitude = models.FloatField(blank=True, null=True)
    longitude = models.FloatField(blank=True, null=True)
    phase = models.PositiveIntegerField(default=1)

    def save(self, *args, **kwargs):
        if self.address and self.latitude is None or self.longitude is None:
            result = geocode(self.address, provider='google')
            lat, lng = result.latlng
            self.latitude = lat
            self.longitude = lng
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name
