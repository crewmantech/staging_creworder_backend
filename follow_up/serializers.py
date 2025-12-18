from rest_framework import serializers
from .models import Appointment, Follow_Up,Notepad

class FollowUpSerializer(serializers.ModelSerializer):
    follow_status_name = serializers.CharField(source='follow_status.name', read_only=True)
    follow_add_by_name = serializers.CharField(source='follow_add_by.first_name', read_only=True)
    class Meta:
        model = Follow_Up
        fields = '__all__'  # Includes all original fields
        extra_fields = ['follow_status_name','follow_add_by_name']  # Add this for clarity, optional

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['follow_status_name'] = (
            instance.follow_status.name if instance.follow_status else None
        )
        representation['follow_add_by_name'] = (
            f"{instance.follow_add_by.first_name} {instance.follow_add_by.last_name}".strip()
            if instance.follow_add_by else None
        )
        
        return representation


class NotepadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notepad
        fields = '__all__'

class AppointmentSerializer(serializers.ModelSerializer):
    doctor_name = serializers.CharField(
        source="doctor.user.username", read_only=True
    )
    branch_name = serializers.CharField(
        source="branch.name", read_only=True
    )
    company_name = serializers.CharField(
        source="company.name", read_only=True
    )

    class Meta:
        model = Appointment
        fields = "__all__"
        read_only_fields = [
            "company",
            "branch",
            "created_by",
            "uhid",
            "bmi"
        ]

    def validate(self, data):
        request = self.context.get("request")
        user = request.user

        doctor = data.get("doctor")

        # 🔐 Doctor must belong to same company
        if doctor and doctor.company != user.profile.company:
            raise serializers.ValidationError(
                "Doctor does not belong to your company."
            )

        # 🔐 Doctor must be available in user's branch
        if doctor and user.profile.branch not in doctor.branches.all():
            raise serializers.ValidationError(
                "Doctor is not available in your branch."
            )

        return data
