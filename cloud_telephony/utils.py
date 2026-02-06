from cloud_telephony.models import CloudTelephonyChannelAssign


def get_company_from_agent_campaign(agent_id):
    assign = CloudTelephonyChannelAssign.objects.filter(
        agent_id=agent_id
    ).select_related("company").first()

    if assign:
        return assign.company
    return None

def get_user_from_agent_campaign(agent_id):
    assign = CloudTelephonyChannelAssign.objects.filter(
        agent_id=agent_id
    ).select_related("user").first()
    return assign.user if assign else None

def has_valid_recording(path):
    if not path:
        return False

    invalid_values = ["-", "File Not Available", "Not Available", ""]
    if path in invalid_values:
        return False

    # basic URL check
    if path.startswith("http"):
        return True

    return False
def get_agent_id_by_user(user_id):
    
    qs = CloudTelephonyChannelAssign.objects.filter(
        user_id=user_id,
        is_active=True  
    )
    assign = qs.order_by("priority", "created_at").first()

    return assign.agent_id if assign else None

def duration_to_seconds(duration_str):
    try:
        h, m, s = map(int, duration_str.split(":"))
        return h * 3600 + m * 60 + s
    except Exception:
        return 0