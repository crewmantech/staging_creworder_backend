from django.db import models
from middleware.request_middleware import get_request
from accounts.models import Company
from django.contrib.auth.models import User
from accounts.models import Branch
from django.utils import timezone
import random
import string

class BaseModel(models.Model):
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="%(class)s_created_by")
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="%(class)s_updated_by")

    def save(self, *args, **kwargs):
        request = get_request()
        if request and request.user.is_authenticated:
            if not self.pk:
                self.created_by = request.user
            self.updated_by = request.user
        super().save(*args, **kwargs)

    class Meta:
        abstract = True

# Create your models here.
class AssetType(BaseModel):
    id = models.CharField(
        primary_key=True,
        max_length=10,
        editable=False,
        unique=True
    )

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="asset_types")
    branch = models.ForeignKey(Branch, on_delete=models.SET_NULL, null=True, blank=True, related_name="asset_types")

    name = models.CharField(max_length=120)
    description = models.TextField(null=True, blank=True)
    requires_serial = models.BooleanField(default=False)
    active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("company", "branch", "name")
        ordering = ["company", "branch", "name"]
    
    def generate_id(self):
        return "AST" + ''.join(random.choices(string.digits, k=6))

    def save(self, *args, **kwargs):
        if not self.id:
            new_id = self.generate_id()
            while AssetType.objects.filter(id=new_id).exists():
                new_id = self.generate_id()
            self.id = new_id
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.company.company_id} - {self.name}"


class Asset(BaseModel):
    """
    Individual physical asset record.
    Each physical device/item is one Asset instance.
    """
    STATUS_CHOICES = [
        ("available", "Available"),
        ("assigned", "Assigned"),
        ("under_maintenance", "Under Maintenance"),
        ("damaged", "Damaged"),
        ("lost", "Lost"),
        ("scrapped", "Scrapped"),
    ]
    id = models.CharField(
        primary_key=True,
        max_length=10,
        editable=False,
        unique=True
    )


    asset_type = models.ForeignKey(AssetType, on_delete=models.CASCADE, related_name="assets")
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="assets")
    branch = models.ForeignKey(Branch, on_delete=models.SET_NULL, null=True, blank=True, related_name="assets")
    name = models.CharField(max_length=150)  # e.g. "Dell XPS 13"
    serial_number = models.CharField(max_length=150, null=True, blank=True)
    model_number = models.CharField(max_length=150, null=True, blank=True)
    purchase_date = models.DateField(null=True, blank=True)
    warranty_end_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default="available")
    notes = models.TextField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("company", "serial_number")
        ordering = ["-created_at"]
        
    def generate_id(self):
        return "ASS" + ''.join(random.choices(string.digits, k=6))

    def save(self, *args, **kwargs):
        if not self.id:
            new_id = self.generate_id()
            while Asset.objects.filter(id=new_id).exists():
                new_id = self.generate_id()
            self.id = new_id
        super().save(*args, **kwargs)

    def __str__(self):
        sn = self.serial_number or "NO-SN"
        return f"{self.asset_type.name} ({sn})"


class AssetAssignment(BaseModel):
    id = models.CharField(
        primary_key=True,
        max_length=10,
        editable=False,
        unique=True
    )

    asset = models.ForeignKey(Asset, on_delete=models.CASCADE, related_name="assignments")
    employee = models.ForeignKey(User, on_delete=models.CASCADE, related_name="asset_assignments")

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="asset_assignments",null=True, blank=True,)
    branch = models.ForeignKey(Branch, on_delete=models.SET_NULL, null=True, blank=True, related_name="asset_assignments")

    assigned_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="asset_assigned_by")
    assigned_on = models.DateField(auto_now_add=True)
    expected_return_date = models.DateField(null=True, blank=True)
    returned_on = models.DateField(null=True, blank=True)
    return_condition = models.CharField(max_length=255, null=True, blank=True)
    active = models.BooleanField(default=True)
    notes = models.TextField(null=True, blank=True)

    class Meta:
        ordering = ["-assigned_on"]
        
    def generate_id(self):
        return "ASA" + ''.join(random.choices(string.digits, k=6))

    def save(self, *args, **kwargs):
        if not self.id:
            new_id = self.generate_id()
            self.company = self.asset.company
            self.branch = self.asset.branch
            while AssetAssignment.objects.filter(id=new_id).exists():
                new_id = self.generate_id()
            self.id = new_id
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.asset} -> {self.employee}"


class AssetLog(BaseModel):
    id = models.CharField(
        primary_key=True,
        max_length=10,
        editable=False,
        unique=True
    )

    asset = models.ForeignKey(Asset, on_delete=models.CASCADE, related_name="logs")

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="asset_logs", null=True, blank=True)
    branch = models.ForeignKey(Branch, on_delete=models.SET_NULL, null=True, blank=True, related_name="asset_logs")

    event = models.CharField(max_length=120)
    by_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="asset_logs_by")
    timestamp = models.DateTimeField(auto_now_add=True)
    metadata = models.JSONField(null=True, blank=True)

    class Meta:
        ordering = ["-timestamp"]
        
    def generate_id(self):
        return "ASL" + ''.join(random.choices(string.digits, k=6))

    def save(self, *args, **kwargs):
        if not self.id:
            new_id = self.generate_id()
            self.company = self.asset.company
            self.branch = self.asset.branch
            while AssetLog.objects.filter(id=new_id).exists():
                new_id = self.generate_id()
            self.id = new_id
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.asset} - {self.event} @ {self.timestamp}"