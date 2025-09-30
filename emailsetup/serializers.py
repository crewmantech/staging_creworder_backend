from rest_framework import serializers
from .models import AgentAuthentication, EmailTemplate,AgentReport
from phonenumber_field.serializerfields import PhoneNumberField
class EmailTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmailTemplate
        fields = '__all__'

class AgentAuthenticationSerializer(serializers.ModelSerializer):
    phone = PhoneNumberField(region="IN")  # Ensures valid phone format

    class Meta:
        model = AgentAuthentication
        fields = '__all__'


class AgentReportSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = AgentReport
        fields = '__all__'