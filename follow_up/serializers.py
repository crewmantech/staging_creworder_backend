from rest_framework import serializers

from follow_up.utils import get_phone_by_reference_id
from orders.models import Order_Table
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
    doctor_id = serializers.CharField(source="doctor.id", read_only=True)
    doctor_username = serializers.CharField(
        source="doctor.user.username", read_only=True
    )
    patient_phone = serializers.CharField(
        required=False,
        allow_null=True,
        allow_blank=True
    )
    doctor_full_name = serializers.SerializerMethodField()
    user_full_name = serializers.SerializerMethodField()
    doctor_email = serializers.EmailField(
        source="doctor.user.email", read_only=True
    )
    doctor_phone = serializers.SerializerMethodField()
    is_order = serializers.SerializerMethodField()

    def get_is_order(self, obj):
        """
        Returns True if at least one order exists for this appointment
        """
        return Order_Table.objects.filter(
            appointment=obj,
            is_deleted=False
        ).exists()
    # doctor_name = serializers.SerializerMethodField()
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
    branch_name = serializers.CharField(source="branch.name", read_only=True)
    company_name = serializers.CharField(source="company.name", read_only=True)

    class Meta:
        model = Appointment
        fields = "__all__"
        read_only_fields = (
            "company",
            "branch",
            "created_by",
            "bmi",
            "uhid",
        )

    def get_doctor_full_name(self, obj):
        if not obj.doctor or not obj.doctor.user:
            return None
        first = obj.doctor.user.first_name or ""
        last = obj.doctor.user.last_name or ""
        return f"{first} {last}".strip()
    def get_user_full_name(self, obj):
        if not obj.created_by:
            return None
        first = obj.created_by.first_name or ""
        last = obj.created_by.last_name or ""
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
        request = self.context["request"]
        instance = getattr(self, "instance", None)

        patient_phone = data.get("patient_phone")
        reference_id = data.get("reference_id")

        # ✅ CREATE
        if instance is None:
            if not patient_phone and not reference_id:
                raise serializers.ValidationError(
                    "Either patient_phone or reference_id is required."
                )

        # ✅ UPDATE
        else:
            # 🔑 Use EXISTING instance values
            existing_phone = instance.patient_phone
            existing_reference = instance.reference_id

            if (
                not patient_phone
                and not reference_id
                and not existing_phone
                and not existing_reference
            ):
                raise serializers.ValidationError(
                    "Either patient_phone or reference_id is required."
                )

        # 🔐 Doctor validation (unchanged)
        doctor = data.get("doctor")
        user = request.user

        if doctor and doctor.company != user.profile.company:
            raise serializers.ValidationError(
                "Doctor does not belong to your company."
            )

        if doctor and user.profile.branch not in doctor.branches.all():
            raise serializers.ValidationError(
                "Doctor is not available in your branch."
            )

        return data


    def create(self, validated_data):
        request = self.context["request"]
        user = request.user

        reference_id = validated_data.get("reference_id")
        patient_phone = validated_data.get("patient_phone")
        reference_id = validated_data.get("reference_id")

        # 🔥 STRICT reference_id behavior
        if reference_id and (not patient_phone or "*" in patient_phone):
            try:
                print("---------------98",reference_id)
                result = get_phone_by_reference_id(
                    user=user,
                    reference_id=reference_id
                )
                print(result,"---------------100")
                validated_data["patient_phone"] = result["phone_number"]

            except ValidationError:
                # ❌ BLOCK creation if phone not found
                raise serializers.ValidationError({
                    "reference_id": "Phone number not found for this reference ID."
                })

        return super().create(validated_data)
    # def update(self, instance, validated_data):
    #     request = self.context.get("request")

    #     if request and request.user.has_perm("accounts.view_number_masking_others"):
    #         # ✅ Keep original phone from DB
    #         validated_data["patient_phone"] = instance.patient_phone

    #     return super().update(instance, validated_data)

class AppointmentLayoutSerializer(serializers.ModelSerializer):
    company = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Appointment_layout
        fields = "__all__"
        read_only_fields = ["id", "company", "created_at", "updated_at"]

