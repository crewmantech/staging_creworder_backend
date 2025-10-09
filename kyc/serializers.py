from datetime import datetime, timedelta
import random
import re
from rest_framework import serializers
from kyc.models import KYC, GSTState, OTPModel


class KYCSerializer(serializers.ModelSerializer):
    class Meta:
        model = KYC
        fields = '__all__'
        read_only_fields = ['id']

    def validate_pan_card_number(self, value):
        """
        Validate PAN Card Number format (5 letters + 4 digits + 1 letter)
        e.g. 'ABCDE1234F'
        """
        if not re.match(r'^[A-Z]{5}[0-9]{4}[A-Z]{1}$', value):
            raise serializers.ValidationError("Invalid PAN card number format.")
        return value

    def validate_gst_number(self, value):
        """
        Validate GST Number format (15 characters)
        e.g. '27ABCDE1234F1Z5'
        """
        if not re.match(r'\d{2}[A-Z]{5}\d{4}[A-Z]{1}[A-Z\d]{1}[Z]{1}[A-Z\d]{1}', value):
            raise serializers.ValidationError("Invalid GST number format.")
        return value

    def validate_tan_number(self, value):
        """
        Validate TAN Number format (10 characters)
        e.g. 'ABCDE1234F'
        """
        if not re.match(r'^[A-Z]{4}[0-9]{4}[A-Z]{1}$', value):
            raise serializers.ValidationError("Invalid TAN number format.")
        return value
    def validate(self, data):
        """
        Ensure the PAN number is present in the GST number.
        """
        pan_card_number = data.get("pan_card_number")
        gst_number = data.get("gst_number")

        if pan_card_number and gst_number:
            extracted_pan = gst_number[2:12]  # Extract PAN from GST number
            if extracted_pan != pan_card_number:
                raise serializers.ValidationError(
                    {"gst_number": "The GST number and PAN card number Not match"}
                )

        return data
    

class GSTStateSerializer(serializers.ModelSerializer):
    class Meta:
        model = GSTState
        fields = ['id', 'state_name', 'state_code']
        read_only_fields = ['id']

class OTPSerializer(serializers.ModelSerializer):
    class Meta:
        model = OTPModel
        fields = ['phone_number', 'otp', 'expiration_time']

    def create(self, validated_data):
        # Generate OTP on creation
        otp = str(random.randint(1000, 9999))
        expiration_time = datetime.now() + timedelta(minutes=5)

        # Create the OTP instance
        otp_instance = OTPModel.objects.create(
            otp=otp,
            expiration_time=expiration_time,
            **validated_data
        )

        # Send OTP to the phone number
        send_otp_to_number(validated_data['phone_number'], otp)

        return otp_instance