import calendar
from datetime import date

from accounts.models import Company
from orders.utils import send_order_report




def daily_order_report_job():
    print("daily_order_report_job Order Report Job Started")
    for company in Company.objects.filter(status=True):
        for branch in company.branches.all():
            send_order_report(company, branch, "daily")


def weekly_order_report_job():
    print("weekly_order_report_job Order Report Job Started")
    for company in Company.objects.filter(status=True):
        for branch in company.branches.all():
            send_order_report(company, branch, "weekly")


def monthly_order_report_job():
    print("monthly_order_report_job Order Report Job Started")
    today = date.today()
    last_day = calendar.monthrange(today.year, today.month)[1]

    # if today.day != last_day:
    #     return

    for company in Company.objects.filter(status=True):
        for branch in company.branches.all():
            send_order_report(company, branch, "monthly")