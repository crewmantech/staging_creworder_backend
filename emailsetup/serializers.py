from rest_framework import serializers
from .models import AgentAuthentication, EmailTemplate,AgentReport
from phonenumber_field.serializerfields import PhoneNumberField
class EmailTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmailTemplate
        fields = '__all__'

class AgentAuthenticationSerializer(serializers.ModelSerializer):
    phone = PhoneNumberField(region="IN")
    company_name = serializers.SerializerMethodField()
    branch_name = serializers.SerializerMethodField()

    class Meta:
        model = AgentAuthentication
        fields = '__all__'
        # Add extra fields:
        extra_fields = ['company_name', 'branch_name']

    def get_company_name(self, obj):
        return obj.company.name if obj.company else None

    def get_branch_name(self, obj):
        return obj.branch.name if obj.branch else None


class AgentReportSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = AgentReport
        fields = '__all__'