import random
from django.db import models
from accounts.models import Company
from accounts.utils import generate_unique_id
from middleware.request_middleware import get_request
from django.contrib.auth.models import User
# Create your models here.
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
        
class KYC(BaseModel):
    company = models.OneToOneField(  # Ensures uniqueness
        Company,
        related_name='kyc',
        on_delete=models.CASCADE
    )
    STATUS = [
        (0, "Inactive"),
        (1, "Active"),
    ]
    id = models.CharField(max_length=50, primary_key=True, unique=True)
    gst_state_code = models.CharField(max_length=2, blank=True, null=True)
    select_kyc_type = models.CharField(max_length=50)  # e.g., 'PAN', 'GST', etc.
    pan_card_number = models.CharField(max_length=10, blank=True, null=True)
    pan_card_name = models.CharField(max_length=50)
    pan_dob = models.DateTimeField(blank=True,null=True)
    pan_card = models.ImageField(upload_to='pancards/', blank=True, null=True)
    adhar_response = models.JSONField(blank=True, null=True)  
    upload_adhar = models.ImageField(upload_to='uploads/', blank=True, null=True)
    gst_certificate = models.ImageField(upload_to='uploads/', blank=True, null=True)   # Aadhaar
    partnership_deed = models.ImageField(upload_to='documents/', blank=True, null=True)
    coi_number = models.CharField(max_length=50, blank=True, null=True)
    coi_image = models.ImageField(upload_to='documents/', blank=True, null=True)  # Certificate of Incorporation
    document_type = models.CharField(max_length=100, blank=True, null=True)
    document_id = models.CharField(max_length=50, blank=True, null=True)
    adhar_number = models.CharField(max_length=50, blank=True, null=True)
    document_name = models.CharField(max_length=255, blank=True, null=True)
    rent_agriment = models.ImageField(upload_to='documents/', blank=True, null=True)  # Rent Agreement
    electricity_bill = models.ImageField(upload_to='documents/', blank=True, null=True)
    document_images = models.JSONField(blank=True, null=True)
    upload_digital_sign = models.ImageField(upload_to='degital_sign/', blank=True, null=True)
    gst_number = models.CharField(max_length=15, blank=True, null=True)
    tan_number = models.CharField(max_length=10, blank=True, null=True)
    e_kyc = models.BooleanField(default=False, null=True, blank=True)
    step_1 = models.BooleanField(default=False, null=True, blank=True)
    step_2 = models.BooleanField(default=False, null=True, blank=True)
    step_3 = models.BooleanField(default=False, null=True, blank=True)
    verification_status = models.CharField(
        max_length=50,
        choices=[('PENDING', 'Pending'), ('COMPLETED', 'Completed'), ('REJECTED', 'Rejected')],
        default='PENDING'
    ) 
    status = models.IntegerField(choices=STATUS, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.id:
            self.id = generate_unique_id(KYC, prefix='KYI')
        super().save(*args, **kwargs)

class GSTState(BaseModel):
    id = models.CharField(max_length=50, primary_key=True, unique=True)
    state_name = models.CharField(max_length=100)
    state_code = models.CharField(max_length=5)

    def save(self, *args, **kwargs):
        if not self.id:
            self.id = generate_unique_id(GSTState, prefix='GSI')
        super().save(*args, **kwargs)
    def __str__(self):
        return self.state_name
    




from datetime import datetime, timedelta
from django.utils import timezone
class OTPModel(models.Model):
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    username = models.CharField(max_length=150, blank=True, null=True)
    otp = models.CharField(max_length=6)
    expiration_time = models.DateTimeField()

    def is_expired(self):
        return self.expiration_time < timezone.now()

    @classmethod
    def create_otp(cls, contact_info=None, username=None):
        otp_code = str(random.randint(1000, 9999))
        expiration_time = timezone.now() + timedelta(minutes=5)
        print(otp_code,"--------------96")
        otp_instance = cls.objects.create(
            phone_number=contact_info if contact_info and contact_info.isdigit() else None,
            email=contact_info if contact_info and "@" in contact_info else None,
            username=username if username else None,
            otp=otp_code,
            expiration_time=expiration_time
        )
        return otp_instance