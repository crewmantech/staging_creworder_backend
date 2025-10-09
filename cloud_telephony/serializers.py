from rest_framework import serializers
from .models import (
    CloudTelephonyVendor, 
    CloudTelephonyChannel, 
    CloudTelephonyChannelAssign, 
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
