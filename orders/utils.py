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


from django.db.models import Sum, F, FloatField, ExpressionWrapper
from django.db.models.functions import Coalesce



def get_price_breakdown(order_qs):
    """
    Accounting-grade price breakdown.
    Fully timezone-safe.
    No mixed-type errors.
    """

    if not order_qs.exists():
        return {
            "base_amount": 0.0,
            "gst_amount": 0.0,
            "sub_total": 0.0,
            "discount": 0.0,
            "shipping": 0.0,
            "cod": 0.0,
            "freight": 0.0,
            "final_payable": 0.0,
        }

    # ---------------- PRODUCT + GST ----------------
    gst_expr = ExpressionWrapper(
        F("product_price") * F("product__product_gst_percent") / 100,
        output_field=FloatField()
    )

    product_data = OrderDetail.objects.filter(
        order__in=order_qs
    ).aggregate(
        base_amount=Coalesce(
            Sum(ExpressionWrapper(F("product_price"), output_field=FloatField())),
            0.0
        ),
        gst_amount=Coalesce(Sum(gst_expr), 0.0),
    )

    base_amount = float(product_data["base_amount"])
    gst_amount = float(product_data["gst_amount"])
    sub_total = base_amount + gst_amount

    # ---------------- ORDER LEVEL ----------------
    order_data = order_qs.aggregate(
        discount=Coalesce(
            Sum(ExpressionWrapper(F("discount"), output_field=FloatField())),
            0.0
        ),
        shipping=Coalesce(
            Sum(ExpressionWrapper(F("shipping_charges"), output_field=FloatField())),
            0.0
        ),
        cod=Coalesce(
            Sum(ExpressionWrapper(F("cod_amount"), output_field=FloatField())),
            0.0
        ),
        freight=Coalesce(
            Sum(ExpressionWrapper(F("freight_charges"), output_field=FloatField())),
            0.0
        ),
        final_payable=Coalesce(
            Sum(ExpressionWrapper(F("total_amount"), output_field=FloatField())),
            0.0
        ),
    )

    return {
        "base_amount": round(base_amount, 2),
        "gst_amount": round(gst_amount, 2),
        "sub_total": round(sub_total, 2),

        "discount": round(float(order_data["discount"]), 2),
        "shipping": round(float(order_data["shipping"]), 2),
        "cod": round(float(order_data["cod"]), 2),
        "freight": round(float(order_data["freight"]), 2),

        # ✅ GUARANTEED MATCH
        "final_payable": round(float(order_data["final_payable"]), 2),
    }