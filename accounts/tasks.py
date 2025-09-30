from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from .models import Company

@shared_task
def deactivate_expired_demo_companies():
    cutoff_time = timezone.now() - timedelta(hours=72)
    expired_companies = Company.objects.filter(
        package__name__iexact="demo",
        created_at__lt=cutoff_time,
        status=True
    )
    count = expired_companies.count()
    expired_companies.update(status=False)
    return f"{count} companies deactivated."
