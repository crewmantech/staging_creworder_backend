# follow_up/apps.py

from django.apps import AppConfig
import threading
import time
import os

class FollowUpConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'follow_up'

    def ready(self):
        # ❌ Prevent duplicate threads in dev server
        if os.environ.get("RUN_MAIN") != "true":
            return

        from follow_up.tasks import followup_reminder_scheduler

        def run_scheduler():
            print("🚀 Follow-up scheduler started (10 min interval)")
            while True:
                try:
                    followup_reminder_scheduler()
                except Exception as e:
                    print("❌ Scheduler Error:", e)

                time.sleep(600)  # ✅ 10 minutes

        threading.Thread(
            target=run_scheduler,
            daemon=True
        ).start()