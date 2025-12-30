from rest_framework import serializers
from .models import ActivityLog

class ActivityLogSerializer(serializers.ModelSerializer):
    module = serializers.SerializerMethodField()

    class Meta:
        model = ActivityLog
        fields = [
            "id",
            "module",
            "object_id",
            "action",
            "changes",
            "performed_by",
            "created_at",
        ]

    def get_module(self, obj):
        return obj.content_type.model
