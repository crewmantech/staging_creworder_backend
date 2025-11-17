from rest_framework.response import Response
from rest_framework import status



def custom_response(success=True, message="", data=None, errors=None, status_code=200):
    return Response({
        "success": success,
        "message": message,
        "data": data if success else None,
        "errors": errors if not success else None,
        "status_code": status_code
    }, status=status_code)


import threading
from django.db import connections
import logging

logger = logging.getLogger(__name__)

def check_and_kill_sleep_queries():
    try:
        with connections['default'].cursor() as cursor:
            cursor.execute("SHOW PROCESSLIST")
            rows = cursor.fetchall()
            for row in rows:
                process_id = row[0]
                command = row[4]
                sleep_time = row[5]

                if command.lower() == 'sleep' and sleep_time > 30:
                    try:
                        cursor.execute(f"KILL {process_id}")
                        logger.info(f"Killed sleep query: {process_id} (sleep {sleep_time}s)")
                    except Exception as e:
                        logger.warning(f"Kill failed: {str(e)}")
    except Exception as e:
        logger.error(f"Sleep kill check failed: {str(e)}")


import random
import string

def generate_unique_id(model_class, prefix='ord', length=5, field_name='id'):
    while True:
        random_id = prefix + ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))
        if not model_class.objects.filter(**{field_name: random_id}).exists():
            return random_id
        

def deactivate_user(user, reason):
    from accounts.models import LoginLog
    user.profile.status = 0
    user.profile.save()
    LoginLog.objects.create(
        user=user,
        ip_address="system",
        user_agent="system",
        status="failed",
        reason=f"User auto-deactivated: {reason}"
    )


def reassign_user_assets_on_suspension(user_obj):
    """
    Reassign all assets (Leads, Categories, Pipelines) of a suspended user.
    Priority:
        1. Team Lead
        2. Manager
    """

    from accounts.models import UserStatus

    profile = user_obj.profile

    # Step 1: Determine replacement user
    new_user = None

    if profile.teamlead and profile.teamlead.profile.status == UserStatus.active:
        new_user = profile.teamlead

    elif profile.manager and profile.manager.profile.status == UserStatus.active:
        new_user = profile.manager

    if not new_user:
        return {
            "status": False,
            "message": "No active TL or Manager found for reassignment."
        }

    # -------------------------
    # 1. Reassign Leads
    # -------------------------
    from lead_management.models import Lead
    leads = Lead.objects.filter(assign_user=user_obj)
    leads.update(assign_user=new_user)

    # -------------------------
    # 2. Reassign UserCategoryAssignment
    # -------------------------
    from lead_management.models import UserCategoryAssignment
    categories = UserCategoryAssignment.objects.filter(user_profile=user_obj)
    categories.update(user_profile=new_user)

    # -------------------------
    # 3. Reassign Pipelines (ManyToMany)
    # -------------------------
    from lead_management.models import Pipeline
    pipelines = Pipeline.objects.filter(assigned_users=user_obj)

    pipeline_count = 0
    for p in pipelines:
        p.assigned_users.remove(user_obj)
        p.assigned_users.add(new_user)
        pipeline_count += 1

    return {
        "status": True,
        "message": "Reassignment completed.",
        "lead_count": leads.count(),
        "category_count": categories.count(),
        "pipeline_count": pipeline_count,
        "assigned_to": new_user.username
    }