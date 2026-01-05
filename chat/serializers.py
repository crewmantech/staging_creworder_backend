from rest_framework import serializers

from follow_up.models import Follow_Up
from .models import Chat,ChatSession,Group,GroupDetails, Notification
class ChatSerializer(serializers.ModelSerializer):
    class Meta:
        model = Chat
        fields = '__all__'

class ChatSesstionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatSession
        fields = '__all__'

class ChatGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = '__all__'

class ChatGroupDetailsSerializer(serializers.ModelSerializer):
    class Meta:
        model = GroupDetails
        fields = '__all__'  # or specify the fields you want to include


class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = '__all__'
class GroupDetailsSerializer(serializers.ModelSerializer):
    class Meta:
        model = GroupDetails
        fields = '__all__'

class NotificationSerializer(serializers.ModelSerializer):
    followup = serializers.PrimaryKeyRelatedField(
        queryset=Follow_Up.objects.all(),
        required=False,
        allow_null=True
    )

    class Meta:
        model = Notification
        fields = [
            "id",
            "user",
            "message",
            "is_read",
            "created_at",
            "url",
            "notification_type",
            "followup",
        ]
        read_only_fields = ["id", "created_at"]

        # 🔥 CRITICAL LINE — disables DRF auto unique validator
        validators = []

    def validate(self, attrs):
        """
        Only followup_reminder requires followup.
        Chat / Group notifications NEVER require it.
        """
        if attrs.get("notification_type") == "followup_reminder":
            if not attrs.get("followup"):
                raise serializers.ValidationError(
                    {"followup": "This field is required for followup reminders."}
                )
        else:
            attrs["followup"] = None

        return attrs
