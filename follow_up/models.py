import random
import string
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import RegexValidator
from accounts.models import Company, Branch, Doctor
from accounts.utils import generate_unique_id
from lead_management.models import LeadStatusModel
from middleware.request_middleware import get_request
from phonenumber_field.modelfields import PhoneNumberField
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
    


import random
import string

class Appointment(BaseModel):

    id = models.CharField(
        max_length=20,
        primary_key=True,
        editable=False
    )

    # 🔗 Reference ID (Lead / FollowUp / Call ID)
    reference_id = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        db_index=True
    )

    APPOINTMENT_STATUS = (
        ("pending", "Pending"),
        ("confirmed", "Confirmed"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
        ("no_show", "No Show"),
    )

    APPOINTMENT_TYPE = (
        ("opd", "OPD"),
        ("online", "Online Consultation"),
        ("emergency", "Emergency"),
    )

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="appointments"
    )

    branch = models.ForeignKey(
        Branch,
        on_delete=models.CASCADE,
        related_name="appointments"
    )

    doctor = models.ForeignKey(
        Doctor,
        on_delete=models.CASCADE,
        related_name="appointments"
    )

    # 🧑 Patient Info
    patient_name = models.CharField(max_length=255, null=True, blank=True)
    patient_phone = PhoneNumberField(null=True, blank=True, db_index=True)
    patient_email = models.EmailField(null=True, blank=True)
    patient_age = models.PositiveIntegerField(null=True, blank=True)
    patient_gender = models.CharField(
        max_length=1,
        choices=[("m", "Male"), ("f", "Female"), ("o", "Other")],
        null=True,
        blank=True
    )

    # 🆔 UHID
    uhid = models.CharField(max_length=20, db_index=True)

    # 🩺 VITALS
    height_cm = models.DecimalField(max_digits=9, decimal_places=2, null=True, blank=True)
    weight_kg = models.DecimalField(max_digits=9, decimal_places=2, null=True, blank=True)
    bmi = models.DecimalField(max_digits=9, decimal_places=2, null=True, blank=True, editable=False)

    # 📝 MEDICAL DETAILS
    complaint = models.TextField(null=True, blank=True)
    diagnosis = models.TextField(null=True, blank=True)
    medicine_prescribed = models.JSONField(default=list, blank=True)
    advice = models.TextField(null=True, blank=True)

    # 🕒 TIME
    appointment_date = models.DateField(null=True, blank=True)
    appointment_time = models.TimeField(null=True, blank=True)
    expected_duration = models.PositiveIntegerField(default=15)

    status = models.CharField(max_length=20, choices=APPOINTMENT_STATUS, default="pending")
    appointment_type = models.CharField(max_length=20, choices=APPOINTMENT_TYPE, default="online")

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_appointments"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # ------------------------
    # ID & UHID GENERATORS
    # ------------------------
    def generate_id(self):
        prefix = "APT"
        random_part = ''.join(random.choices(string.digits, k=6))
        return f"{prefix}{random_part}"

    def generate_uhid(self):
        prefix = "UHID"
        last = Appointment.objects.order_by("-created_at").first()
        next_id = 1
        if last and last.uhid:
            try:
                next_id = int(last.uhid.replace(prefix, "")) + 1
            except Exception:
                pass
        return f"{prefix}{str(next_id).zfill(6)}"

    def save(self, *args, **kwargs):
        if not self.id:
            self.id = self.generate_id()

        # 🔁 Reuse UHID by phone
        if self.patient_phone:
            old = Appointment.objects.filter(
                patient_phone=self.patient_phone
            ).exclude(pk=self.pk).first()
            self.uhid = old.uhid if old else self.generate_uhid()

        # 🧮 BMI
        if self.height_cm and self.weight_kg:
            height_m = float(self.height_cm) / 100
            self.bmi = round(float(self.weight_kg) / (height_m ** 2), 2)

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.id} - {self.patient_name or 'Patient'}"
    


class Appointment_layout(BaseModel):
    id = models.CharField(max_length=50, primary_key=True, unique=True)

    logo = models.ImageField(upload_to='logo_lable_appointment_images/', null=True, blank=True)

    doctor_info =models.BooleanField(default=True, null=True, blank=True)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, db_column='company_id', null=True, blank=True)

    page_setting = models.CharField(max_length=50, null=True, blank=True)
    web_url = models.CharField(max_length=50, null=True, blank=True)
    Appointment_url = models.CharField(max_length=50, null=True, blank=True)
    discriminator = models.CharField(max_length=50, null=True, blank=True)

    # Boolean fields default TRUE as you requested
    
    show_logo = models.BooleanField(default=True, null=True, blank=True)
    show_signature = models.BooleanField(default=True, null=True, blank=True)
    show_advice = models.BooleanField(default=True, null=True, blank=True)
    show_dose = models.BooleanField(default=True, null=True, blank=True)
    
    # All remaining fields (string fields)

    discriminator =models.TextField(null=True, blank=True)
    show_discriminator =  models.BooleanField(default=True, null=True, blank=True)
    customer_number = models.BooleanField(default=True, null=True, blank=True)

    customer_address =models.CharField(max_length=50, null=True, blank=True)
    company_contact = models.CharField(max_length=50, null=True, blank=True)
    company_email = models.CharField(max_length=50, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'appointment_layout'

    def save(self, *args, **kwargs):
        if not self.id:
            self.id = generate_unique_id(Appointment_layout, prefix='ALI')
        super().save(*args, **kwargs)