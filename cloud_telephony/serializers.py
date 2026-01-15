from rest_framework import serializers
from .models import (
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

    class Meta:
        model = CloudTelephonyChannelAssign
        fields = '__all__' 

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