from django.db import models
from django.contrib.auth.models import User
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType

class ActivityLog(models.Model):
    ACTION_CHOICES = (
        ("create", "Create"),
        ("update", "Update"),
        ("delete", "Delete"),
    )

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.CharField(max_length=50)
    content_object = GenericForeignKey("content_type", "object_id")

    action = models.CharField(max_length=10, choices=ACTION_CHOICES)

    changes = models.JSONField(null=True, blank=True)
    performed_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "activity_log"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.content_type} {self.object_id} {self.action}"
