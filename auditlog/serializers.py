from rest_framework import serializers
from .models import ActivityLog

class ActivityLogSerializer(serializers.ModelSerializer):
    module = serializers.SerializerMethodField()
    performed_by_name = serializers.SerializerMethodField()
    performed_by_id = serializers.SerializerMethodField()
    created_time = serializers.SerializerMethodField()  # only time (optional)

    class Meta:
        model = ActivityLog
        fields = [
            "id",
            "module",
            "object_id",
            "action",
            "changes",
            "performed_by_id",
            "performed_by_name",
            "created_at",     # full datetime (keep if needed)
            "created_time",   # only time
        ]

    def get_module(self, obj):
        return obj.content_type.model

    def get_performed_by_name(self, obj):
        """
        Returns full name of the user.
        Falls back to username/email if name not available.
        """
        if obj.performed_by:
            full_name = obj.performed_by.get_full_name()
            return full_name if full_name else obj.performed_by.username
        return None

    def get_performed_by_id(self, obj):
        return obj.performed_by.id if obj.performed_by else None

    def get_created_time(self, obj):
        """
        Returns only time (HH:MM AM/PM)
        """
        return obj.created_at.strftime("%I:%M %p") if obj.created_at else None

