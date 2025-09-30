from rest_framework import serializers
from .models import *

class ShipmentVendorSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShipmentVendor
        fields = ['id', 'name', 'image']

class ShipmentSerializer(serializers.ModelSerializer):
    shipment_vendor = ShipmentVendorSerializer(read_only=True)  # For retrieving full data
    shipment_vendor_id = serializers.PrimaryKeyRelatedField(
        queryset=ShipmentVendor.objects.all(), source="shipment_vendor", write_only=True
    )  # For saving only the ID
    company_id = serializers.CharField(read_only=True)
    branch_id = serializers.CharField(read_only=True)
    class Meta:
        model = ShipmentModel
        fields = '__all__'
        extra_fields = ['shipment_vendor_id', 'company_id', 'branch_id']# Returns all fields
# class ShipmentSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = ShipmentModel
#         fields = '__all__'  

class CourierServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = CourierServiceModel
        fields = '__all__'  