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