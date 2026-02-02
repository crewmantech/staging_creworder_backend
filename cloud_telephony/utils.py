from cloud_telephony.models import CloudTelephonyChannelAssign


def get_company_from_agent_campaign(agent_id, campaign_id):
    assign = CloudTelephonyChannelAssign.objects.filter(
        agent_id=agent_id,
        camp_id=campaign_id,
        is_active=True
    ).select_related("company").first()

    if assign:
        return assign.company
    return None