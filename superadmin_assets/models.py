from django.db import models,IntegrityError
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import Permission
from accounts.models import Company, Branch
from middleware.request_middleware import get_request
from django.contrib.auth.models import User
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError
from django.utils.crypto import get_random_string
import random, string, hashlib
from phonenumber_field.modelfields import PhoneNumberField
from django.utils import timezone

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

class MenuModel(BaseModel):
    name = models.CharField(max_length=255,unique=True)
    url = models.TextField()
    icon=models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    module_name = models.CharField(max_length=255,null=True, blank=True)
    class Meta:
        db_table = 'menu_table'
    def __str__(self):
        return f"{self.id} by {self.name}"
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        content_type, created = ContentType.objects.get_or_create(
            app_label="superadmin_assets",  
            model="menumodel"  
        )
        
        # permission_names = [
        #     "view_all", "view_own", "add", "change_all", "change_own", 
        #     "delete_all", "delete_own", "export_all", "export_own"
        # ]
        
        # for perm_name in permission_names:
        #     Permission.objects.get_or_create(
        #         name=f"{perm_name.replace('_', ' ').capitalize()} {self.name.replace('_', ' ')}",
        #         codename=f"{perm_name}_{self.name.lower().replace(' ', '_')}",
        #         content_type=content_type
        #     )
        
        # Add dynamic permission for viewing the menu itself
        Permission.objects.get_or_create(
            name=f"show_menumodel {self.name}",
            codename=f"show_menumodel_{self.name.lower().replace(' ', '_')}",
            content_type=content_type
        )
    
class SubMenusModel(BaseModel):
    menu =models.ForeignKey(MenuModel,on_delete=models.CASCADE)
    name = models.CharField(max_length=255,unique=True)
    url = models.TextField()
    icon = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    module_name = models.CharField(max_length=255,null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        db_table = 'submenus_table'
    def __str__(self):
        return f"{self.id} by {self.name}"
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        content_type, created = ContentType.objects.get_or_create(
            app_label="superadmin_assets",  
            model="submenusmodel"  
        )
        
        # permission_names = [
        #     "view_all", "view_own", "add", "change_all", "change_own", 
        #     "delete_all", "delete_own", "export_all", "export_own"
        # ]
        
        # for perm_name in permission_names:
        #     Permission.objects.get_or_create(
        #         name=f"{perm_name.replace('_', ' ').capitalize()} {self.name.replace('_', ' ')}",
        #         codename=f"{perm_name}_{self.name.lower().replace(' ', '_')}",
        #         content_type=content_type
        #     )
        
        # Add dynamic permission for viewing the submenu itself
        Permission.objects.get_or_create(
            name=f"show_submenusmodel {self.name}",
            codename=f"show_submenusmodel_{self.name.lower().replace(' ', '_')}",
            content_type=content_type
        )

          
class SettingsMenu(BaseModel):
    name = models.CharField(max_length=255,unique=True)
    url = models.TextField()
    icon = models.TextField()
    component_name = models.TextField()
    status = models.IntegerField(choices=[(0, 'Inactive'), (1, 'Active')], default=1)
    for_user = models.CharField(max_length=255,choices=[('superadmin', 'For Super Admin'), ('admin', 'For Admin'),('both', 'Both')])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    module_name = models.CharField(max_length=255,null=True, blank=True)

    class Meta:
        db_table = 'settings_menu_table'
    def __str__(self):
        return f"{self.id} by {self.name}"
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        content_type, created = ContentType.objects.get_or_create(
            app_label="superadmin_assets",  # Fixed app label
            model="SettingsMenu"  # Fixed model name
        )
        permission_names = ["view","add","change","delete"]
        for perm_name in permission_names:
            Permission.objects.get_or_create(
                name=f"settings_{perm_name.replace('_', ' ').capitalize()} {self.name.replace('_', ' ')}",
                codename=f"settings_{perm_name}_{self.name.lower().replace(' ', '_')}",
                content_type=content_type
            )
        Permission.objects.get_or_create(
            name=f"show_settingsmenu_{self.name}",
            codename=f"show_settingsmenu_{self.name.lower().replace(' ', '_')}",
            content_type=content_type
        )
class PixelCodeModel(BaseModel):
    google_analytics_code = models.TextField()
    meta_pexel_code = models.TextField()
    other_pexel_code = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'pixelcode_table'
    def __str__(self):
        return f"{self.id} by {self.name}"
    
class BennerModel(BaseModel):
    banner_img = models.ImageField(upload_to="banner_images/")
    link = models.TextField()
    title = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    for_user = models.CharField(max_length=255,choices=[('agent', 'For agent'), ('admin', 'For Admin'), ('both', 'Both')],default='both')
    
    class Meta:
        db_table = 'banner_table'
    def __str__(self):
        return f"{self.id} by {self.link}"
    
class ThemeSettingModel(BaseModel):
    name = models.CharField(max_length=255, blank=False, null=False)
    dark_logo = models.ImageField(upload_to="theme_setting_images/")
    light_logo = models.ImageField(upload_to="theme_setting_images/")
    favicon_logo = models.ImageField(upload_to="theme_setting_images/")
    invoice_logo = models.ImageField(upload_to="theme_setting_images/")
    signature = models.ImageField(upload_to="theme_setting_images/")
    primary_color_code = models.CharField(max_length=255, blank=False, null=False)
    page_theme = models.CharField(max_length=255,choices=[('dark', 'Dark'), ('light', 'Light')], default='light')
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE,related_name='theme_branch',null=True, blank=True)
    company = models.ForeignKey(Company, on_delete=models.CASCADE,related_name='theme_company',null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'theme_setting_table'
    def __str__(self):
        return f"{self.id} by {self.name}"
    


class SandboxCredentials(models.Model):
    api_key = models.CharField(max_length=255)
    api_secret = models.CharField(max_length=255)
    api_host = models.URLField()
    is_active = models.BooleanField(default=False)  # Only one can be active

    def __str__(self):
        return f"Sanbox Credentials for {self.api_host} (Active: {self.is_active})"

    def save(self, *args, **kwargs):
        if self.is_active:
            # Deactivate all other SandboxCredentials before saving this one as active
            SandboxCredentials.objects.update(is_active=False)
        super(SandboxCredentials, self).save(*args, **kwargs)


class SMSCredentials(models.Model):
    sms_api_key = models.CharField(max_length=255)
    sms_sender_id = models.CharField(max_length=20)
    api_host = models.URLField()
    is_active = models.BooleanField(default=False)  # Only one can be active

    def __str__(self):
        return f"SMS Credentials: {self.sms_sender_id} (Active: {self.is_active})"

    def save(self, *args, **kwargs):
        if self.is_active:
            # Deactivate all other SMSCredentials before saving this one as active
            SMSCredentials.objects.update(is_active=False)
        super(SMSCredentials, self).save(*args, **kwargs)






class SuperAdminCompany(models.Model):
    class Meta:
        verbose_name_plural = "superadmin companies"

    id = models.CharField(max_length=50, primary_key=True, unique=True)
    account_type_choices = [('current', 'Current Account'), ('savings', 'Savings Account')]
    name = models.CharField(max_length=100, blank=False)
    company_email = models.EmailField(max_length=100, unique=True, null=False)
    company_phone = PhoneNumberField(unique=True, null=False)
    company_website = models.CharField(max_length=100, blank=False)
    company_address = models.CharField(max_length=200, blank=False)
    status = models.BooleanField(default=True)
    created_at = models.DateField(auto_now_add=True)
    updated_at = models.DateField(auto_now=True)
    company_id = models.CharField(max_length=50, blank=True, null=True)
    company_image = models.ImageField(upload_to='company_images/', blank=True, null=True)
    gst = models.CharField(max_length=60, null=True, blank=True)
    pan = models.CharField(max_length=60, null=True, blank=True)
    cin = models.CharField(max_length=60, null=True, blank=True)
    bank_account_no = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        validators=[RegexValidator(regex=r'^\d{1,20}$', message="Bank account number must contain only digits.")],
    )
    city = models.CharField(max_length=100, blank=True, null=True)
    state = models.CharField(max_length=100, blank=True, null=True)
    pincode = models.CharField(max_length=6, blank=True, null=True)
    bank_account_type = models.CharField(max_length=20, null=True, blank=True, choices=account_type_choices)
    bank_name = models.CharField(max_length=120, null=True, blank=True)
    # The above code is defining a variable named `bank_branch_name` in Python.
    bank_branch_name = models.CharField(max_length=120, null=True, blank=True)
    bank_ifsc_code = models.CharField(max_length=40, null=True, blank=True)
    support_email = models.EmailField(max_length=100, null=True, blank=True)

    
    def generate_id(self):
        random_suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
        return f"SUPCMP{random_suffix}"

    def generate_company_id(self):
        while True:
            hash_object = hashlib.sha256(self.name.encode())
            company_id = f"{hash_object.hexdigest()[:5]}{get_random_string(length=5, allowed_chars='0123456789')}"
            if not SuperAdminCompany.objects.filter(company_id=company_id).exists():
                return company_id.upper()

    def save(self, *args, **kwargs):
        if not self.id:
            self.id = self.generate_id()
        if not self.company_id:
            self.company_id = self.generate_company_id()
        
        if SuperAdminCompany.objects.filter(company_email=self.company_email).exclude(id=self.id).exists():
            raise ValidationError({"company_email": "This email is already associated with another company."})
        if SuperAdminCompany.objects.filter(company_phone=self.company_phone).exclude(id=self.id).exists():
            raise ValidationError("This phone number is already in use by another company.")
        
        super().save(*args, **kwargs)
    
    def __str__(self):
        return self.name



class EmailCredentials(models.Model):
    USE_FOR_CHOICES = [
        ("alternate_email", "Alternate Email"),
        ("welcome", "Welcome Email"),
        ("order", "Order Confirmation"),
        ("default", "Default"),
    ]

    name = models.CharField(max_length=255, blank=False, null=False)
    user = models.CharField(max_length=255, blank=False, null=False)
    password = models.CharField(max_length=255, blank=False, null=False)
    smtp_server = models.CharField(max_length=255, blank=False, null=False)
    smtp_port = models.IntegerField(null=False)
    use_for = models.CharField(
        max_length=20,
        choices=USE_FOR_CHOICES,
        default="default",
        blank=False,
        null=False,
        unique = True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "email_setting_table"

    def __str__(self):
        return f"{self.id} by {self.name}"
    
class SupportQuestion(BaseModel):
    PRIORITY_CHOICES = (
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
    )

    question_id = models.CharField(max_length=20, unique=True, editable=False)
    question = models.CharField(max_length=255)
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.question_id:
            last = SupportQuestion.objects.order_by('id').last()
            next_id = last.id + 1 if last else 1
            self.question_id = f"QST-{next_id:04d}"
        super().save(*args, **kwargs)

    def __str__(self):
        return self.question_id


class SupportTicket(BaseModel):
    STATUS_CHOICES = (
        ('open', 'Open'),
        ('in_progress', 'In Progress'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed'),
    )

    ticket_id = models.CharField(max_length=30, unique=True, editable=False)

    company = models.ForeignKey(
    Company,
    on_delete=models.CASCADE,
    related_name="superadmin_support_tickets"
)

    question = models.ForeignKey(SupportQuestion, on_delete=models.CASCADE)

    description = models.TextField(blank=True)
    issue_image = models.ImageField(
        upload_to='support/tickets/issues/', null=True, blank=True
    )

    solution_description = models.TextField(null=True, blank=True)
    solution_image = models.ImageField(
        upload_to='support/tickets/solutions/', null=True, blank=True
    )

    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_support_tickets"
    )

    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='open'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.ticket_id:
            year = timezone.now().year
            last = SupportTicket.objects.filter(
                ticket_id__startswith=f"TCK-{year}"
            ).order_by('id').last()

            last_no = int(last.ticket_id.split('-')[-1]) if last else 0
            self.ticket_id = f"TCK-{year}-{last_no + 1:05d}"

        super().save(*args, **kwargs)

    def __str__(self):
        return self.ticket_id