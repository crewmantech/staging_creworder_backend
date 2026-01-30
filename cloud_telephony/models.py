from django.db import models
from django.contrib.auth.models import User
from accounts.models import Company, Branch
from accounts.utils import generate_unique_id
from middleware.request_middleware import get_request

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


class CloudTelephonyVendor(BaseModel):
    id = models.CharField(max_length=50, primary_key=True, unique=True)
    name = models.CharField(max_length=255, unique=True)
    image = models.ImageField(upload_to='cloudtelephony_vendor_images/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'cloud_telephony_vendor_table'
    def save(self, *args, **kwargs):
        if not self.id:
            self.id = generate_unique_id(CloudTelephonyVendor, prefix='CVI')
        super().save(*args, **kwargs)
    def __str__(self):
        return self.name


class CloudTelephonyChannel(BaseModel):
    AUTH_TOKEN_CHOICES = [
        (0, "No Auth"),
        (1, "Bearer Token"),
        (2, "JWT Bearer"),
        (3, "Basic Auth"),
    ]
    STATUS = [
        (0, "Inactive"),
        (1, "Active"),
    ]
    id = models.CharField(max_length=50, primary_key=True, unique=True)
    cloudtelephony_vendor = models.ForeignKey(
        CloudTelephonyVendor, on_delete=models.CASCADE, null=True, blank=True, related_name="cloudtelephony"
    )
    # cloud_telephony_provider_name = models.CharField(max_length=255, null=True, blank=True)
    # logo = models.ImageField(upload_to="cloudtelephony_channel_images/", null=True, blank=True)
    token = models.TextField()
    # auth_token_type = models.IntegerField(choices=AUTH_TOKEN_CHOICES)
    status = models.IntegerField(choices=STATUS)
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE)
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    # user = models.ForeignKey(User, on_delete=models.CASCADE, default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    tenent_id =  models.CharField(max_length=255, null=False)
    username = models.CharField(max_length=255, null=True)
    password = models.CharField(max_length=255, null=True)
    other = models.CharField(max_length=500,null=True)
    class Meta:
        db_table = "cloud_telephony_channel"
    def save(self, *args, **kwargs):
        if not self.id:
            self.id = generate_unique_id(CloudTelephonyChannel, prefix='CTI')
        super().save(*args, **kwargs)
    def __str__(self):
        return f"{self.cloudtelephony_vendor}"
    
from django.core.exceptions import ValidationError

class CloudTelephonyChannelAssign(BaseModel):

    TYPE_CHOICES = (
        (1, "Call Agent"),
        (2, "Monitoring"),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    cloud_telephony_channel = models.ForeignKey(
        'CloudTelephonyChannel', on_delete=models.CASCADE
    )
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE)
    company = models.ForeignKey(Company, on_delete=models.CASCADE)

    type = models.IntegerField(choices=TYPE_CHOICES)
    is_active = models.BooleanField(default=True)
    priority = models.IntegerField(default=1)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    campangin_name = models.CharField(max_length=255, null=True, blank=True)
    agent_username = models.CharField(max_length=255, null=True)
    agent_password = models.CharField(max_length=255, null=True)
    agent_id = models.CharField(max_length=255, null=True)
    camp_id = models.CharField(max_length=255, null=True)
    other = models.CharField(max_length=500, null=True, blank=True)


    class Meta:
        db_table = "telephony_channels_assign_table"
        unique_together = ('user', 'company', 'cloud_telephony_channel')

    def clean(self):
        """
        Django admin + serializer validation
        """

        # RULE 1: Only one Call Agent total
        if self.type == 1:
            exists = CloudTelephonyChannelAssign.objects.filter(
                user=self.user,
                company=self.company,
                type=1
            ).exclude(id=self.id).exists()

            if exists:
                raise ValidationError("Only one Call Agent channel allowed per user")

        # RULE 2: Only one Monitoring active
        if self.type == 2 and self.is_active:
            exists = CloudTelephonyChannelAssign.objects.filter(
                user=self.user,
                company=self.company,
                type=2,
                is_active=True
            ).exclude(id=self.id).exists()

            if exists:
                raise ValidationError("Only one Monitoring channel can be active")

    def save(self, *args, **kwargs):
        # self.full_clean()   # remove this line
        if self.type == 2 and self.is_active:
            CloudTelephonyChannelAssign.objects.filter(
                user=self.user,
                company=self.company,
                type=2,
                is_active=True
            ).exclude(id=self.id).update(is_active=False)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user} - {self.cloud_telephony_channel} ({self.get_type_display()})"


class UserMailSetup(BaseModel):
    name = models.CharField(max_length=255, null=False)
    email = models.EmailField(max_length=255, null=False)
    username = models.CharField(max_length=255, null=False)
    password = models.CharField(max_length=255, null=False)  # Consider encryption here
    hostname = models.CharField(max_length=255, null=False)
    mail_smtp = models.CharField(max_length=255, null=False)
    mail_port = models.IntegerField(null=False)
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE)
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'user_mail_setup_table'

    def __str__(self):
        return f"{self.name} | {self.email} | {self.company.name} | {self.branch.name}"


class CallRecording(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE)

    agent_username = models.CharField(max_length=255)
    number = models.CharField(max_length=20)
    duration = models.CharField(max_length=50)
    call_datetime = models.DateTimeField()

    recording_file = models.FileField(upload_to="call_recordings/")
    recording_original_url = models.TextField()

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "call_recording_table"

    def __str__(self):
        return f"Recording - {self.agent_username} - {self.number}"

import secrets
class SecretKey(models.Model):
    id = models.CharField(max_length=50, primary_key=True, unique=True)

    cloudtelephony_vendor = models.ForeignKey(
        CloudTelephonyVendor,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="vendor_secret_keys"
    )

    secret_key = models.CharField(max_length=255, unique=True)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    deactivated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "cloudtelephony_vendor_secret_key"
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if not self.id:
            self.id = generate_unique_id(SecretKey, prefix="SVK")  # Secret Vendor Key

        if not self.secret_key:
            # Auto generate 64-character secure key
            self.secret_key = secrets.token_hex(32)

        super().save(*args, **kwargs)

    def __str__(self):
        status = "ACTIVE" if self.is_active else "INACTIVE"
        return f"{self.cloudtelephony_vendor.name} - {status}"
    

class CallLog(models.Model):
    call_id = models.CharField(max_length=50, db_index=True)
    call_uuid = models.CharField(max_length=100, blank=True, null=True)

    phone = models.CharField(max_length=20)
    agent_id = models.CharField(max_length=20, blank=True, null=True)

    status = models.CharField(max_length=20)
    direction = models.CharField(max_length=20, blank=True, null=True)

    campaign_id = models.CharField(max_length=20, blank=True, null=True)
    session_id = models.CharField(max_length=50, blank=True, null=True)
    transfer_id = models.CharField(max_length=20, blank=True, null=True)
    job_id = models.CharField(max_length=20, blank=True, null=True)
    hangup_reason = models.CharField(max_length=100, blank=True, null=True)

    raw_payload = models.JSONField(default=dict)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.call_id} - {self.status}"