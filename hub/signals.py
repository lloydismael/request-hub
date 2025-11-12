from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from .models import Notification, Request


@receiver(pre_save, sender=Request)
def cache_previous_status(sender, instance, **kwargs):
    if not instance.pk:
        instance._previous_status = None
        return
    try:
        previous = sender.objects.get(pk=instance.pk)
        instance._previous_status = previous.status
    except sender.DoesNotExist:
        instance._previous_status = None


@receiver(post_save, sender=Request)
def notify_on_completion(sender, instance, created, **kwargs):
    previous_status = getattr(instance, "_previous_status", None)
    if instance.status == Request.Status.COMPLETED and previous_status != Request.Status.COMPLETED:
        code = instance.reference_code or f"REQ-{instance.pk:05d}"
        Notification.objects.create(
            recipient=instance.requestor,
            related_request=instance,
            message=f"Request {code} has been completed.",
        )
        if instance.engineer:
            Notification.objects.create(
                recipient=instance.engineer,
                related_request=instance,
                message=f"Request {code} closed by admin.",
            )


@receiver(post_save, sender=Request)
def notify_on_assignment(sender, instance, created, **kwargs):
    if not instance.engineer:
        return
    previous_engineer_id = getattr(instance, "_previous_engineer_id", None)
    if created or previous_engineer_id != instance.engineer_id:
        code = instance.reference_code or f"REQ-{instance.pk:05d}"
        Notification.objects.create(
            recipient=instance.engineer,
            related_request=instance,
            message=f"You have been assigned to request {code}",
        )


@receiver(pre_save, sender=Request)
def cache_previous_engineer(sender, instance, **kwargs):
    if not instance.pk:
        instance._previous_engineer_id = None
        return
    try:
        previous = sender.objects.get(pk=instance.pk)
        instance._previous_engineer_id = previous.engineer_id
    except sender.DoesNotExist:
        instance._previous_engineer_id = None