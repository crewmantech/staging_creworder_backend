from rest_framework import serializers
from .models import (
    CallActivity,
    CallLead,
    CallLog,
    CallRecording,
    CloudTelephonyVendor, 
    CloudTelephonyChannel, 
    CloudTelephonyChannelAssign,
    SecretKey, 
    UserMailSetup
)

class CloudTelephonyVendorSerializer(serializers.ModelSerializer):
    class Meta:
        model = CloudTelephonyVendor
        fields = '__all__'
        read_only_fields = ['id']
        
class CloudTelephonyChannelSerializer(serializers.ModelSerializer):
    cloudtelephony_vendor_name = serializers.CharField(source='cloudtelephony_vendor.name', read_only=True)
    cloudtelephony_vendor_image = serializers.ImageField(source='cloudtelephony_vendor.image', read_only=True)

    # branch = serializers.PrimaryKeyRelatedField(read_only=True)
    company = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = CloudTelephonyChannel
        fields = '__all__'
        read_only_fields = ['id']


class CloudTelephonyChannelAssignSerializer(serializers.ModelSerializer):
    company = serializers.PrimaryKeyRelatedField(read_only=True)
    vendor_name = serializers.SerializerMethodField()
    class Meta:
        model = CloudTelephonyChannelAssign
        fields = "__all__"
    def get_vendor_name(self, obj):
        if obj.cloud_telephony_channel and obj.cloud_telephony_channel.cloudtelephony_vendor:
            return obj.cloud_telephony_channel.cloudtelephony_vendor.name
        return None
    def validate(self, data):
        instance = self.instance
        user = data.get("user")
        company = data.get("company")
        type_ = data.get("type")
        is_active = data.get("is_active")

        # Call Agent rule
        if type_ == 1:
            qs = CloudTelephonyChannelAssign.objects.filter(
                user=user,
                company=company,
                type=1,
            )
            if instance:
                qs = qs.exclude(id=instance.id)

            if qs.exists():
                raise serializers.ValidationError(
                    {"error": "Only one Call Agent channel allowed per user"}
                )

        # Monitoring active rule
        if type_ == 2 and is_active:
            qs = CloudTelephonyChannelAssign.objects.filter(
                user=user,
                company=company,
                type=2,
                is_active=True,
            )
            if instance:
                qs = qs.exclude(id=instance.id)

            if qs.exists():
                raise serializers.ValidationError(
                    {"error": "Only one Monitoring channel can be active"}
                )

        return data


class UserMailSetupSerializer(serializers.ModelSerializer):
    branch_name = serializers.CharField(source='branch.name', read_only=True)
    company_name = serializers.CharField(source='company.name', read_only=True)

    class Meta:
        model = UserMailSetup
        fields = '__all__'
        extra_kwargs = {
            'password': {'write_only': True}  # Password security
        }


class CallRecordingInputSerializer(serializers.Serializer):
    secret_key = serializers.CharField(required=True)
    recording_url = serializers.URLField(required=True)
    agent_username = serializers.CharField(required=True)
    datetime = serializers.DateTimeField(required=True)
    duration = serializers.CharField(required=True)
    number = serializers.CharField(required=True)


class CallRecordingModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = CallRecording
        fields = "__all__"

class SecretKeySerializer(serializers.ModelSerializer):
    vendor_name = serializers.CharField(source="cloudtelephony_vendor.name", read_only=True)

    class Meta:
        model = SecretKey
        fields = [
            "id",
            "cloudtelephony_vendor",
            "vendor_name",
            "secret_key",
            "is_active",
            "created_at",
            "deactivated_at"
        ]
        read_only_fields = ["id", "secret_key", "created_at", "deactivated_at"]

class CloudTelephonyChannelAssignCSVSerializer(serializers.ModelSerializer):
    company = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = CloudTelephonyChannelAssign
        fields = "__all__"
        extra_kwargs = {
            "priority": {"required": False},
            "campangin_name": {"required": False, "allow_null": True},
            "agent_username": {"required": False, "allow_null": True},
            "agent_password": {"required": False, "allow_null": True},
            "agent_id": {"required": False, "allow_null": True},
            "camp_id": {"required": False, "allow_null": True},
            "other": {"required": False, "allow_null": True},
        }
class CallLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = CallLog
        fields = "__all__"


class CallActivitySerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(
        source="updated_by.username",
        read_only=True
    )
    class Meta:
        model = CallActivity
        fields = "__all__"


class CallLeadSerializer(serializers.ModelSerializer):
    activities = CallActivitySerializer(many=True)
    new_number = serializers.SerializerMethodField()

    class Meta:
        model = CallLead
        fields = "__all__"

    def get_new_number(self, obj):
        return False