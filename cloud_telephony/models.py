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


class CloudTelephonyChannelAssign(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, default=1)
    cloud_telephony_channel = models.ForeignKey(
        CloudTelephonyChannel, on_delete=models.CASCADE, default=1
    )
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE)
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    # cloud_telephony_provider_name = models.CharField(max_length=255, null=True, blank=True)
    priority = models.IntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    campangin_name = models.CharField(max_length=255, null=True, blank=True)
    agent_username = models.CharField(max_length=255, null=True)
    agent_password = models.CharField(max_length=255, null=True)
    agent_id = models.CharField(max_length=255, null=True)
    camp_id = models.CharField(max_length=255, null=True)
    other = models.CharField(max_length=500,null=True)
    class Meta:
        db_table = "telephony_channels_assign_table"
        unique_together = ('user', 'company')
    def __str__(self):
        return f"{self.cloud_telephony_channel} (agent_username {self.agent_username})"


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
