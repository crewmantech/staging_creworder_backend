import random,string
import json
from django.contrib.auth.models import User
from django.db import models
from django.core.exceptions import PermissionDenied
from accounts.models import Company, Branch,PickUpPoint
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import Permission
from accounts.utils import generate_unique_id
from middleware.request_middleware import get_request
from shipment.models import ShipmentModel, ShipmentVendor
from django.core.validators import RegexValidator, URLValidator

class BaseModel(models.Model):
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="%(app_label)s_%(class)s_created_by")
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="%(app_label)s_%(class)s_updated_by")

    def save(self, *args, **kwargs):
        request = get_request()
        if request and request.user.is_authenticated:
            if not self.pk:
                self.created_by = request.user
            self.updated_by = request.user
        super().save(*args, **kwargs)
    class Meta:
        abstract = True

class Category(models.Model):
    STATUS = [
        (0, "Inactive"),
        (1, "Active"),
    ]
    id = models.CharField(max_length=50, primary_key=True, unique=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=False, null=False)
    image = models.ImageField(
        upload_to="category_images/", null=True, blank=True
    )
    status=models.IntegerField(choices=STATUS)
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE)
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        db_table = 'category_table'
        unique_together = ("name", "branch", "company")
    
    def save(self, *args, **kwargs):
        if not self.id:
            self.id = generate_unique_id(Category, prefix='CGI')
        super().save(*args, **kwargs)  
    def __str__(self):
        return f"category {self.id} by {self.name}"
    
class Products(models.Model):
    id = models.CharField(max_length=50, primary_key=True, unique=True)
    product_id = models.CharField(max_length=100, unique=True,null=True, blank=True)
    product_name = models.CharField(max_length=255)
    product_sku = models.CharField(max_length=255)
    product_quantity = models.IntegerField()
    product_price = models.CharField(max_length=100)
    product_hsn_number = models.CharField(max_length=200)
    product_gst_percent = models.IntegerField(choices=[(0, '0%'),(5, '5%'), (12, '12%'), (18, '18%'), (28, '28%')])
    product_image = models.ImageField(upload_to='product_images/', null=True, blank=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    product_description = models.TextField(blank=False, null=False)
    product_availability = models.IntegerField(choices=[(0, 'InStock'), (1, 'OutOfStock')])
    product_status = models.IntegerField(choices=[(0, 'Pending'), (1, 'Active'), (2, 'Suspended'), (3, 'Deleted')])
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE)
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    product_created = models.DateTimeField(auto_now_add=True)
    product_updated = models.DateTimeField(auto_now=True, null=True)
    product_inventory_location = models.TextField(blank=False, null=False)
    product_size = models.IntegerField()
    product_weight = models.FloatField()
    product_height = models.IntegerField()
    product_width = models.IntegerField()
    dos = models.TextField(null=True, blank=True, default=None)
    duration = models.TextField(null=True, blank=True, default=None)
    advice = models.TextField(null=True, blank=True, default=None)
    instructions = models.TextField(null=True, blank=True, default=None)
    class Meta:
        db_table = 'products_table'
        unique_together = ("product_name", "branch", "company") 
    def __str__(self):
        return f"products {self.id} by {self.product_name}"
    
    def save(self, *args, **kwargs):
        if not self.id:
            self.id = generate_unique_id(Products, prefix='PDI')
        super().save(*args, **kwargs)
        content_type, created = ContentType.objects.get_or_create(
            app_label="orders",  # Fixed app label
            model="Products"  # Fixed model name
        )
        permission_names = ["can_work_on_this"]
        
        for perm_name in permission_names:
            company_name = self.company.name if self.company else "SuperAdmin"
            permission, created = Permission.objects.get_or_create(
                name=f"Products {perm_name.replace('_', ' ').capitalize()} {self.product_name.replace('_', ' ')} - {company_name}",
                codename=f"products_{perm_name}_{self.product_name.lower().replace(' ', '_')}",
                content_type=content_type
            )
    
class Payment_Type(models.Model):
    id = models.CharField(max_length=50, primary_key=True, unique=True)
    name = models.CharField(max_length=50)
    # branch = models.ForeignKey(Branch, on_delete=models.CASCADE, default=1)
    # company = models.ForeignKey(Company, on_delete=models.CASCADE, default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        db_table = 'payment_types_table'
    def save(self, *args, **kwargs):
        if not self.id:
            self.id = generate_unique_id(Payment_Type, prefix='PTI')
        super().save(*args, **kwargs)  
    def __str__(self):
        return self.name

class Payment_method(models.Model):
    id = models.CharField(max_length=50, primary_key=True, unique=True)
    name = models.CharField(max_length=50)
    # branch = models.ForeignKey(Branch, on_delete=models.CASCADE, default=1)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, default=1,blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        db_table = 'payment_method_table'
    def save(self, *args, **kwargs):
        if not self.id:
            self.id = generate_unique_id(Payment_method, prefix='PMI')
        super().save(*args, **kwargs)  
    def __str__(self):
        return self.name
    
class OrderStatus(models.Model):
    id = models.CharField(max_length=50, primary_key=True, unique=True)
    name = models.CharField(max_length=50)
    description = models.TextField(default="Order Status")
    # branch = models.ForeignKey(Branch, on_delete=models.CASCADE, default=1)
    # company = models.ForeignKey(Company, on_delete=models.CASCADE, default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        db_table = 'order_status_table'
        permissions = (
            ('view_orderstatus_customer_information', 'OrderStatus view Customer Information'),
            ('view_orderstatus_order_status_tracking', 'OrderStatus view Order Status Tracking'),
            ('view_orderstatus_order_payment_status', 'OrderStatus view Order Payment Status')
            # ('view_orderstatus_order_number_masking', 'OrderStatus view Order Number Masking')
            )
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.id:
            self.id = generate_unique_id(OrderStatus, prefix='OSI')
        super().save(*args, **kwargs)
        content_type, created = ContentType.objects.get_or_create(
            app_label="orders",  # Fixed app label
            model="orderstatus"  # Fixed model name
        )
        permission_names = ["can_work_on_this"]
        for perm_name in permission_names:
            Permission.objects.get_or_create(
                name=f"OrderStatus {perm_name.replace('_', ' ').capitalize()} {self.name.replace('_', ' ')}",
                codename=f"orderstatus_{perm_name}_{self.name.lower().replace(' ', '_')}",
                content_type=content_type
            )
    
class Payment_Status(models.Model):
    id = models.CharField(max_length=50, primary_key=True, unique=True)
    name = models.CharField(max_length=50)
    # branch = models.ForeignKey(Branch, on_delete=models.CASCADE, default=1)
    # company = models.ForeignKey(Company, on_delete=models.CASCADE, default=1)
    # amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'payment_status_table'
    
    def save(self, *args, **kwargs):
        if not self.id:
            self.id = generate_unique_id(Payment_Status, prefix='PSI')
        super().save(*args, **kwargs)  

    def __str__(self):
        return self.name

# class Customer_State(models.Model):
#     id = models.AutoField(primary_key=True)
#     name = models.CharField(max_length=50)
#     branch = models.ForeignKey(Branch, on_delete=models.CASCADE, default=1)
#     company = models.ForeignKey(Company, on_delete=models.CASCADE, default=1)
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)
#     class Meta:
#         db_table = 'state_table'

#     def __str__(self):
#         return self.name

class Customer_State(models.Model):
    id = models.CharField(max_length=50, primary_key=True, unique=True)
    name = models.CharField(max_length=50, unique=True)
    keys = models.TextField(blank=True, default="")
    gst_state_code = models.CharField(max_length=20, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "state_table"

    def save(self, *args, **kwargs):
        if not self.id:
            self.id = generate_unique_id(Customer_State, prefix="CSI")

        # normalize keys
        if self.keys:
            key_list = [
                k.strip().lower()
                for k in self.keys.split(",")
                if k.strip()
            ]
            self.keys = ",".join(sorted(set(key_list)))
        else:
            self.keys = ""

        super().save(*args, **kwargs)

    def __str__(self):
        return self.name
    
class Order_Table(BaseModel):
    id = models.CharField(max_length=50, primary_key=True, unique=True)
    order_id = models.CharField(max_length=100, unique=True, null=True, blank=True)
    network_ip = models.CharField(max_length=100)
    customer_name = models.CharField(max_length=255)
    customer_parent_name = models.CharField(max_length=255, null=True, blank=True)
    customer_phone = models.CharField(max_length=50)
    customer_alter_phone = models.CharField(max_length=50, null=True, blank=True)
    customer_email = models.EmailField(max_length=255, null=True, blank=True)
    customer_address = models.TextField()
    customer_postal = models.CharField(max_length=20)
    customer_city = models.CharField(max_length=255)
    customer_state = models.ForeignKey(Customer_State, on_delete=models.PROTECT)
    customer_country = models.CharField(max_length=150)
    product_details = models.JSONField()
    total_amount = models.FloatField()
    gross_amount = models.FloatField()
    discount = models.FloatField()
    prepaid_amount = models.IntegerField()
    cod_amount = models.IntegerField(default=0)
    payment_type = models.ForeignKey(Payment_Type, on_delete=models.PROTECT)
    payment_status = models.ForeignKey(Payment_Status, on_delete=models.PROTECT)
    order_status = models.ForeignKey(OrderStatus, on_delete=models.PROTECT)
    order_ship_by = models.TextField(null=True, blank=True)
    order_wayBill = models.CharField(max_length=255, null=True, blank=True)
    order_remark = models.TextField()
    repeat_order = models.IntegerField(choices=[(0, 'New'), (1, 'Repeat')])
    order_created_by = models.ForeignKey(User, on_delete=models.PROTECT)
    is_booked = models.IntegerField(choices=[(0, 'Not Booked'), (1, 'Booked')])
    is_scheduled = models.IntegerField(choices=[(0, 'Not Schedule'), (1, 'Scheduled')], default=0)
    service_provider = models.CharField(max_length=50, null=True, blank=True)
    call_id = models.CharField(max_length=50, null=True, blank=True)
    lead_id = models.CharField(max_length=50, null=True, blank=True)
    course_order = models.IntegerField(default=0)
    product_qty = models.IntegerField(default=0)
    shipping_charges = models.IntegerField(default=0)
    edd_time = models.CharField(max_length=255, null=True, blank=True)
    zone = models.CharField(max_length=255, null=True, blank=True)
    region = models.CharField(max_length=255, null=True, blank=True)
    pick_up_point = models.ForeignKey(PickUpPoint, on_delete=models.PROTECT, null=True, blank=True)
    course_order_repeated = models.IntegerField(default=0)
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, default=1)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, default=1)  
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    shipment_id = models.IntegerField(null=True)
    vendor_order_id = models.CharField(max_length=255, null=True, blank=True)
    assigned_date_time = models.DateTimeField(null=True, blank=True)
    courier_name = models.CharField(max_length=255, null=True, blank=True)
    freight_charges = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    awb_response = models.JSONField(null=True, blank=True)
    estimated_delivery_date = models.DateField(null=True, blank=True)
    pickup_id = models.IntegerField(null=True)
    manifest_id = models.IntegerField(null=True)
    is_pickup_scheduled = models.BooleanField(default=False, null=True)
    ofd_counter = models.IntegerField(null=True, default=0)
    shipment_vendor = models.ForeignKey(ShipmentVendor, on_delete=models.PROTECT, null=True, blank=True)
    locality = models.CharField(max_length=255, null=True, blank=True)
    qcqueations = models.JSONField(null=True, blank=True)
    is_deleted = models.BooleanField(default=False, null=True)
    is_pickup = models.IntegerField(choices=[(0, 'Pickup Pending'), (1, 'Pickup Done'), (2, 'RTO Recieved')], default=0)
    is_pickups = models.ForeignKey('ReturnType', on_delete=models.PROTECT, null=True, blank=True)
    payment_method =models.ForeignKey('Payment_method', on_delete=models.PROTECT, null=True, blank=True)
    utr_number = models.CharField(max_length=255, null=True, blank=True)
    # ✅ NEW FIELDS
    course_order_count = models.IntegerField(default=1)   # 1st new column
    is_closed = models.BooleanField(default=False)        # 2nd new column
    odablock = models.BooleanField(default=False)
    reference_order = models.ForeignKey(                  # 3rd new column
        "self", on_delete=models.SET_NULL, null=True, blank=True, related_name="repeated_orders"
    )
    ndr_count = models.IntegerField(default=0)  
    ndr_action = models.CharField(max_length=255, null=True, blank=True)  
    ndr_data = models.JSONField(null=True, blank=True)  
    ndr_date = models.DateTimeField(null=True, blank=True, default=None)
    appointment = models.ForeignKey(
        "follow_up.Appointment",
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    class Meta:
        db_table = 'orders_table'
    def save(self, *args, **kwargs):
        created = self.pk is None
        if not self.id:
            self.id = generate_unique_id(Order_Table, prefix='OTI')
        super().save(*args, **kwargs)
        OrderLogModel.objects.create(
            order=self,
            order_status=self.order_status,
            action_by=self.updated_by if self.updated_by else self.order_created_by,
            action=f"Order {'created' if created else 'updated'} with ID: {self.id}",
            remark=self.order_remark
        )
    

class OrderDetail(models.Model):
    id = models.CharField(max_length=50, primary_key=True, unique=True)
    order = models.ForeignKey(Order_Table, on_delete=models.CASCADE)
    product = models.ForeignKey(Products, on_delete=models.PROTECT,default=1)
    product_name = models.CharField(max_length=255, default='0')
    product_qty = models.IntegerField()
    product_mrp = models.FloatField(null=True, blank=True)
    product_price = models.FloatField(null=True, blank=True)
    gst_amount = models.FloatField(null=True, blank=True)
    taxeble_amount = models.FloatField(null=True, blank=True)
    product_total_price = models.FloatField(null=True, blank=True)
    class Meta:
        db_table = 'orders_details_table'
        permissions = (
            ('view_orderdetail_customer_information', 'ordereetail view Customer Information'),
            ('view_orderdetail_order_status_tracking', 'orderdetail view Order Status Tracking'),
            ('view_orderdetail_order_payment_status', 'orderdetail view Order Payment Status'),
            ('view_orderdetail_Product_Information', 'orderdetail view Products Information'),
            )
    def save(self, *args, **kwargs):
        if not self.id:
            self.id = generate_unique_id(OrderDetail, prefix='ODI')
        super().save(*args, **kwargs)
    def __str__(self):
        return self.order
    
class OrderLogModel(models.Model):
    id = models.CharField(max_length=50, primary_key=True, unique=True)
    order = models.ForeignKey(Order_Table, on_delete=models.CASCADE)
    order_status = models.ForeignKey(OrderStatus, on_delete=models.PROTECT)
    action_by = models.ForeignKey(User, on_delete=models.PROTECT)
    remark = models.TextField()
    action = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        db_table = 'order_log_table'
    def save(self, *args, **kwargs):
        if not self.id:
            self.id = generate_unique_id(OrderLogModel, prefix='OLI')
        super().save(*args, **kwargs)
    def __str__(self):
        return f"category {self.id} by {self.order}"


class BaseModel(models.Model):
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="%(app_label)s_%(class)s_created_by")
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    def save(self, *args, **kwargs):
        request = get_request()
        if request and request.user.is_authenticated:
            if not self.pk:
                self.created_by = request.user
            self.updated_by = request.user
        super().save(*args, **kwargs)

    class Meta:
        abstract = True

class PincodeLocality(BaseModel):
    pincode = models.CharField(max_length=6, unique=False)  # Assuming Indian pin codes (6 digits)
    locality_name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        unique_together = ('pincode', 'locality_name')  # Ensures locality_name is unique for the same pincode
        db_table = 'order_locality_picode'
    def __str__(self):
        return f"{self.locality_name} - {self.pincode}"
    


class OrderValueSetting(models.Model):
    id = models.CharField(max_length=50, primary_key=True, unique=True)
    title = models.CharField(max_length=255)
    payment_type = models.ForeignKey(Payment_Type, on_delete=models.PROTECT)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, default=1)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, default=1)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.id:
            self.id = generate_unique_id(OrderValueSetting, prefix='OVI')
        super().save(*args, **kwargs)
    def __str__(self):
        return f"{self.title} - {self.payment_type} - {self.amount}"
    
    
class AllowStatus(models.Model):
    id = models.CharField(max_length=50, primary_key=True, unique=True)
    name = models.CharField(max_length=50)
    status_code = models.CharField(max_length=20)
    shipment_vendor = models.ForeignKey(ShipmentVendor, on_delete=models.CASCADE)
    class Meta:
        db_table = 'allow_status'
        unique_together = ('name', 'shipment_vendor')
    def save(self, *args, **kwargs):
        if not self.id:
            self.id = generate_unique_id(AllowStatus, prefix='ASI')
        super().save(*args, **kwargs)
    def __str__(self):
        return f"{self.name} ({self.status_code})"

class OrderStatusWorkflow(models.Model):
    id = models.CharField(max_length=50, primary_key=True, unique=True)
    order_status = models.ForeignKey(OrderStatus, on_delete=models.CASCADE)
    shipment_vendor = models.ForeignKey(ShipmentVendor, on_delete=models.CASCADE)
    allow_status = models.ManyToManyField(AllowStatus, related_name='workflows')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'order_status_workflow'
        unique_together = ('order_status', 'shipment_vendor')
    def save(self, *args, **kwargs):
        if not self.id:
            self.id = generate_unique_id(OrderStatusWorkflow, prefix='OWI')
        super().save(*args, **kwargs)
    def __str__(self):
        return f"{self.order_status.name} - {self.shipment_vendor.name}"

class ReturnType(models.Model):
    id = models.CharField(max_length=50, primary_key=True, unique=True)
    name = models.CharField(max_length=50, unique=True)
    status_code = models.CharField(max_length=20)
    class Meta:
        db_table = 'return_type'
    def save(self, *args, **kwargs):
        if not self.id:
            self.id = generate_unique_id(ReturnType, prefix='RTI')
        super().save(*args, **kwargs)
    def __str__(self):
        return f"{self.name} ({self.status_code})"




class LableLayout(BaseModel):
    customer_name = models.BooleanField(default=False,null=True)
    customer_address = models.BooleanField(default=False,null=True)
    customer_phone = models.BooleanField(default=False,null=True)
    customer_email = models.BooleanField(default=False,null=True)
    order_date = models.BooleanField(default=False,null=True)
    invoice_no = models.BooleanField(default=False,null=True)
    order_barcode = models.BooleanField(default=False,null=True)
    sku = models.BooleanField(default=False,null=True)
    item_name = models.BooleanField(default=False,null=True)
    quantity = models.BooleanField(default=False,null=True)
    item_amount = models.BooleanField(default=False,null=True)
    discount = models.BooleanField(default=False,null=True)
    order_gst = models.BooleanField(default=False,null=True)
    order_address = models.BooleanField(default=False,null=True)
    standard_printout = models.BooleanField(default=False,null=True)
    partial = models.BooleanField(default=False,null=True)
    show_logo = models.BooleanField(default=False,null=True)
    logo_images = models.ImageField(upload_to='logo_images/', null=True, blank=True)
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE,null=True, blank=True)
    company = models.ForeignKey(Company, on_delete=models.CASCADE,null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    id = models.CharField(max_length=50, primary_key=True, unique=True)
    class Meta:
        db_table = 'lable_layout'
    def save(self, *args, **kwargs):
        if not self.id:
            self.id = generate_unique_id(LableLayout, prefix='LLI')
        super().save(*args, **kwargs)


class invoice_layout(BaseModel):
    id = models.CharField(max_length=50, primary_key=True, unique=True)

    logo = models.ImageField(upload_to='logo_lable_invoice_images/', null=True, blank=True)
    signature = models.ImageField(upload_to='signature_lable_invoice_images/', null=True, blank=True)

    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, null=True, blank=True)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, db_column='company_id', null=True, blank=True)

    page_setting = models.CharField(max_length=50, null=True, blank=True)

    # Boolean fields default TRUE as you requested
    show_logo = models.BooleanField(default=True, null=True, blank=True)
    show_signature = models.BooleanField(default=True, null=True, blank=True)
    payment_status = models.BooleanField(default=True, null=True, blank=True)

    # All remaining fields (string fields)
    shipped_from = models.BooleanField(default=True, null=True, blank=True)
    customer_contact = models.BooleanField(default=True, null=True, blank=True)
    company_email = models.BooleanField(default=True, null=True, blank=True)
    cin = models.BooleanField(default=True, null=True, blank=True)
    pan = models.BooleanField(default=True, null=True, blank=True)
    gst = models.BooleanField(default=True, null=True, blank=True)
    fssai = models.BooleanField(default=True, null=True, blank=True)
    payment_info = models.BooleanField(default=True, null=True, blank=True)
    customer_address = models.BooleanField(default=True, null=True, blank=True)
    company_contact = models.BooleanField(default=True, null=True, blank=True)
    customer_email = models.BooleanField(default=True, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'invoice_layout'

    def save(self, *args, **kwargs):
        if not self.id:
            self.id = generate_unique_id(invoice_layout, prefix='ILI')
        super().save(*args, **kwargs)





    


class SmsConfig(BaseModel):
    NOTIFICATION_TYPE_CHOICES = [
        ('sms', 'SMS'),
        ('email', 'Email'),
        ('whatsapp', 'WhatsApp'),
    ]

    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    order_status = models.ManyToManyField(OrderStatus, related_name="sms_configs")
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPE_CHOICES)
    
    mobile_number = models.CharField(
        max_length=10,
        validators=[RegexValidator(r'^\d{10}$', message="Enter a valid 10-digit mobile number")],
        help_text="Enter a 10-digit mobile number (without country code)"
    )
    brand_name = models.CharField(max_length=100,blank=True, null=True)
    website = models.URLField(validators=[URLValidator()], blank=True, null=True)
    email = models.EmailField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['company', 'notification_type'],
                name='unique_company_notification_type'
            )
        ]

    def __str__(self):
        return f"{self.company.name} - {self.notification_type}"
