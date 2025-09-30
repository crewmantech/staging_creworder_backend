import random
import string
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import RegexValidator
from accounts.models import Company, Branch
from lead_management.models import LeadStatusModel
from middleware.request_middleware import get_request

phone_regex = RegexValidator(
    regex=r'^\+?1?\d{9,15}$',
    message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed."
)

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
        
class Follow_Up(BaseModel):
    # FOLLOW_STATUS_CHOICES = [
    #     ("pending", 'Pending'),
    #     ("responded", 'Responded'),
    #     ("deleted", 'Deleted'),
    # ]
    SNOOZE_CHOICES = [
        ("pending", 'Pending'),
        ("snooze", 'Snooze'),
    ]

    followup_id = models.CharField(max_length=10, unique=True, editable=False)
    customer_name = models.CharField(max_length=255)
    customer_phone = models.CharField(validators=[phone_regex], max_length=17, blank=False)
    reminder_date = models.DateTimeField()
    description = models.TextField()
    follow_status = models.ForeignKey(LeadStatusModel,max_length=255,on_delete=models.CASCADE)
    snooze = models.CharField(max_length=255,choices=SNOOZE_CHOICES)
    follow_add_by = models.ForeignKey(User, related_name='user_id', on_delete=models.CASCADE) 
    call_id = models.CharField(max_length=50, null=True, blank=True)
    branch = models.ForeignKey(Branch, related_name="followup_branch", on_delete=models.CASCADE,blank=True, null=True,)
    company = models.ForeignKey(Company, blank=True, null=True, on_delete=models.CASCADE, related_name="followup_company")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        db_table = 'follow_up_table'

    def generate_id(self):
        """Generate a custom id with prefix CMP and 5 random alphanumeric characters"""
        return f"FUP{''.join(random.choices(string.ascii_uppercase + string.digits, k=6))}"

    def save(self, *args, **kwargs):
        if not self.followup_id:
            unique = False
            while not unique:
                new_id = self.generate_id()
                if not Follow_Up.objects.filter(followup_id=new_id).exists():
                    self.followup_id = new_id
                    unique = True
        super().save(*args, **kwargs)

    def __str__(self):
        return self.followup_id

    


class Notepad(BaseModel):
    authID = models.ForeignKey(User, on_delete=models.CASCADE)
    note = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        db_table = 'notepad_table'
    def __str__(self):
        return f"Note {self.id} by {self.authID}"