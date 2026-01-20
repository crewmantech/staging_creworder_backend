import re
from django.db.models import Sum, F, FloatField
from django.db.models.functions import Coalesce
from django.db.models import Sum, Count,Avg
from accounts.models import Employees
from orders.models import Customer_State, Order_Table, OrderDetail
from services.email.email_service import send_email
from django.contrib.auth.models import User
from datetime import time,date, timedelta
def get_order_amount_breakup(order_qs):
    """
    Returns:
    {
        order_id: {
            base_amount,
            gst_amount,
            total_amount
        }
    }
    """
    qs = (
        OrderDetail.objects
        .filter(order__in=order_qs)
        .values("order_id")
        .annotate(
            base_amount=Coalesce(Sum("product_price"), 0.0),
            gst_amount=Coalesce(Sum("gst_amount"), 0.0),
            total_amount=Coalesce(
                Sum(F("product_price") + F("gst_amount"), output_field=FloatField()),
                0.0
            )
        )
    )

    return {
        row["order_id"]: {
            "base_amount": row["base_amount"],
            "gst_amount": row["gst_amount"],
            "total_amount": row["total_amount"],
        }
        for row in qs
    }


from django.db.models import Sum, F, FloatField, ExpressionWrapper,Q
from django.db.models.functions import Coalesce



# def get_price_breakdown(order_qs):
#     """
#     Accounting-grade price breakdown.
#     Fully timezone-safe.
#     No mixed-type errors.
#     """

#     if not order_qs.exists():
#         return {
#             "base_amount": 0.0,
#             "gst_amount": 0.0,
#             "sub_total": 0.0,
#             "discount": 0.0,
#             "shipping": 0.0,
#             "cod": 0.0,
#             "freight": 0.0,
#             "final_payable": 0.0,
#         }

#     # ---------------- PRODUCT + GST ----------------
#     gst_expr = ExpressionWrapper(
#         F("product_price") * F("product__product_gst_percent") / 100,
#         output_field=FloatField()
#     )

#     product_data = OrderDetail.objects.filter(
#         order__in=order_qs
#     ).aggregate(
#         base_amount=Coalesce(
#             Sum(ExpressionWrapper(F("product_price"), output_field=FloatField())),
#             0.0
#         ),
#         gst_amount=Coalesce(Sum(gst_expr), 0.0),
#     )

#     base_amount = float(product_data["base_amount"])
#     gst_amount = float(product_data["gst_amount"])
#     sub_total = base_amount + gst_amount

#     # ---------------- ORDER LEVEL ----------------
#     order_data = order_qs.aggregate(
#         discount=Coalesce(
#             Sum(ExpressionWrapper(F("discount"), output_field=FloatField())),
#             0.0
#         ),
#         shipping=Coalesce(
#             Sum(ExpressionWrapper(F("shipping_charges"), output_field=FloatField())),
#             0.0
#         ),
#         cod=Coalesce(
#             Sum(ExpressionWrapper(F("cod_amount"), output_field=FloatField())),
#             0.0
#         ),
#         freight=Coalesce(
#             Sum(ExpressionWrapper(F("freight_charges"), output_field=FloatField())),
#             0.0
#         ),
#         final_payable=Coalesce(
#             Sum(ExpressionWrapper(F("total_amount"), output_field=FloatField())),
#             0.0
#         ),
#     )

#     return {
#         "base_amount": round(base_amount, 2),
#         "gst_amount": round(gst_amount, 2),
#         "sub_total": round(sub_total, 2),

#         "discount": round(float(order_data["discount"]), 2),
#         "shipping": round(float(order_data["shipping"]), 2),
#         "cod": round(float(order_data["cod"]), 2),
#         "freight": round(float(order_data["freight"]), 2),

#         # ✅ GUARANTEED MATCH
#         "final_payable": round(float(order_data["final_payable"]), 2),
#     }



def get_price_breakdown(order_qs):
    """
    FINAL REQUIREMENT:
    - total_amount (final payable)
    - base_amount (GST excluded)
    - gst_amount (tax only)
    """

    if not order_qs.exists():
        return {
            "base_amount": 0.0,
            "gst_amount": 0.0,
            "total_amount": 0.0,
        }

    # ---------- FINAL TOTAL (SOURCE OF TRUTH) ----------
    total_amount = float(
        order_qs.aggregate(
            total=Coalesce(
                Sum(ExpressionWrapper(F("total_amount"), output_field=FloatField())),
                0.0
            )
        )["total"]
    )

    # ---------- CALCULATE EFFECTIVE GST RATIO ----------
    # base = price / (1 + gst%)
    base_expr = ExpressionWrapper(
        F("product_price") /
        (1 + (F("product__product_gst_percent") / 100.0)),
        output_field=FloatField()
    )

    gst_expr = ExpressionWrapper(
        F("product_price") - base_expr,
        output_field=FloatField()
    )

    product_tax_data = OrderDetail.objects.filter(
        order__in=order_qs
    ).aggregate(
        base_sum=Coalesce(Sum(base_expr), 0.0),
        gst_sum=Coalesce(Sum(gst_expr), 0.0),
    )

    base_sum = float(product_tax_data["base_sum"])
    gst_sum = float(product_tax_data["gst_sum"])

    if base_sum == 0:
        return {
            "base_amount": 0.0,
            "gst_amount": 0.0,
            "total_amount": round(total_amount, 2),
        }

    # ---------- SCALE BASE & GST TO FINAL TOTAL ----------
    scale_factor = total_amount / (base_sum + gst_sum)

    base_amount = base_sum * scale_factor
    gst_amount = total_amount - base_amount

    return {
        "base_amount": round(base_amount, 2),
        "gst_amount": round(gst_amount, 2),
        "total_amount": round(total_amount, 2),
    }
from phonenumber_field.phonenumber import PhoneNumber
def normalize_phone(phone):
    """
    Accepts:
    - string phone
    - PhoneNumber object
    Returns:
    - ['9876543210', '+919876543210']
    """

    if not phone:
        return None

    # ✅ Handle PhoneNumber object safely
    if isinstance(phone, PhoneNumber):
        phone = phone.as_e164  # '+918489895444'

    # Safety: force string
    phone = str(phone)

    digits = re.sub(r"\D", "", phone)

    if len(digits) < 10:
        return None

    core = digits[-10:]
    return [
        core,
        f"+91{core}",
    ]


def get_customer_state(state_name):
    state_name = state_name.strip().lower()
    return Customer_State.objects.filter(
        Q(name__iexact=state_name) |
        Q(keys__regex=rf'(^|,){state_name}(,|$)')
    ).first()


from datetime import date, datetime, time
import calendar

def get_current_month_range():
    today = date.today()

    first_day = date(today.year, today.month, 1)
    last_day = date(
        today.year,
        today.month,
        calendar.monthrange(today.year, today.month)[1]
    )

    start_datetime = datetime.combine(first_day, time.min)
    end_datetime = datetime.combine(last_day, time.max)

    return start_datetime, end_datetime

from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings


def send_report_email(subject, recipients, context):
    html = render_to_string("emails/monthly_order_report.html", context)

    # email = EmailMultiAlternatives(
    #     subject=subject,
    #     body="Monthly Order Report",
    #     from_email=settings.DEFAULT_FROM_EMAIL,
    #     to=recipients
    # )
    # email.attach_alternative(html, "text/html")
    # email.send()
    print(recipients,"----------------------269")
    email = send_email(subject, html, ['lakhansharma1june@gmail.com'],"welcome")
# def send_monthly_report_mail(subject, to_emails, context):
#     html_content = render_to_string(
#         "emails/monthly_order_report.html",
#         context
#     )
    
#     email = send_email(subject, html_content, 'lakhansharma1june@gmail.com',"welcome")
    # email.attach_alternative(html_content, "text/html")
    # email.send()

def get_manager_team_user_ids(manager_id):
    return Employees.objects.filter(
        manager_id=manager_id,
        status=1
    ).values_list("user_id", flat=True)


def get_order_summary(company_id, branch_id, start_dt, end_dt, user_ids=None):

    orders = Order_Table.objects.filter(
        company_id=company_id,
        branch_id=branch_id,
        is_deleted=False,
        created_at__range=(start_dt, end_dt)
    )

    if user_ids:
        orders = orders.filter(
            Q(order_created_by_id__in=user_ids) |
            Q(updated_by_id__in=user_ids)
        )

    summary = orders.aggregate(
        total_orders=Count("id"),
        total_amount=Sum("total_amount"),
        total_discount=Sum("discount"),
        total_gross_amount=Sum("gross_amount"),
    )

    user_wise = orders.values(
        "order_created_by_id",
        "order_created_by__username",
        "order_created_by__first_name",
        "order_created_by__last_name"
    ).annotate(
        total_orders=Count("id"),
        total_amount=Sum("total_amount"),
        total_discount=Sum("discount"),
        total_gross_amount=Sum("gross_amount"),
    ).order_by("-total_orders")

    user_wise_data = []
    for u in user_wise:
        user_wise_data.append({
            "user_id": u["order_created_by_id"],
            "username": u["order_created_by__username"],
            "name": f'{u["order_created_by__first_name"]} {u["order_created_by__last_name"]}'.strip(),
            "total_orders": u["total_orders"],
            "total_amount": u["total_amount"] or 0,
            "total_discount": u["total_discount"] or 0,
            "total_gross_amount": u["total_gross_amount"] or 0,
        })

    return summary, user_wise_data


def get_order_report(company_id, branch_id, start_dt, end_dt, user_ids=None):

    orders = Order_Table.objects.filter(
        company_id=company_id,
        branch_id=branch_id,
        is_deleted=False,
        created_at__range=(start_dt, end_dt)
    )

    if user_ids:
        orders = orders.filter(
            Q(order_created_by_id__in=user_ids) |
            Q(updated_by_id__in=user_ids)
        )

    # =============================
    # OVERALL SUMMARY
    # =============================
    summary = orders.aggregate(
        total_orders=Count("id"),
        total_amount=Sum("total_amount"),
        total_discount=Sum("discount"),
        total_gross_amount=Sum("gross_amount"),
    )

    # =============================
    # STATUS-WISE SUMMARY
    # =============================
    status_qs = orders.values(
        "order_status__name"
    ).annotate(
        orders=Count("id"),
        amount=Sum("total_amount")
    )

    status_summary = [
        {
            "status": s["order_status__name"],
            "orders": s["orders"],
            "amount": s["amount"] or 0
        }
        for s in status_qs
    ]

    # =============================
    # USER + STATUS WISE
    # =============================
    user_status_qs = orders.values(
        "order_created_by_id",
        "order_created_by__username",
        "order_created_by__first_name",
        "order_created_by__last_name",
        "order_status__name"
    ).annotate(
        orders=Count("id"),
        amount=Sum("total_amount")
    )

    user_map = {}

    for row in user_status_qs:
        uid = row["order_created_by_id"]

        if uid not in user_map:
            user_map[uid] = {
                "user_id": uid,
                "username": row["order_created_by__username"],
                "name": f'{row["order_created_by__first_name"]} {row["order_created_by__last_name"]}'.strip(),
                "total_orders": 0,
                "total_amount": 0,
                "statuses": []
            }

        user_map[uid]["statuses"].append({
            "status": row["order_status__name"],
            "orders": row["orders"],
            "amount": row["amount"] or 0
        })

        user_map[uid]["total_orders"] += row["orders"]
        user_map[uid]["total_amount"] += row["amount"] or 0

    return {
        "summary": summary,
        "status_summary": status_summary,
        "user_wise": list(user_map.values())
    }


def send_order_report(company, branch, report_type):
    today = date.today()

    # ==========================
    # DATE RANGE
    # ==========================
    if report_type == "daily":
        start_dt = datetime.combine(today, time.min)
        end_dt = datetime.combine(today, time.max)

    elif report_type == "weekly":
        start_dt = datetime.combine(today - timedelta(days=today.weekday()), time.min)
        end_dt = datetime.combine(start_dt.date() + timedelta(days=6), time.max)

    elif report_type == "monthly":
        start_dt = datetime.combine(date(today.year, today.month, 1), time.min)
        end_dt = datetime.combine(
            date(
                today.year,
                today.month,
                calendar.monthrange(today.year, today.month)[1],
            ),
            time.max,
        )
    else:
        raise ValueError("Invalid report type")

    # ==========================
    # ORDER QUERYSET (IMPORTANT)
    # ==========================
    print("Fetching orders for report:", company.name, branch.name, start_dt, end_dt)
    order_qs = Order_Table.objects.filter(
        company_id=company.id,
        branch_id=branch.id,
        created_at__range=(start_dt, end_dt),
        order_status__name="Delivered"  # ✅ recommended (adjust if needed)
    )

    # ==========================
    # PRICE BREAKDOWN
    # ==========================
    price_breakdown = get_price_breakdown(order_qs)
    # {
    #   base_amount,
    #   gst_amount,
    #   total_amount
    # }

    # ==========================
    # ADMIN REPORT
    # ==========================
    admin_emails = list(
        User.objects.filter(
            profile__company_id=company.id,
            profile__user_type="admin",
            is_active=True
        ).values_list("email", flat=True)
    )

    admin_data = get_order_report(
        company_id=company.id,
        branch_id=branch.id,
        start_dt=start_dt,
        end_dt=end_dt,
    )

    if admin_emails:
        send_report_email(
            subject=f"📊 {report_type.capitalize()} Order Report",
            recipients=admin_emails,
            context={
                "role": "ADMIN",
                "company_name": company.name,
                "branch_name": branch.name,
                "start_date": start_dt.date(),
                "end_date": end_dt.date(),
                "report_type":report_type,
                # ✅ ADD PRICE DATA TO EMAIL
                "base_amount": price_breakdown["base_amount"],
                "gst_amount": price_breakdown["gst_amount"],
                "total_amount": price_breakdown["total_amount"],

                **admin_data,
            },
        )

    # ==========================
    # MANAGER REPORT
    # ==========================
    manager_ids = Employees.objects.filter(
        manager__isnull=False,
        company_id=company.id,
        branch_id=branch.id,
        status=1,
    ).values_list("manager_id", flat=True).distinct()

    managers = User.objects.filter(id__in=manager_ids, is_active=True)

    for manager in managers:
        team_user_ids = Employees.objects.filter(
            manager_id=manager.id,
            branch_id=branch.id,
        ).values_list("user_id", flat=True)

        if not team_user_ids or not manager.email:
            continue

        team_orders = order_qs.filter(user_id__in=team_user_ids)
        team_price_breakdown = get_price_breakdown(team_orders)

        manager_data = get_order_report(
            company_id=company.id,
            branch_id=branch.id,
            start_dt=start_dt,
            end_dt=end_dt,
            user_ids=team_user_ids,
        )

        send_report_email(
            subject=f"📊 {report_type.capitalize()} Team Order Report",
            recipients=[manager.email],
            context={
                "role": "MANAGER",
                "company_name": company.name,
                "branch_name": branch.name,
                "start_date": start_dt.date(),
                "end_date": end_dt.date(),
                "report_type":report_type,
                # ✅ TEAM PRICE BREAKDOWN
                "base_amount": team_price_breakdown["base_amount"],
                "gst_amount": team_price_breakdown["gst_amount"],
                "total_amount": team_price_breakdown["total_amount"],

                **manager_data,
            },
        )