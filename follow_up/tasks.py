# follow_up/tasks.py

from django.utils import timezone
from datetime import timedelta
from chat.models import Notification
from follow_up.models import Follow_Up


def followup_reminder_scheduler():
    """
    Runs every minute and checks reminder_date
    """

    now = timezone.now()
    print(now,"------------------15")
    start_time = now.replace(second=0, microsecond=0)
    end_time = start_time + timedelta(minutes=1)

    followups = Follow_Up.objects.filter(
        reminder_date__gte=start_time,
        reminder_date__lt=end_time
    )

    for followup in followups:
        users_to_notify = set()

        # Assigned user
        if followup.assign_user:
            users_to_notify.add(followup.assign_user)

        # Created by user
        if followup.follow_add_by:
            users_to_notify.add(followup.follow_add_by)

        # Updated by user (if exists in BaseModel)
        if hasattr(followup, "updated_by") and followup.updated_by:
            users_to_notify.add(followup.updated_by)

        for user in users_to_notify:
            Notification.objects.get_or_create(
                user=user,
                followup=followup,
                notification_type="followup_reminder",
                defaults={
                    "message": f"⏰ Follow-up reminder for {followup.customer_name}",
                    "url": f"/followups/{followup.followup_id}/"
                }
            )
