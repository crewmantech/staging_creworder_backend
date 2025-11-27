from rest_framework import serializers
from .models import AgentAuthentication, AgentAuthenticationNew, AgentUserMapping, EmailTemplate,AgentReport
from phonenumber_field.serializerfields import PhoneNumberField
from django.contrib.auth.models import User
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


class UserMiniSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email"]


class AgentAuthenticationNewSerializer(serializers.ModelSerializer):
    users = UserMiniSerializer(many=True, read_only=True)
    company_name = serializers.SerializerMethodField()
    branch_name = serializers.SerializerMethodField()
    user_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False
    )

    class Meta:
        model = AgentAuthentication
        fields = [
            "id",
            "company",
            "branch",
            "email",
            "phone",
            "users",
            "user_ids",
        ]
        extra_fields = ['company_name', 'branch_name']
    def create(self, validated_data):
        user_ids = validated_data.pop("user_ids", [])
        instance = AgentAuthenticationNew.objects.create(**validated_data)

        # Assign users uniquely
        for uid in user_ids:
            if AgentUserMapping.objects.filter(user_id=uid).exists():
                raise serializers.ValidationError(
                    {"user_ids": f"User {uid} is already assigned to another entity."}
                )

            AgentUserMapping.objects.create(
                user_id=uid,
                agent_auth=instance
            )

        return instance

    def update(self, instance, validated_data):
        user_ids = validated_data.pop("user_ids", None)

        # Normal field update
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Handle users update
        if user_ids is not None:
            # Remove previous mappings
            AgentUserMapping.objects.filter(agent_auth=instance).delete()

            # Add new mappings
            for uid in user_ids:
                if AgentUserMapping.objects.filter(user_id=uid).exists():
                    raise serializers.ValidationError(
                        {"user_ids": f"User {uid} is already assigned to another entity."}
                    )

                AgentUserMapping.objects.create(
                    user_id=uid,
                    agent_auth=instance
                )

        return instance
    def get_company_name(self, obj):
        return obj.company.name if obj.company else None

    def get_branch_name(self, obj):
        return obj.branch.name if obj.branch else None