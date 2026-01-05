from django.db.models import Sum, F, FloatField
from django.db.models.functions import Coalesce

from orders.models import OrderDetail

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


def get_price_breakdown(order_qs):
    """
    Returns aggregated base, gst, total amounts for given orders
    """
    data = OrderDetail.objects.filter(
        order__in=order_qs
    ).aggregate(
        base_amount=Coalesce(Sum("product_price"), 0.0),
        gst_amount=Coalesce(Sum("gst_amount"), 0.0),
        total_amount=Coalesce(
            Sum(F("product_price") + F("gst_amount"), output_field=FloatField()),
            0.0
        )
    )

    return {
        "base_amount": float(data["base_amount"]),
        "gst_amount": float(data["gst_amount"]),
        "total_amount": float(data["total_amount"]),
    }