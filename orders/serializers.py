from rest_framework import serializers

from accounts.models import AdminBankDetails, Company
from staging_creworder_backend import settings
from kyc.serializers import KYCSerializer
from shipment.models import ShipmentModel
from .models import Customer_State, SmsConfig, Order_Table, OrderDetail,Category, OrderStatusWorkflow, OrderValueSetting, Payment_Status, PincodeLocality,Products,OrderLogModel,Payment_Type,OrderStatus, AllowStatus, ReturnType,LableLayout,invoice_layout
from django.contrib.auth.models import User
from accounts.serializers import AdminBankDetailsSerializers, CompanySerializer

class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Products
        fields = '__all__'  
        


class OrderDetailSerializer(serializers.ModelSerializer):
    gst_rate = serializers.SerializerMethodField()
    product_sku = serializers.SerializerMethodField()
    product_hsn_number = serializers.SerializerMethodField()
    discount_per_product = serializers.SerializerMethodField()
    base_price = serializers.SerializerMethodField()
    gst_amount = serializers.SerializerMethodField()
    taxable_value = serializers.SerializerMethodField()
    final_price_per_unit = serializers.SerializerMethodField()
    final_total_price = serializers.SerializerMethodField()
    product_weight = serializers.SerializerMethodField()
    # ✅ NEW FIELDS
    sgst_rate = serializers.SerializerMethodField()
    cgst_rate = serializers.SerializerMethodField()
    igst_rate = serializers.SerializerMethodField()
    sgst_amount = serializers.SerializerMethodField()
    cgst_amount = serializers.SerializerMethodField()
    igst_amount = serializers.SerializerMethodField()

    class Meta:
        model = OrderDetail
        fields = '__all__'

    def get_customer_state_code(self, obj):
        return obj.order.customer_state.gst_state_code  

    def get_company_state_code(self, obj):
        return "07" # assuming state_code exists

    def is_same_state(self, obj):
        return self.get_customer_state_code(obj) == self.get_company_state_code(obj)

    def get_gst_rate(self, obj):
        return obj.product.product_gst_percent if obj.product else None

    def get_product_sku(self, obj):
        return obj.product.product_sku if obj.product else None
    
    def get_product_weight(self, obj):
        return obj.product.product_weight if obj.product else None
    
    def get_product_hsn_number(self, obj):
        return obj.product.product_hsn_number if obj.product else None

    def get_discount_per_product(self, obj):
        order = obj.order
        if not order or not order.discount:
            return 0

        qty = obj.product_qty
        unit_price = float(obj.product_price)
        product_total = unit_price * qty

        order_details = order.orderdetail_set.all()
        total_order_value = sum(float(item.product_price) * item.product_qty for item in order_details)

        if total_order_value == 0:
            return 0

        product_discount_total = (product_total / total_order_value) * float(order.discount)
        discount_per_unit = product_discount_total / qty if qty else 0

        return round(discount_per_unit, 2)

    def get_base_price(self, obj):
        gst_rate = self.get_gst_rate(obj)
        if gst_rate is None:
            return float(obj.product_price)
        base_price = float(obj.product_price) / (1 + gst_rate / 100)
        return round(base_price, 2)

    def get_final_price_per_unit(self, obj):
        unit_price = float(obj.product_price)
        discount = self.get_discount_per_product(obj)
        return round(unit_price - discount, 2)

    def get_final_total_price(self, obj):
        return round(self.get_final_price_per_unit(obj) * obj.product_qty, 2)

    def get_gst_amount(self, obj):
        final_price_total = self.get_final_total_price(obj)
        gst_rate = self.get_gst_rate(obj)
        if not gst_rate:
            return 0
        base_price_total = final_price_total / (1 + gst_rate / 100)
        gst_total = final_price_total - base_price_total
        return round(gst_total, 2)

    def get_taxable_value(self, obj):
        final_price_total = self.get_final_total_price(obj)
        gst_rate = self.get_gst_rate(obj)
        if not gst_rate:
            return round(final_price_total, 2)
        base_price_total = final_price_total / (1 + gst_rate / 100)
        return round(base_price_total, 2)

    # 🧾 NEW FIELDS - TAX BREAKUP
    def get_sgst_rate(self, obj):
        return round(self.get_gst_rate(obj) / 2, 2) if self.is_same_state(obj) else 0

    def get_cgst_rate(self, obj):
        return round(self.get_gst_rate(obj) / 2, 2) if self.is_same_state(obj) else 0

    def get_igst_rate(self, obj):
        return self.get_gst_rate(obj) if not self.is_same_state(obj) else 0

    def get_sgst_amount(self, obj):
        gst_amount = self.get_gst_amount(obj)
        return round(gst_amount / 2, 2) if self.is_same_state(obj) else 0

    def get_cgst_amount(self, obj):
        gst_amount = self.get_gst_amount(obj)
        return round(gst_amount / 2, 2) if self.is_same_state(obj) else 0

    def get_igst_amount(self, obj):
        return self.get_gst_amount(obj) if not self.is_same_state(obj) else 0







class OrderLogSerializer(serializers.ModelSerializer):
    action_by_username = serializers.SerializerMethodField()
    order_status_name = serializers.SerializerMethodField()
    class Meta:
        model = OrderLogModel
        fields = '__all__'  

    def get_action_by_username(self, auth):
        return auth.action_by.username if auth.action_by else None
    def get_order_status_name(self, auth):
        return auth.order_status.name if auth.order_status else None
    

class OrderTableSerializer(serializers.ModelSerializer):
    created_at = serializers.DateTimeField(format="%d-%b-%Y %I:%M %p", read_only=True)
    updated_at = serializers.DateTimeField(format="%d-%b-%Y %I:%M %p", read_only=True)
    assigned_date_time = serializers.DateTimeField(format="%d-%b-%Y %I:%M %p", read_only=True)
    estimated_delivery_date = serializers.DateField(format="%d-%b-%Y", read_only=True)
    order_details = OrderDetailSerializer(many=True, read_only=True, source='orderdetail_set')
    
    # order_logs = OrderLogSerializer(many=True, read_only=True, source='orderlogmodel_set')
    order_created_by_username = serializers.SerializerMethodField()
    last_action_by_name = serializers.SerializerMethodField()
    last_upated_at = serializers.SerializerMethodField()
    payment_mode = serializers.SerializerMethodField()
    order_status_title = serializers.SerializerMethodField()
    customer_state_name= serializers.SerializerMethodField()
    payment_type_name=serializers.SerializerMethodField()
    tracking_link = serializers.SerializerMethodField()
    
    class Meta:
        model = Order_Table
        fields = '__all__'  

    def get_order_created_by_username(self, auth):
        return auth.order_created_by.username if auth.order_created_by else None
    def get_order_status_title(self, data):
        return data.order_status.name if data.order_status else None
    def get_customer_state_name(self,data):
        return data.customer_state.name if data.customer_state else None
    def get_payment_type_name(self,data):
        return data.payment_type.name if data.payment_type else None
    def get_last_action_by_name(self, obj):
        recent_log = OrderLogModel.objects.filter(order=obj).order_by('-updated_at').first()
        return OrderLogSerializer(recent_log).data['action_by_username'] if recent_log else None
    def get_payment_mode(self, obj):
        return obj.payment_type.name if obj.payment_type else None
    def get_last_upated_at(self, obj):
        recent_log = OrderLogModel.objects.filter(order=obj).order_by('-updated_at').first()
        return OrderLogSerializer(recent_log).data['updated_at'] if recent_log else None
    
    def get_tracking_link(self, obj):
        """
        Safely generates the tracking link for the order using shipment vendor and airway bill.
        """
        try:
            if obj.shipment_vendor and obj.order_wayBill:
                shipment = ShipmentModel.objects.filter(
                    shipment_vendor=obj.shipment_vendor,
                    company=obj.company,
                    branch=obj.branch,
                    status=1
                ).order_by('provider_priority').first()

                if shipment and shipment.tracking_url:
                    base_url = shipment.tracking_url.rstrip('/') + '/'
                    return f"{base_url}{obj.order_wayBill}"
        except Exception as e:
            # Optional: log the exception
            return "#"
            # logger.warning(f"Tracking URL generation failed: {str(e)}")
            
        return None

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = '__all__'  

class OrderStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderStatus
        fields = '__all__'  

class InvoiceSerializer(serializers.ModelSerializer):
    order_details = OrderDetailSerializer(many=True, read_only=True, source='orderdetail_set')
    order_created_by_username = serializers.SerializerMethodField()
    payment_mode = serializers.SerializerMethodField()
    order_status_title = serializers.SerializerMethodField()
    company_detail = serializers.SerializerMethodField()
    state_name = serializers.SerializerMethodField()
    payment_status_title = serializers.SerializerMethodField()
    admin_account_details = serializers.SerializerMethodField()
    kyc_details = serializers.SerializerMethodField()
    total_taxable_amount = serializers.SerializerMethodField()  # <- added

    class Meta:
        model = Order_Table
        fields = '__all__'

    def get_order_created_by_username(self, auth):
        return auth.order_created_by.username if auth.order_created_by else None

    def get_order_status_title(self, data):
        return data.order_status.name if data.order_status else None

    def get_payment_mode(self, obj):
        return obj.payment_type.name if obj.payment_type else None

    def get_state_name(self, obj):
        return obj.customer_state.name if obj.customer_state else None

    def get_payment_status_title(self, obj):
        return obj.payment_status.name if obj.payment_status else None

    def get_company_detail(self, obj):
        if obj.company:
            return CompanySerializer(obj.company).data
        return {}

    def get_admin_account_details(self, obj):
        company = obj.company
        branch = obj.branch
        
        if company and branch:
            priority1 = AdminBankDetails.objects.filter(company=company, branch=branch, priority=1).first()
            if priority1:
                return AdminBankDetailsSerializers(priority1).data

            alternative = AdminBankDetails.objects.filter(company=company, branch=branch).exclude(priority=1).first()
            if alternative:
                return AdminBankDetailsSerializers(alternative).data

        return {None}

    def get_kyc_details(self, obj):
        if obj.company and hasattr(obj.company, 'kyc'):
            return KYCSerializer(obj.company.kyc).data
        return {}

    def get_total_taxable_amount(self, obj):
        order_details = obj.orderdetail_set.all()
        total = 0
        for detail in order_details:
            serializer = OrderDetailSerializer(detail)
            total += serializer.data.get('taxable_value', 0)
        return round(total, 2)

class FilterOrdersSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order_Table
        fields = '__all__'


class PincodeLocalitySerializer(serializers.ModelSerializer):
    class Meta:
        model = PincodeLocality
        fields = ['id', 'pincode', 'locality_name']

class PaymentStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment_Status
        fields = '__all__' 

class CustomerStateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer_State
        fields = '__all__'

class PaymentTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment_Type
        fields = '__all__' 

class OrderValueSettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderValueSetting
        fields = '__all__'

class ScanOrderSerializer(serializers.Serializer):
    order_id = serializers.CharField()


class AllowStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = AllowStatus
        fields = ['id', 'name', 'status_code',"shipment_vendor"]


class OrderStatusWorkflowSerializer(serializers.ModelSerializer):
    order_status = serializers.CharField(source='order_status.name')
    shipment_vendor = serializers.CharField(source='shipment_vendor.name')
    allow_status = AllowStatusSerializer(many=True)

    class Meta:
        model = OrderStatusWorkflow
        fields = ['id', 'order_status', 'shipment_vendor', 'allow_status']

class ReturnTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReturnType
        fields = '__all__'






class LableLayoutSerializer(serializers.ModelSerializer):
    logo_images_url = serializers.SerializerMethodField() 
    class Meta:
        model = LableLayout
        fields = '__all__'
    def get_logo_images_url(self, obj):
        request = self.context.get('request')
        if obj.logo_images:
            if request:
                return request.build_absolute_uri(obj.logo_images.url)
            elif hasattr(settings, "BASE_URL"):
                return f"{settings.BASE_URL}{obj.logo_images.url}"
            else:
                return obj.logo_images.url
        return None

class LableinvoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = invoice_layout
        fields = '__all__'


class NotificationsConfigSerializer(serializers.ModelSerializer):
    company = serializers.PrimaryKeyRelatedField(queryset=Company.objects.all())
    order_status = serializers.PrimaryKeyRelatedField(queryset=OrderStatus.objects.all(), many=True)
    
    class Meta:
        model = SmsConfig
        fields = ['id', 'company', 'order_status', 'notification_type', 'created_at', 'updated_at','mobile_number','brand_name','website','email']

    def create(self, validated_data):
        # Create NotificationConfig instance
        order_status_data = validated_data.pop('order_status')
        notification_config = SmsConfig.objects.create(**validated_data)
        notification_config.order_status.set(order_status_data)
        notification_config.save()
        return notification_config

    def update(self, instance, validated_data):
        # Update NotificationConfig instance
        order_status_data = validated_data.pop('order_status')
        instance = super().update(instance, validated_data)
        instance.order_status.set(order_status_data)
        instance.save()
        return instance
    

class OrderStatusUpdateSerializer(serializers.Serializer):
    order_ids = serializers.ListField(
        child=serializers.CharField(), allow_empty=False
    )


class OrderTableSerializer1(serializers.ModelSerializer):
    created_at = serializers.DateTimeField(format="%d-%b-%Y %I:%M %p", read_only=True)
    updated_at = serializers.DateTimeField(format="%d-%b-%Y %I:%M %p", read_only=True)
    assigned_date_time = serializers.DateTimeField(format="%d-%b-%Y %I:%M %p", read_only=True)
    estimated_delivery_date = serializers.DateField(format="%d-%b-%Y", read_only=True)
    order_details = OrderDetailSerializer(many=True, read_only=True, source='orderdetail_set')
    customer_phone = serializers.SerializerMethodField()
    # order_logs = OrderLogSerializer(many=True, read_only=True, source='orderlogmodel_set')
    order_created_by_username = serializers.SerializerMethodField()
    last_action_by_name = serializers.SerializerMethodField()
    last_upated_at = serializers.SerializerMethodField()
    payment_mode = serializers.SerializerMethodField()
    order_status_title = serializers.SerializerMethodField()
    customer_state_name= serializers.SerializerMethodField()
    payment_type_name=serializers.SerializerMethodField()
    tracking_link = serializers.SerializerMethodField()
    
    class Meta:
        model = Order_Table
        fields = '__all__'  
    def get_customer_phone(self, obj):
        return obj.customer_phone[-10:] if obj.customer_phone else None
    def get_order_created_by_username(self, auth):
        return auth.order_created_by.username if auth.order_created_by else None
    def get_order_status_title(self, data):
        return data.order_status.name if data.order_status else None
    def get_customer_state_name(self,data):
        return data.customer_state.name if data.customer_state else None
    def get_payment_type_name(self,data):
        return data.payment_type.name if data.payment_type else None
    def get_last_action_by_name(self, obj):
        recent_log = OrderLogModel.objects.filter(order=obj).order_by('-updated_at').first()
        return OrderLogSerializer(recent_log).data['action_by_username'] if recent_log else None
    def get_payment_mode(self, obj):
        return obj.payment_type.name if obj.payment_type else None
    def get_last_upated_at(self, obj):
        recent_log = OrderLogModel.objects.filter(order=obj).order_by('-updated_at').first()
        return OrderLogSerializer(recent_log).data['updated_at'] if recent_log else None
    
    def get_tracking_link(self, obj):
        """
        Safely generates the tracking link for the order using shipment vendor and airway bill.
        """
        try:
            if obj.shipment_vendor and obj.order_wayBill:
                shipment = ShipmentModel.objects.filter(
                    shipment_vendor=obj.shipment_vendor,
                    company=obj.company,
                    branch=obj.branch,
                    status=1
                ).order_by('provider_priority').first()

                if shipment and shipment.tracking_url:
                    base_url = shipment.tracking_url.rstrip('/') + '/'
                    return f"{base_url}{obj.order_wayBill}"
        except Exception as e:
            # Optional: log the exception
            return "#"
            # logger.warning(f"Tracking URL generation failed: {str(e)}")
            
        return None
    


class OrderSummarySerializer(serializers.Serializer):
    payment_type = serializers.IntegerField()
    payment_type__name = serializers.CharField()
    total_orders = serializers.IntegerField()
    total_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
