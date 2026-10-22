from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from wagtailcache.cache import clear_cache

from .models import StaffProfileAccess


def invalidate_public_contacts():
    transaction.on_commit(clear_cache)
    transaction.on_commit(cache.clear)


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def registered_email_changed(sender, instance, raw=False, **kwargs):
    if not raw and StaffProfileAccess.objects.filter(user_id=instance.pk).exists():
        invalidate_public_contacts()


@receiver(post_save, sender=StaffProfileAccess)
def profile_account_linked(sender, instance, created=False, raw=False, **kwargs):
    if not raw and created:
        invalidate_public_contacts()


@receiver(post_delete, sender=StaffProfileAccess)
def profile_account_removed(sender, instance, **kwargs):
    invalidate_public_contacts()
