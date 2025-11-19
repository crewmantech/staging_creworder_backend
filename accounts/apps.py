# accounts/apps.py
# from django.apps import AppConfig


# class AccountsConfig(AppConfig):
#     default_auto_field = 'django.db.models.BigAutoField'
#     name = 'accounts'
# new

import random
import pytz
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from django.apps import AppConfig
from django.db.models.signals import post_migrate
import logging
from django.utils.timezone import now
from services.email.email_service import send_email
from django.template.loader import render_to_string
logger = logging.getLogger(__name__)

class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'accounts'

    def ready(self):
        # Import models only when the app is ready
        from .models import CompanyInquiry, Package, Company, User, Employees,Branch,Attendance
        from accounts.models import ExpiringToken as Token
        from django.contrib.auth.models import Group
        from datetime import time, datetime,timedelta
        from apscheduler.triggers.cron import CronTrigger
        from datetime import timedelta
        from django.utils import timezone
        def process_pending_inquiries():
            try:
                pending_inquiries = CompanyInquiry.objects.filter(status="pending")
                for inquiry in pending_inquiries:
                    package = Package.objects.get(name="demo")
                    superuser = User.objects.filter(is_superuser=True).first()

                    if not superuser:
                        raise Exception("No superuser account exists. Please create a superuser first.")

                    # Define company data
                    company_data = {
                        'name': inquiry.company_name,
                        'company_email': inquiry.company_email,
                        'company_phone': inquiry.company_phone,
                        'company_website': inquiry.company_website,
                        'company_address': inquiry.company_address,
                        'package': package,
                    }

                    company = Company(**company_data)
                    company.created_by = superuser
                    company.save(user=superuser)
                    random_number = random.randint(1000, 9999)
                    username = f"{inquiry.company_name.split()[0]}_{inquiry.full_name.split()[0]}"
                    user = User.objects.create_user(
                        username=username.lower(),
                        email=inquiry.email,
                        password=inquiry.password,  # Ensure secure password handling
                    )
                   # Assign the user to the 'admin' group (or any desired group)
                    admin_group = Group.objects.get(name='super-super-DemoRole')  # Ensure the 'admin' group exists
                    user.groups.add(admin_group)
                    user.save()
                    branches = Branch.objects.filter(company=company)
                    Employees.objects.create(
                        user=user,
                        contact_no=inquiry.contact_number,
                        gender='m',
                        marital_status="unmarried",
                        user_type="admin",
                        company=company,
                        branch=branches.first() if branches.exists() else None,
                    )

                    inquiry.status = "approved"
                    inquiry.company = company
                    res =inquiry.save()
                    try:
                        subject = "Welcome to Creworder"
                        template = "emails/welcome_email.html"  # Your HTML email template
                        context = {
                            'full_name': inquiry.full_name,
                            'company_name': inquiry.company_name,
                            'username': username.lower(),
                            'password': inquiry.password,
                            'login_url': "https://creworder.com/login",  # Update with your login URL
                        }
                        html_message = render_to_string(template, context)
                        # plain_message = strip_tags(html_message)
                        recipient_list = [inquiry.company_email,inquiry.email]
                        send_email(subject, html_message, recipient_list,"welcome")
                        

                        logger.info(f"Email sent successfully to {inquiry.email}")
                    except Exception as email_error:
                        logger.error(f"Error sending email to {inquiry.email}: {email_error}")

            except Exception as e:
                logger.error(f"Error processing inquiries: {e}")
        def fix_attendance_clock_out():
            try:
                today = now().date()
                # Get all attendances of today with missing clock_out
                pending_attendance = Attendance.objects.filter(clock_out__isnull=True, date=today)
                updated_count = 0
                print(pending_attendance,"-------------108")
                for attendance in pending_attendance:
                    print(attendance,"-------109")
                    user = attendance.user
                    token = Token.objects.filter(user=user).first()

                    # Default fallback clock_out = 7:00 PM
                    clock_out_value = time(19, 0)
                    print(token,"-=------token")
                    if token:
                        # Expiry time = token.created + 15 minutes
                        token_expiry = token.created + timedelta(minutes=15)
                        print(token_expiry,"-=------120")
                        # if now() > token_expiry:
                            # Use expiry time as clock_out
                        clock_out_value = token_expiry.time()

                    attendance.clock_out = clock_out_value
                    attendance.save(update_fields=["clock_out"])
                    updated_count += 1

                logger.info(f"✅ Fixed clock_out for {updated_count} attendance records.")
                return updated_count
            except Exception as e:
                logger.error(f"❌ Error while fixing attendance clock_out: {e}")
                return 0
        def deactivate_old_demo_companies():
            print("-----------------137")
            """Deactivate companies with 'demo' package older than 3 days."""
            three_days_ago = timezone.now().date() - timedelta(days=3)
            companies = Company.objects.filter(
                created_at__lte=three_days_ago,
                package__name__iexact='demo',
                status=True
            )
            updated_count = companies.update(status=False)
            print(f"Deactivated {updated_count} demo companies older than 3 days.")
            # for company in companies:
            #     company.status = False
            #     status = company.update(update_fields=['status'])
            #     print(status)
            #     print(f"Deactivated demo company: {company.name} (created at: {company.created_at})")
        def auto_create_monthly_targets():
            from .models import UserTargetsDelails
            today = datetime.today()

            # Only run if today is 1st (extra protection)
            if today.day != 1:
                return

            current_monthyear = today.strftime("%m-%Y")
            last_month = today.replace(day=1) - timedelta(days=1)
            last_monthyear = last_month.strftime("%m-%Y")

            # Fetch all last month targets
            last_month_targets = UserTargetsDelails.objects.filter(
                monthyear=last_monthyear,
                in_use=True
            )

            for target in last_month_targets:
                print(target,"------------------172")
                # Skip if new month target already exists
                if UserTargetsDelails.objects.filter(
                    user=target.user,
                    monthyear=current_monthyear
                ).exists():
                    continue

                # Create auto new target
                UserTargetsDelails.objects.create(
                    user=target.user,
                    daily_amount_target=target.daily_amount_target,
                    daily_orders_target=target.daily_orders_target,
                    monthly_amount_target=target.monthly_amount_target,
                    monthly_orders_target=target.monthly_orders_target,
                    monthyear=current_monthyear,
                    branch=target.branch,
                    company=target.company,
                    in_use=True
                )
        def start_scheduler(sender, **kwargs):
            tz = pytz.timezone("Asia/Kolkata")
            scheduler = BackgroundScheduler()
            scheduler.add_job(
                process_pending_inquiries,
                IntervalTrigger(seconds=30),  # Run every 30 seconds
                id="process_pending_inquiries",
                max_instances=1,
                misfire_grace_time=30,  # Optional
            )
            scheduler.add_job(
                auto_create_monthly_targets,
                IntervalTrigger(seconds=180),  # Run every 30 seconds
                id="create_target_inquiries",
                max_instances=1,
                misfire_grace_time=30,  # Optional
            )
            scheduler.add_job(
                fix_attendance_clock_out,
                CronTrigger(hour=23, minute=30),  # 10:3 PM
                id="fix_attendance_clock_out",
                max_instances=1,
                replace_existing=True,
            )
            
            scheduler.add_job(deactivate_old_demo_companies, 'interval', hours=24, id='deactivate_old_demo_companies')
            scheduler.add_job(
                auto_create_monthly_targets,
                trigger=CronTrigger(day="1", hour="0", minute="1", timezone=tz),
                id="auto_create_monthly_targets",
                replace_existing=True,
                max_instances=1
            )
            # scheduler.add_job(
            #     deactivate_old_demo_companies,
            #     IntervalTrigger(seconds=40),  # Run every 30 seconds
            #     id="deactivate_old_demo_companies",
            #     max_instances=1,
            #     misfire_grace_time=30,  # Optional
            # )
            scheduler.start()

        # Ensure the scheduler starts after migrations are complete
        # post_migrate.connect(start_scheduler, sender=self)

        start_scheduler(sender=self )
        post_migrate.connect(start_scheduler, sender=self)
