from django.db import models
# from accounts.models import Company, Branch
from middleware.request_middleware import get_request
from django.contrib.auth.models import User

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
 
        
class ShipmentVendor(models.Model):  # Shipment Vendor Model
    name = models.CharField(max_length=255, unique=True)
    image = models.ImageField(upload_to='shipment_channels_image/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)
    class Meta:
        db_table = 'shipment_vendor_table'

    def __str__(self):
        return self.name


class ShipmentModel(models.Model):  # Shipment Model
    STATUS_CHOICES = [
        (1, "Active"),
        (0, "Inactive")
    ]

    credential_username = models.CharField(max_length=255, null=True, blank=True)
    credential_password = models.CharField(max_length=255, null=True, blank=True)
    credential_email = models.CharField(max_length=255, null=True, blank=True)
    credential_token = models.CharField(max_length=255, null=True, blank=True)
    provider_priority = models.IntegerField()
    status = models.IntegerField(choices=STATUS_CHOICES)
    shipment_channel_id = models.IntegerField()

    shipment_vendor = models.ForeignKey(
        ShipmentVendor, on_delete=models.CASCADE, null=True, blank=True, related_name="shipments"
    )
    branch = models.ForeignKey("accounts.Branch", on_delete=models.CASCADE, null=True, blank=True)
    company = models.ForeignKey("accounts.Company", on_delete=models.CASCADE, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)
    tracking_url = models.URLField(blank=True, null=True)
    class Meta:
        db_table = 'shipment_table'

    def __str__(self):
        return f"Shipment {self.id} by {self.shipment_vendor.name if self.shipment_vendor else 'N/A'}"
    
class CourierServiceModel(BaseModel):
    name = models.CharField(max_length=255)
    api_url=models.TextField(null=False,blank=False)
    remark=models.TextField(null=False,blank=False)
    branch=models.ForeignKey("accounts.Branch",on_delete=models.PROTECT)
    company=models.ForeignKey("accounts.Company",on_delete=models.CASCADE)
    created_at=models.DateTimeField(auto_now_add=True)
    update_at=models.DateTimeField(auto_now=True)

    class Meta:
        db_table='courier_services_table'
        
    def __str__(self):
        return f"Courier name {self.name}, Branch {self.branch.name}"