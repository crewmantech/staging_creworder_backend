from rest_framework.exceptions import ValidationError
from follow_up.models import Follow_Up
from lead_management.models import Lead
from services.cloud_telephoney.cloud_telephoney_service import get_phone_number_by_call_id



def get_phone_by_reference_id(user, reference_id):
    """
    Returns phone_number ONLY on success.
    Raises ValidationError on failure.
    """

    if not reference_id:
        raise ValidationError("reference_id is required")

    # -------- 1️⃣ Try Lead --------
    lead = Lead.objects.filter(
        lead_id=reference_id
    ).only("customer_phone").first()

    if lead and lead.customer_phone:
        return {
            "type": "lead",
            "reference_id": reference_id,
            "phone_number": lead.customer_phone
        }

    # -------- 2️⃣ Try Follow Up --------
    followup = Follow_Up.objects.filter(
        followup_id=reference_id
    ).only("customer_phone").first()

    if followup and followup.customer_phone:
        return {
            "type": "followup",
            "reference_id": reference_id,
            "phone_number": followup.customer_phone
        }

    # -------- 3️⃣ Fallback: Cloud call lookup --------
    # reference_id is treated as call_id
    try:
        phone_number = get_phone_number_by_call_id(
            user=user,
            call_id=reference_id
        )
        return {
            "type": "call",
            "reference_id": reference_id,
            "phone_number": phone_number
        }
    except ValidationError as e:
        # Bubble up vendor error cleanly
        raise ValidationError({
            "reference_id": reference_id,
            "message": "Phone number not found in Lead, Follow-up, or Call records",
            "details": e.detail
        })
