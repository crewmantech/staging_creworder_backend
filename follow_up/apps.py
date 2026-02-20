# follow_up/apps.py

from django.utils import timezone
from django.apps import AppConfig
import threading
import time
import os

class FollowUpConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'follow_up'

    def ready(self):
        # ❌ Prevent duplicate threads in dev server
        # if os.environ.get("RUN_MAIN") != "true":
        #     return

        from follow_up.tasks import followup_reminder_scheduler

        def run_scheduler():
            print("🚀 Follow-up scheduler started (5 min interval)")

            while True:
                try:
                    now = timezone.localtime(timezone.now())

                    # seconds remaining to next 5-minute mark
                    sleep_seconds = 300 - (
                        (now.minute % 5) * 60 + now.second
                    )

                    print(f"⏳ Sleeping {sleep_seconds} seconds")

                    time.sleep(sleep_seconds)

                    followup_reminder_scheduler()

                except Exception as e:
                    print("❌ Scheduler Error:", e)
                    time.sleep(60)  # ✅ 5 minutes

        threading.Thread(
            target=run_scheduler,
            daemon=True
        ).start()