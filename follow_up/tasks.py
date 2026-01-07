# follow_up/tasks.py

from django.utils import timezone
from datetime import timedelta
from chat.models import Notification
from follow_up.models import Follow_Up


def followup_reminder_scheduler():
    """
    Runs every 5 minutes
    Checks reminders in fixed 5-minute windows
    """

    now = timezone.localtime(timezone.now())
    print("Current IST Time:", now, now.tzinfo)

    # ⏱ Round DOWN to nearest 5-minute mark
    end_time = now.replace(
        minute=(now.minute // 5) * 5,
        second=0,
        microsecond=0
    )

    start_time = end_time - timedelta(minutes=5)

    print(
        f"⏳ Checking followups from {start_time} → {end_time}"
    )

    followups = Follow_Up.objects.filter(
        reminder_date__gte=start_time,
        reminder_date__lt=end_time
    )

    for followup in followups:
        users_to_notify = set()

        # 👤 Assigned user
        if followup.assign_user:
            users_to_notify.add(followup.assign_user)

        # 👤 Created by user
        if followup.follow_add_by:
            users_to_notify.add(followup.follow_add_by)

        # 👤 Updated by user (optional)
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
