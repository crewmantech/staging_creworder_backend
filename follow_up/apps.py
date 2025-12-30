# follow_up/apps.py

from django.apps import AppConfig
import threading
import time

class FollowUpConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'follow_up'

    def ready(self):
        from follow_up.tasks import followup_reminder_scheduler

        def run_scheduler():
            while True:
                try:
                    followup_reminder_scheduler()
                except Exception as e:
                    print("Follow-up Scheduler Error:", e)
                time.sleep(60)  # run every minute

        threading.Thread(target=run_scheduler, daemon=True).start()
