from django.db.models.signals import pre_save, post_save, post_delete
from django.dispatch import receiver
from django.contrib.contenttypes.models import ContentType

from follow_up.models import Appointment, Follow_Up
from lead_management.models import Lead
from .models import ActivityLog


TRACK_MODELS = (Lead, Appointment, Follow_Up)


def get_changes(old, new):
    changes = {}
    for field in new._meta.fields:
        name = field.name
        old_val = getattr(old, name, None)
        new_val = getattr(new, name, None)
        if old_val != new_val:
            changes[name] = {
                "old": str(old_val),
                "new": str(new_val),
            }
    return changes


@receiver(pre_save)
def log_update(sender, instance, **kwargs):
    if sender not in TRACK_MODELS:
        return

    if not instance.pk:
        return

    try:
        old_instance = sender.objects.get(pk=instance.pk)
    except sender.DoesNotExist:
        return

    changes = get_changes(old_instance, instance)
    if changes:
        ActivityLog.objects.create(
            content_type=ContentType.objects.get_for_model(sender),
            object_id=str(instance.pk),
            action="update",
            changes=changes,
            performed_by=getattr(instance, "updated_by", None),
        )


@receiver(post_save)
def log_create(sender, instance, created, **kwargs):
    if sender not in TRACK_MODELS:
        return

    if created:
        ActivityLog.objects.create(
            content_type=ContentType.objects.get_for_model(sender),
            object_id=str(instance.pk),
            action="create",
            performed_by=getattr(instance, "created_by", None),
        )


@receiver(post_delete)
def log_delete(sender, instance, **kwargs):
    if sender not in TRACK_MODELS:
        return

    ActivityLog.objects.create(
        content_type=ContentType.objects.get_for_model(sender),
        object_id=str(instance.pk),
        action="delete",
    )
