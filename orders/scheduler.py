from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from django.conf import settings

from .tasks import (
    daily_order_report_job,
    weekly_order_report_job,
    monthly_order_report_job,
)

scheduler = BackgroundScheduler(timezone=settings.TIME_ZONE)


def start_scheduler():
    if scheduler.running:
        return

    # ✅ DAILY – 8:00 PM
    scheduler.add_job(
        daily_order_report_job,
        CronTrigger(hour=14, minute=44),
        id="daily_order_report",
        replace_existing=True,
    )

    # ✅ WEEKLY – Sunday 8:30 PM
    scheduler.add_job(
        weekly_order_report_job,
        # CronTrigger(day_of_week="sun", hour=20, minute=30),
        CronTrigger(hour=14, minute=44),
        id="weekly_order_report",
        replace_existing=True,
    )

    # ✅ MONTHLY – Every day 8:30 PM (checks last day internally)
    scheduler.add_job(
        monthly_order_report_job,
        # CronTrigger(hour=20, minute=30),
        CronTrigger(hour=14, minute=44),
        id="monthly_order_report",
        replace_existing=True,
    )

    scheduler.start()
