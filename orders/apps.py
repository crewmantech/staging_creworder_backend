# orders/apps.py
from django.apps import AppConfig



class OrdersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'orders'

    def ready(self):
        """
        Start APScheduler only once when Django starts
        """
        try:
            from orders.scheduler import start_scheduler
            start_scheduler()
        except Exception as e:
            # Avoid crashing Django if scheduler fails
            print("Scheduler not started:", e)
