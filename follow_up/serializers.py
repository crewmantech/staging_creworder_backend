from rest_framework import serializers

from follow_up.utils import get_phone_by_reference_id
from .models import Appointment, Appointment_layout, Follow_Up,Notepad
from rest_framework.exceptions import ValidationError

class FollowUpSerializer(serializers.ModelSerializer):
    follow_status_name = serializers.CharField(source='follow_status.name', read_only=True)
    follow_add_by_name = serializers.CharField(source='follow_add_by.first_name', read_only=True)
    assign_user_name = serializers.CharField(
        source='assign_user.first_name',
        read_only=True
    )

    class Meta:
        model = Follow_Up
        fields = '__all__'

class BulkFollowupAssignSerializer(serializers.Serializer):
    user_ids = serializers.ListField(
        child=serializers.IntegerField(),
        allow_empty=False
    )
    followup_ids = serializers.ListField(
        child=serializers.CharField(),
        allow_empty=False
    )
    
class NotepadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notepad
        fields = '__all__'

class AppointmentSerializer(serializers.ModelSerializer):
    # 🔹 Doctor basic details
    doctor_id = serializers.CharField(source="doctor.id", read_only=True)
    doctor_username = serializers.CharField(
        source="doctor.user.username", read_only=True
    )
    doctor_full_name = serializers.SerializerMethodField()
    doctor_email = serializers.EmailField(
        source="doctor.user.email", read_only=True
    )
    doctor_phone = serializers.SerializerMethodField()

    # 🔹 Doctor professional details
    doctor_registration_number = serializers.CharField(
        source="doctor.registration_number", read_only=True
    )
    doctor_degree = serializers.CharField(
        source="doctor.degree", read_only=True
    )
    doctor_specialization = serializers.CharField(
        source="doctor.specialization", read_only=True
    )
    doctor_experience_years = serializers.IntegerField(
        source="doctor.experience_years", read_only=True
    )
    doctor_address = serializers.CharField(
        source="doctor.address", read_only=True
    )
    doctor_is_active = serializers.BooleanField(
        source="doctor.is_active", read_only=True
    )
    doctor_sign = serializers.ImageField(
        source="doctor.doctor_sign", read_only=True
    )

    # 🔹 Branch & Company
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

    def get_doctor_full_name(self, obj):
        if not obj.doctor or not obj.doctor.user:
            return None
        first = obj.doctor.user.first_name or ""
        last = obj.doctor.user.last_name or ""
        return f"{first} {last}".strip()

    def get_doctor_phone(self, obj):
        if (
            obj.doctor
            and hasattr(obj.doctor.user, "profile")
            and obj.doctor.user.profile.contact_no
        ):
            return str(obj.doctor.user.profile.contact_no)
        return None
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

    def create(self, validated_data):
        request = self.context.get("request")
        user = request.user

        reference_id = validated_data.get("reference_id")
        patient_phone = validated_data.get("patient_phone")

        # 🔐 CONDITIONAL FETCH (YOUR CONDITION)
        if (
            reference_id
            and not patient_phone
            and user.has_perm("accounts.view_number_masking_others")
            and user.profile.user_type != "admin"
        ):
            try:
                result = get_phone_by_reference_id(
                    user=user,
                    reference_id=reference_id
                )
                validated_data["patient_phone"] = result["phone_number"]
            except ValidationError:
                # Do NOT block appointment creation
                pass

        return super().create(validated_data)
    

class AppointmentLayoutSerializer(serializers.ModelSerializer):
    company = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Appointment_layout
        fields = "__all__"
        read_only_fields = ["id", "company", "created_at", "updated_at"]

