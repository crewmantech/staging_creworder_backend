import binascii
import hashlib
import os
import pdb
import random
import string
from django.contrib.auth.models import Group
from django.contrib.auth.models import User, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied
from django.db import IntegrityError, models
from django.utils.crypto import get_random_string
from phonenumber_field.modelfields import PhoneNumberField
# from superadmin_assets.models import SubMenusModel,MenuModel
from django.core.validators import RegexValidator
from django.utils.translation import gettext_lazy as _
from datetime import datetime, timedelta, date
from django.core.exceptions import ValidationError
from django.utils.timezone import now

from rest_framework import serializers
from accounts.utils import TEMPLATE_TYPE_CHOICES, TIME_INTERVAL_CHOICES, generate_unique_id
from middleware.request_middleware import get_request
from shipment.models import ShipmentModel


# from django.utils import timezone


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

        
class Module(BaseModel):
    name = models.CharField(max_length=60, null=False, blank=False, unique=True)
    description = models.TextField(blank=False, null=False)
    def __str__(self):
        return self.name


class Package(BaseModel):
    id = models.CharField(max_length=50, primary_key=True, unique=True)
    name = models.CharField(max_length=100, null=False, blank=False)
    type = models.CharField(max_length=20, choices=[('free', 'Free'), ('paid', 'Paid')], blank=False, null=False,
                            default='free')
    monthly_price = models.IntegerField(blank=False, null=False, default=100)
    annual_price = models.IntegerField(blank=False, null=False, default=100)
    quarterly_price = models.IntegerField(blank=False, null=False, default=100)
    description = models.TextField(blank=False, null=False)
    max_employees = models.IntegerField(blank=False, null=False, default=5)
    # created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    status = models.BooleanField(default=True)
    created_at = models.DateField(auto_now_add=True)
    updated_at = models.DateField(auto_now=True)
    max_admin = models.IntegerField(blank=True, null=True)
    setup_fees = models.IntegerField(blank=True, null=True)
    sms_credit = models.IntegerField(default=0, blank=True, null=True)  # Default SMS credits
    whatsapp_credit = models.IntegerField(default=0, blank=True, null=True)  # Default WhatsApp credits
    email_credit = models.IntegerField(default=0, blank=True, null=True)
    def save(self, *args, **kwargs):
        if self.created_by.profile.user_type != 'superadmin':
            raise PermissionDenied("Only superadmins can create packages.")
        if not self.id:
            self.id = generate_unique_id(Package, prefix='PKG')
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name
    
class PackageDetailsModel(BaseModel):
    package = models.ForeignKey("Package", on_delete=models.CASCADE, related_name="packagedetails")
    menu = models.ForeignKey("superadmin_assets.MenuModel", on_delete=models.PROTECT, related_name="menu", blank=True, null=True)
    submenu = models.ForeignKey("superadmin_assets.SubMenusModel", on_delete=models.PROTECT, related_name="submunuid", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    update_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "package_detail_table"

    def __str__(self):
        return f"{self.id} {self.package.name} {self.menu.name if self.menu else 'No Menu'} {self.submenu.name if self.submenu else 'No Submenu'}"


class Company(BaseModel):
    class Meta:
        verbose_name_plural = "companies"
        permissions = (
            ('can_view_own_company', 'Can view own company'),
            ('can_edit_own_company', 'Can edit own company'),
            ('can_delete_own_company', 'Can delete own company'),
            ('can_manage_own_company', 'Can manage own company'),
            ('can_change_company_status', 'Can change company status')
        )

    id = models.CharField(max_length=50, primary_key=True, unique=True)
    payment_freq = [('month', 'Monthly'), ('quarter', "Quarterly"), ('annual', 'Annually')]
    account_type_choices = [('current', 'Current Account'), ('savings', 'Savings Account')]
    name = models.CharField(max_length=100, blank=False)
    company_email = models.EmailField(max_length=100, unique=True, null=False)
    company_phone = PhoneNumberField(unique=True, null=False)
    company_website = models.CharField(max_length=100, blank=False)
    company_address = models.CharField(max_length=200, blank=False)
    package = models.ForeignKey(Package, on_delete=models.CASCADE, default=1)
    status = models.BooleanField(default=True)
    created_at = models.DateField(auto_now_add=True)
    updated_at = models.DateField(auto_now=True)
    company_id = models.CharField(max_length=50, blank=True, null=True)
    company_image = models.ImageField(upload_to='company_images/', blank=True, null=True)
    payment_mode = models.CharField(max_length=20, blank=True, null=True, choices=payment_freq)
    next_payment_date = models.DateField(null=True, blank=True)
    gst = models.CharField(max_length=60, null=True, blank=True)
    pan = models.CharField(max_length=60, null=True, blank=True)
    cin = models.CharField(max_length=60, null=True, blank=True)
    fssai = models.CharField(max_length=60, null=True, blank=True)
    bank_account_no = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        validators=[RegexValidator(regex=r'^\d{1,20}$', message="Bank account number must contain only digits.")],
    )
    city = models.CharField(max_length=100,blank=True, null=True)
    state = models.CharField(max_length=100,blank=True, null=True)
    pincode = models.CharField(max_length=6,blank=True, null=True)
    bank_account_type = models.CharField(max_length=20, null=True, blank=True, choices=account_type_choices)
    bank_name = models.CharField(max_length=120, null=True, blank=True)
    bank_branch_name = models.CharField(max_length=120, null=True, blank=True)
    bank_ifsc_code = models.CharField(max_length=40, null=True, blank=True)
    support_email = models.EmailField(max_length=100, null=True, blank=True)
    is_verify = models.BooleanField(default=False, null=True, blank=True)
    is_agree = models.BooleanField(default=False, null=True, blank=True)
    basic_step = models.BooleanField(default=False, null=True, blank=True)
    
    def generate_id(self):
        """Generate a custom id with prefix CMP and 5 random alphanumeric characters"""
        random_suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
        return f"CMP{random_suffix}"

    def generate_company_id(self):
        """Generate a unique company_id based on the company name"""
        while True:
            hash_object = hashlib.sha256(self.name.encode())
            company_id = f"{hash_object.hexdigest()[:5]}{get_random_string(length=5, allowed_chars='0123456789')}"
            if not Company.objects.filter(company_id=company_id).exists():
                return company_id.upper()

    def save(self, *args, **kwargs):
        system_update = kwargs.pop('system_update', False)
        request = get_request()
        if request :
            user = request.user
        else:
            user = kwargs.pop('user', None)
        if not self.id:  # Creating a new company
            if user and user.profile.user_type != 'superadmin':
                raise PermissionDenied("Only superadmins can create companies.")
        else:  # Updating an existing company
            if not system_update:
                if not (user and (user.is_superuser or user.has_perm('accounts.can_edit_own_company'))):
                    raise PermissionDenied("You do not have permission to edit this company.")

        if not self.id:
            self.id = self.generate_id()

        if not self.company_id:
            self.company_id = self.generate_company_id()

        if Company.objects.filter(company_email=self.company_email).exclude(id=self.id).exists():
            raise serializers.ValidationError({"company_email": "This email is already associated with another company."})

        if Company.objects.filter(company_phone=self.company_phone).exclude(id=self.id).exists():
            raise serializers.ValidationError("This phone number is already in use by another company.")

        try:
            super().save(*args, **kwargs)
        except IntegrityError as e:
            error_message = str(e).lower()
            if "company_email" in error_message:
                raise ValidationError({"company_email": "This email is already registered."})
            elif "company_phone" in error_message:
                raise ValidationError({"company_phone": "This phone number is already registered."})
            else:
                raise ValidationError("A database integrity error occurred.")

        if not self.branches.exists():
            Branch.objects.create(name="Default Branch", company=self, address=self.company_address)

    def __str__(self):
        return self.name

class Branch(BaseModel):
    class Meta:
        verbose_name_plural = "Branches"

    name = models.CharField(max_length=80, blank=False, null=False)
    branch_id = models.CharField(max_length=255, blank=True)
    address = models.CharField(max_length=255, blank=False, null=False)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="branches")
    created_at = models.DateField(auto_now_add=True)
    updated_at = models.DateField(auto_now=True)

    def generate_branch_id(self):
        prefix = self.company.company_id
        characters = string.digits
        random_suffix = ''.join(random.choice(characters) for _ in range(5))
        return prefix + random_suffix

    def save(self, *args, **kwargs):
        is_new = self._state.adding

        if not self.branch_id:
            self.branch_id = self.generate_branch_id()

        super().save(*args, **kwargs)

        if not is_new:
            return

        # ---------- AUTO CREATE PERMISSIONS ----------
        content_type = ContentType.objects.get_for_model(Branch)

        # Global permissions (optional)
        # fixed_permissions = [
        #     ("can_view_all", "Can view all branches"),
        #     # ("can_view_own", "Can view own branch"),
        # ]
        # for codename, label in fixed_permissions:
        #     Permission.objects.get_or_create(
        #         codename=f"branch_{codename}",
        #         name=f"Branch {label}",
        #         content_type=content_type,
        #     )

        # ---------- Branch-specific permission ----------
        company_name = self.company.name.replace(" ", "_").lower()
        branch_name = self.name.replace(" ", "_").lower()

        permission_codename = f"branch_view_{company_name}_{branch_name}"
        permission_name = f"Branch View {self.name} - {self.company.name}"

        try:
            Permission.objects.get_or_create(
                codename=permission_codename,
                name=permission_name,
                content_type=content_type,
            )
        except IntegrityError:
            pass


# class UserRole(models.Model):
#     ROLE_CHOICES = [
#         ('superadmin', 'Super Admin'),
#         ('admin', 'Admin'),
#         ('agent', 'Agent'),
#     ]
#     user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='role')
#     role = models.CharField(max_length=50, choices=ROLE_CHOICES)
#     def __str__(self):
#         return self.user.username


class UserStatus(models.IntegerChoices):
    inactive = 0, "Inactive"
    active = 1, "Active"
    suspended = 2, "Suspended"
    deleted = 3, "Deleted"


class ShiftTiming(BaseModel):
    name = models.CharField(max_length=100, null=False, blank=False)
    branch = models.ForeignKey(Branch, null=True, blank=True, related_name="shifts", on_delete=models.CASCADE)
    start_time = models.TimeField(null=False, blank=False)
    end_time = models.TimeField(null=False, blank=False)

    def __str__(self):
        branch_id = self.branch.branch_id if self.branch else None
        return f'{self.name} - {branch_id}'
        # return f'{self.name} - {self.branch.branch_id}'
    
class Employees(BaseModel):
    gender_choices = [
        ('m', 'Male'),
        ('f', 'Female'),
        ('t', 'Transgender')
    ]

    employment_choices = [
        ('full', 'Full Time'),
        ('part', 'Part Time'),
        ('trainee', 'Trainee'),
        ('intern', 'Internship')
    ]
    ROLE_CHOICES = [
        ('superadmin', 'Super Admin'),
        ('admin', 'Admin'),
        ('agent', 'Agent'),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    status = models.IntegerField(choices=UserStatus.choices, default=UserStatus.active)
    gender = models.CharField(max_length=2, choices=gender_choices, default="m")
    contact_no = PhoneNumberField(null=False, unique=True, blank=False)
    marital_status = models.CharField(max_length=20, choices=[('married', "Married"), ('unmarried', "Unmarried")],default="unmarried")
    date_of_joining = models.DateField(auto_now_add=True)
    daily_order_target = models.IntegerField(blank=True, null=True)
    reporting = models.ForeignKey(User, blank=True, null=True, on_delete=models.CASCADE)
    address = models.TextField(null=True, blank=True)
    employee_id = models.CharField(max_length=50, unique=True, blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, null=True, blank=True)
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, null=True, blank=True, related_name='users')
    professional_email = models.EmailField(null=True, blank=True)
    teamlead=models.ForeignKey(User,on_delete=models.PROTECT,null=True,blank=True,related_name='agent_teamlead')
    manager=models.ForeignKey(User,on_delete=models.PROTECT,null=True,blank=True,related_name='agent_manager')
    enrolment_id = models.CharField(max_length=50, null=True, blank=True)
    profile_image = models.ImageField(upload_to='profile_images/', blank=True, null=True)
    department = models.ForeignKey('Department', on_delete=models.PROTECT, related_name="department_wise_users",null=True, blank=True)
    designation = models.ForeignKey('Designation', on_delete=models.PROTECT, related_name='designation_wise_users',null=True, blank=True)
    login_allowed = models.BooleanField(default=False)
    employment_type = models.CharField(max_length=30, null=True, blank=True, choices=employment_choices)
    user_type = models.CharField(max_length=50, choices=ROLE_CHOICES,default="agent")
    two_way_authentication = models.BooleanField(default=False)
    reffral_code = models.CharField(max_length=30, blank=True, null=True)
    refral_by = models.CharField(max_length=30, null=True, blank=True)
    shift = models.ForeignKey(ShiftTiming, on_delete=models.SET_NULL, null=True, blank=True, related_name="employeesshift")
    def generate_reffral_code(self):
        """Generate a custom id with prefix CMP and 5 random alphanumeric characters"""
        random_suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
        return f"REF{random_suffix}"
    def save(self, *args, **kwargs):
        if not self.reffral_code:
            self.reffral_code = self.generate_reffral_code()
        if not self.employee_id:
            self.employee_id = self.generate_employee_id()
        super().save(*args, **kwargs)

    def generate_employee_id(self):
        prefix = ""
        if self.user.profile.user_type == "superadmin":
            prefix = "SUPER"
        elif self.user.profile.user_type == "admin" or self.user.profile.user_type == "agent":
            # prefix = str(self.user.profile.company.company_id).upper()[:4]
            if self.user.profile.company:
                prefix = str(self.user.profile.company.company_id).upper()[:4]
            else:
                prefix = "NONE"
        length = 8 - len(prefix)
        characters = string.digits
        random_suffix = ''.join(random.choice(characters) for _ in range(length))
        return prefix + random_suffix

    def __str__(self):
        return self.user.username
    

class Notice1(BaseModel):
    title = models.CharField(max_length=255)
    description = models.TextField()
    company = models.ForeignKey(
    Company,
    on_delete=models.CASCADE,
    null=True,
    blank=True
)


    branches = models.ManyToManyField(
        Branch,
        related_name="notices1",
        blank=True
    )

    users = models.ManyToManyField(
        User,
        related_name="notices1",
        blank=True
    )

    

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title


class FormEnquiry(BaseModel):
    class Meta:
        verbose_name_plural = "Form Enquiries"
    id = models.CharField(max_length=50, primary_key=True, unique=True)
    name = models.CharField(max_length=70, blank=False, null=False)
    phone = PhoneNumberField(null=False, blank=False)
    email = models.EmailField(null=False, blank=False)
    message = models.TextField(blank=False, null=False)
    created_at = models.DateField(auto_now_add=True)
    updated_at = models.DateField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.id:
            self.id = generate_unique_id(FormEnquiry, prefix='FOQ')
        super().save(*args, **kwargs)
    def __str__(self):
        return self.id


class SupportTicketStatus(models.IntegerChoices):
    open = 0, "Open"
    pending = 1, "Pending"
    resolved = 2, "Resolved"
    closed = 3, "Closed"


class SupportTicket(BaseModel):
    priority_choices = [
        ('urgent', 'Urgent'),
        ('high', 'High'),
        ('low', 'Low'),
        ('medium', 'Medium')
    ]
    company = models.ForeignKey(Company, blank=False, null=False, on_delete=models.CASCADE)
    subject = models.CharField(max_length=200, null=False, blank=False)
    description = models.TextField(blank=False, null=False)
    status = models.IntegerField(null=False, blank=False, default=SupportTicketStatus.open,
                                 choices=SupportTicketStatus.choices)
    ticket_id = models.CharField(max_length=80, null=True, blank=True)
    agent = models.ForeignKey(User, blank=False, null=False, related_name="support_tickets", on_delete=models.PROTECT)
    type = models.CharField(max_length=20, choices=[('ques', 'Question'), ('problem', 'Problem'),
                                                    ('gen_query', 'General Query')], blank=False, null=False)
    priority = models.CharField(max_length=15, blank=True, null=True, choices=priority_choices)
    created_at = models.DateField(auto_now_add=True)
    updated_at = models.DateField(auto_now=True)
    solution = models.TextField(blank=True,null=True)

    def save(self, *args, **kwargs):
        if not self.ticket_id:
            self.ticket_id = self.generate_ticket_id()
        super().save(*args, **kwargs)

    def generate_ticket_id(self):
        characters = string.ascii_uppercase + string.digits
        ticket_id = ''.join(random.choice(characters) for _ in range(10))

        while SupportTicket.objects.filter(ticket_id=ticket_id).exists():
            ticket_id = ''.join(random.choice(characters) for _ in range(10))

        return ticket_id

    def __str__(self):
        return self.ticket_id


class Department(BaseModel):
    id = models.CharField(max_length=50, primary_key=True, unique=True)
    name = models.CharField(max_length=200, null=False, blank=False)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="departments", null=True, blank=True)
    created_at = models.DateField(auto_now_add=True)  # Automatically sets the time when the object is first created
    updated_at = models.DateField(auto_now_add=True)
    class Meta:
        unique_together = ("name", "company")
    # created_by = models.ForeignKey(User, related_name="department_created_by", on_delete=models.SET_NULL, null=True, blank=True)
    # updated_by = models.ForeignKey(User, related_name="department_updated_by", on_delete=models.SET_NULL, null=True, blank=True)
    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        is_new = self._state.adding

        # Generate unique ID if not set
        if not self.id:
            self.id = generate_unique_id(Department, prefix='DEP')

        # Try to get company from logged-in user if not provided
        if not self.company:
            request = get_request()
            if request and hasattr(request.user, "profile") and getattr(request.user.profile, "company", None):
                self.company = request.user.profile.company

        print("Before super().save():", self.company)

        super().save(*args, **kwargs)

        # Proceed only when department is newly created
        if is_new:
            content_type, _ = ContentType.objects.get_or_create(
                app_label=self._meta.app_label,
                model=self._meta.model_name
            )

            # ✅ Global permissions (fixed)
            fixed_permissions = [
                ("can_view_all", "Can view all departments"),
                ("can_view_own", "Can view own department"),
            ]
            for codename, label in fixed_permissions:
                Permission.objects.get_or_create(
                    codename=f"department_{codename}",
                    name=f"Department {label}",
                    content_type=content_type,
                )

            # ✅ Company-specific permission
            company = self.company
            if company:
                company_id = company.id
                company_name = company.name
            else:
                company_id = "superadmin"
                company_name = "Superadmin"

    
            perm_name = "can_view"
            permission_name = f"Department {perm_name.replace('_', ' ').capitalize()} {self.name.replace('_', ' ')} - {company_name}"
            permission_codename = f"department_{perm_name}_{self.name.lower().replace(' ', '_')}"

            print(permission_codename, permission_name, "-----------------466")

            try:
                Permission.objects.get_or_create(
                    codename=permission_codename,
                    name=permission_name,
                    content_type=content_type,
                )
            except IntegrityError:
                pass
            # codename = f"department_can_view_{self.name.lower().replace(' ', '_')}_{company_id}_{self.id}"
            # readable_name = f"Can view Department '{self.name}' ({company_name})"
            # print(codename,readable_name,"-----------------466")
            # try:
            #     Permission.objects.get_or_create(
            #         codename=readable_name,
            #         name=codename,
            #         content_type=content_type,
            #     )
            # except IntegrityError:
            #     pass

    def __str__(self):
        return f"{self.name} - {self.company.name if self.company else 'Superadmin'}"

    def delete(self, *args, **kwargs):
        content_type = ContentType.objects.get_for_model(self)
        Permission.objects.filter(
            content_type=content_type,
            name__icontains=self.name
        ).delete()
        super().delete(*args, **kwargs)
class Designation(BaseModel):
    id = models.CharField(max_length=50, primary_key=True, unique=True)
    name = models.CharField(max_length=200, null=False, blank=False)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="designations", null=True, blank=True)
    created_at = models.DateField(auto_now_add=True)
    updated_at = models.DateField(auto_now_add=True)
    # created_by = models.ForeignKey(User, related_name="designation_created_by", on_delete=models.SET_NULL, null=True, blank=True)
    # updated_by = models.ForeignKey(User, related_name="designation_updated_by", on_delete=models.SET_NULL, null=True, blank=True)
    class Meta:
        unique_together = ("name", "company")
    def save(self, *args, **kwargs):
        if not self.id:
            self.id = generate_unique_id(Designation, prefix='DEG')
        super().save(*args, **kwargs)
    def __str__(self):
        return self.name


class Leaves(BaseModel):
    duration_choices = [
        ('full', 'Full Day'),
        ('first', 'First Half'),
        ('second', 'Second Half')
    ]

    type_choices = [
        ('casual', 'Casual'),
        ('sick', 'Sick'),
        ('earned', 'Earned')
    ]

    status_choices = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('disapprove','Disapprove')
    ]
    id = models.CharField(max_length=50, primary_key=True, unique=True)

    user = models.ForeignKey(User, related_name="leaves", on_delete=models.CASCADE, null=False, blank=False)
    duration = models.CharField(max_length=30, null=True, blank=True, choices=duration_choices)
    type = models.CharField(max_length=30, null=False, blank=False, choices=type_choices)
    status = models.CharField(max_length=30, null=False, blank=False, choices=status_choices)
    reason = models.CharField(max_length=500, null=False, blank=False)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, null=True, blank=True, related_name="leaves")
    attachment = models.ImageField(upload_to='leave_attachments/', blank=True, null=True)
    class Meta:
        permissions = (
            ('can_approve_disapprove_leaves', 'Can approve disapprove leaves'),
        )
    def save(self, *args, **kwargs):
        if not self.id:
            self.id = generate_unique_id(Leaves, prefix='LEV')
        super().save(*args, **kwargs)
    def __str__(self):
        return f'{self.user.username} - {self.reason}'


class Holiday(BaseModel):
    id = models.CharField(max_length=50, primary_key=True, unique=True)
    occasion = models.CharField(max_length=100, null=False, blank=False)
    date = models.DateField(null=False, blank=False)
    department = models.ForeignKey(Department, null=True, blank=True, on_delete=models.PROTECT)
    designation = models.ForeignKey(Designation, null=True, blank=True, on_delete=models.PROTECT)
    branch = models.ForeignKey(Branch, null=True, blank=True, related_name="holidays", on_delete=models.CASCADE)
    
    def save(self, *args, **kwargs):
        if not self.id:
            self.id = generate_unique_id(Holiday, prefix='HOD')
        super().save(*args, **kwargs)
    def __str__(self):
        return f'{self.occasion} - {self.date}'


class Award(BaseModel):
    id = models.CharField(max_length=50, primary_key=True, unique=True)
    title = models.CharField(max_length=120, null=False, blank=False, unique=True)
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, null=True, blank=True, related_name="awards")
    summary = models.CharField(max_length=255, null=True, blank=True)
    
    def save(self, *args, **kwargs):
        if not self.id:
            self.id = generate_unique_id(Award, prefix='AWD')
        super().save(*args, **kwargs)
    def __str__(self):
        return f'{self.title} - {self.branch.branch_id}'


class Appreciation(BaseModel):
    id = models.CharField(max_length=50, primary_key=True, unique=True)
    award = models.ForeignKey(Award, on_delete=models.CASCADE, null=False, blank=False)
    user = models.ForeignKey(User, related_name="appreciations", null=False, blank=False, on_delete=models.CASCADE)
    date_given = models.DateField(null=False, blank=False)
    summary = models.CharField(max_length=500, null=True, blank=True)
    award_image = models.ImageField(upload_to='award_images/', blank=True, null=True)

    def save(self, *args, **kwargs):
        if not self.id:
            self.id = generate_unique_id(Appreciation, prefix='APN')
        super().save(*args, **kwargs)
    def __str__(self):
        return f'{self.award.title} - {self.user.username}'
    

class Shift_Roster(BaseModel):
    id = models.CharField(max_length=50, primary_key=True, unique=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="shift_rosters")
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, null=True, blank=True, related_name="shift_rosters")
    ShiftTiming = models.ForeignKey(ShiftTiming, on_delete=models.CASCADE, null=True, blank=True, related_name="shift_rosters")  # New Field
    date = models.DateField(null=False, blank=False, default=date.today)
    remark = models.TextField(null=True, blank=True)
    created_at = models.DateField(auto_now_add=True)
    updated_at = models.DateField(auto_now=True)
    
    class Meta:
        db_table = 'shift_roster_table'

    def save(self, *args, **kwargs):
        if not self.id:
            self.id = generate_unique_id(Shift_Roster, prefix='SHR')
        super().save(*args, **kwargs)
    def __str__(self):
        return f'{self.user.username} - {self.branch.branch_id} '



from django.utils import timezone

class Attendance(BaseModel):
    ATTENDANCE_CHOICES = [('A', 'A'), ('P', 'P')]
    WORKING_CHOICES = [('home', 'Home'), ('office', 'Office'), ('other', 'Other')]

    id = models.CharField(max_length=50, primary_key=True, unique=True)
    user = models.ForeignKey(User, related_name="attendances", on_delete=models.CASCADE)
    branch = models.ForeignKey(Branch, related_name="attendance_branch", on_delete=models.CASCADE, null=True, blank=True)
    company = models.ForeignKey(Company, related_name="attendance_company", on_delete=models.CASCADE, null=True, blank=True)
    shift = models.ForeignKey(ShiftTiming, on_delete=models.PROTECT, related_name="shift_wise_attendances", null=True)
    date = models.DateField(default=timezone.now)
    working_from = models.CharField(max_length=80, choices=WORKING_CHOICES, default="office")
    attendance = models.CharField(max_length=2, choices=ATTENDANCE_CHOICES, default="P")

    clock_in = models.TimeField(null=True, blank=True)
    clock_out = models.TimeField(null=True, blank=True)
    total_active_hours = models.DurationField(default=timedelta)

    def save(self, *args, **kwargs):
        if not self.id:
            self.id = generate_unique_id(Attendance, prefix='ATE')
        super().save(*args, **kwargs)

    def update_summary(self):
        """Recalculate first clock-in, last clock-out and total active hours"""
        sessions = self.sessions.all().order_by("clock_in")
        if sessions.exists():
            self.clock_in = sessions.first().clock_in
            self.clock_out = sessions.last().clock_out or self.clock_out

            total = timedelta()
            for s in sessions:
                if s.clock_in and s.clock_out:
                    total += (datetime.combine(self.date, s.clock_out) -
                              datetime.combine(self.date, s.clock_in))
            self.total_active_hours = total
        self.save()


class AttendanceSession(models.Model):
    id = models.CharField(max_length=50, primary_key=True, unique=True)
    attendance = models.ForeignKey(Attendance, related_name="sessions", on_delete=models.CASCADE)
    clock_in = models.TimeField()
    clock_out = models.TimeField(null=True, blank=True)
    duration = models.DurationField(default=timedelta)

    def save(self, *args, **kwargs):
        if not self.id:
            self.id = generate_unique_id(AttendanceSession, prefix='ATS')
        if self.clock_in and self.clock_out:
            self.duration = (datetime.combine(date.today(), self.clock_out) -
                             datetime.combine(date.today(), self.clock_in))
        super().save(*args, **kwargs)

class AllowedIP(BaseModel):
    id = models.CharField(max_length=50, primary_key=True, unique=True)
    ip_address = models.GenericIPAddressField()
    ip_from_choices = [('home', 'Home'),('office', 'Office')]
    ip_from = models.CharField(max_length=100, choices=ip_from_choices, null=False,default='office')
    branch = models.ForeignKey('Branch', related_name="ip_address_branch", on_delete=models.CASCADE)
    company = models.ForeignKey('Company', blank=False, default=1, null=False, on_delete=models.CASCADE, related_name="ip_address_company")
    created_at = models.DateTimeField(default=now)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.id:
            self.id = generate_unique_id(AllowedIP, prefix='ALP')
        super().save(*args, **kwargs)
    def __str__(self):
        return f"{self.ip_address} for {self.branch.branch_id}"
    
class CustomAuthGroup(BaseModel):
    id = models.CharField(max_length=50, primary_key=True, unique=True)
    group = models.OneToOneField(Group, on_delete=models.CASCADE, related_name='custom_group')
    branch = models.ForeignKey(Branch, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_branch')
    company = models.ForeignKey(Company, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_company')
    name = models.CharField(max_length=255, null=False)
    remark = models.TextField(blank=False, null=False)
    created_at = models.DateField(auto_now_add=True)
    updated_at = models.DateField(auto_now=True)
    for_user = models.CharField(max_length=255,choices=[('agent', 'For agent'), ('admin', 'For Admin'), ('both', 'Both')],default='admin' )
    class Meta:
        db_table = 'custom_auth_group'
        unique_together = ('name', 'branch', 'company')

    def save(self, *args, **kwargs):
        if not self.id:
            self.id = generate_unique_id(CustomAuthGroup, prefix='CAG')
        super().save(*args, **kwargs)
    def __str__(self):
        return f"{self.name} ({self.company} - {self.branch} - {self.group.id})"

    # def delete(self, *args, **kwargs):
    #     from django.contrib.auth.models import User
    #     print(self.group.user_set.exists(),"--------------------557")
    #     # Check if any user is assigned to this group
    #     if self.group.user_set.exists():
    #         raise Exception("Cannot delete this role — it is assigned to one or more users.")
    #     super().delete(*args, **kwargs)


     
class PickUpPoint(BaseModel):
    id = models.CharField(max_length=50, primary_key=True, unique=True)
    pickup_location_name = models.CharField(max_length=255)  # <-- New field
    
    contact_person_name = models.CharField(max_length=255)
    contact_number = PhoneNumberField()
    contact_email = models.EmailField(max_length=100, null=False)
    alternate_contact_number = PhoneNumberField(null=True, blank=True)
    complete_address = models.CharField(max_length=255, null=False)
    landmark = models.CharField(max_length=255, null=False)
    pincode = models.IntegerField(null=False)
    city = models.CharField(max_length=200, null=False)
    state = models.CharField(max_length=200, null=False)
    country = models.CharField(max_length=200, null=False)
    
    is_verified = models.BooleanField(default=False)
    status = models.BooleanField(default=False)
    
    branches = models.ManyToManyField(Branch, related_name="pickup_branches")
    company = models.ForeignKey(Company, blank=False, null=False, on_delete=models.CASCADE, related_name="pickup_company")
    
    vendor = models.ForeignKey(
        ShipmentModel, blank=True, null=True, on_delete=models.SET_NULL, related_name="pickup_vendor"
    )
    vendor_response = models.JSONField(null=True,blank=True)
    pickup_code = models.CharField(max_length=200,null=True,blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'pick_up_point_table'
        # No uniqueness constraint on pickup_location_name
        # You can optionally add ordering or other Meta options
    def save(self, *args, **kwargs):
        if not self.id:
            self.id = generate_unique_id(PickUpPoint, prefix='PUP')
        super().save(*args, **kwargs)
    def __str__(self):
        return f"{self.pickup_location_name or self.contact_person_name} - {self.complete_address} ({self.pincode})"


class UserTargetsDelails(BaseModel):
    """
    Represents target-related data for users, including daily, weekly, and achieved targets.
    """
    month_choice = [
    ('january', 'January'),
    ('february', 'February'),
    ('march', 'March'),
    ('april', 'April'),
    ('may', 'May'),
    ('june', 'June'),
    ('july', 'July'),
    ('august', 'August'),
    ('september', 'September'),
    ('october', 'October'),
    ('november', 'November'),
    ('december', 'December'),
    ]
    id = models.BigAutoField(primary_key=True, verbose_name=_("ID"))  
    daily_amount_target = models.DecimalField(max_digits=10, decimal_places=2, verbose_name=_("Daily Amount Target"))
    daily_orders_target = models.PositiveIntegerField(verbose_name=_("Daily Orders Target"))
    monthly_amount_target = models.DecimalField(max_digits=12, decimal_places=2, verbose_name=_("Monthly Amount Target"))
    monthly_orders_target = models.PositiveIntegerField(verbose_name=_("Monthly Orders Target"))
    user = models.ForeignKey('auth.User',on_delete=models.CASCADE,verbose_name=_("User"),related_name='targets')
    achieve_target = models.BooleanField(default=False, verbose_name=_("Achieve Target"))
    in_use = models.BooleanField(default=True, verbose_name=_("In Use"))
    monthyear = models.CharField(max_length=20, blank=False, null=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    branch = models.ForeignKey(Branch, related_name="Target_branch",on_delete=models.CASCADE)
    company = models.ForeignKey(Company, blank=False, null=False, on_delete=models.CASCADE,related_name="Target_Company")


    class Meta:
        db_table = 'user_targets_details_table'
        verbose_name = _("Target Table")
        verbose_name_plural = _("Target Tables")
        ordering = ['-id']  
        constraints = [
            models.CheckConstraint(check=models.Q(daily_amount_target__gte=0), name='check_daily_amount_target_positive'),
            models.CheckConstraint(check=models.Q(monthly_amount_target__gte=0), name='check_monthly_amount_target_positive'),
            models.CheckConstraint(check=models.Q(daily_orders_target__gte=0), name='check_daily_orders_target_positive'),
            models.CheckConstraint(check=models.Q(monthly_orders_target__gte=0), name='check_monthly_orders_target_positive'),
            models.UniqueConstraint(fields=['user', 'monthyear'], name='unique_user_monthyear_target'),
        ]

    def __str__(self):
        return f"Target for User {self.user_id} - {self.daily_amount_target}"

    def save(self, *args, **kwargs):
        # today = date.today()
        # current_month = today.strftime("%B").lower()
        # selected_month = self.month.lower()
        # if current_month==selected_month:
        #     UserTargetsDelails.objects.filter(models.Q(in_use=True), models.Q(user=self.user)).update(in_use=False)
        super().save(*args, **kwargs)

class AdminBankDetails(BaseModel):
    account_number = models.CharField(max_length=255)
    re_account_number = models.CharField(max_length=255)
    ACCOUNT_TYPE_CHOICES = [('saving_account', 'Saving Account'),('current_account', 'Current Account'),('salary_account', 'Salary Account'),]
    account_type = models.CharField(max_length=100, choices=ACCOUNT_TYPE_CHOICES, null=False)
    bank_name = models.CharField(max_length=255, null=True, blank=True)
    ifsc_code = models.CharField(max_length=255, null=False)
    account_holder_name = models.CharField(max_length=255, null=False)
    branch_name = models.CharField(max_length=255, null=False)
    user = models.ForeignKey('auth.User', related_name='admin_bank_details_user', on_delete=models.CASCADE)
    PRIORITY_CHOICES = [(1, 'First'),(2, 'Second'),(3, 'Third'),]
    priority = models.IntegerField(choices=PRIORITY_CHOICES, null=False)
    branch = models.ForeignKey('Branch', related_name="admin_bank_details_branch", on_delete=models.CASCADE,blank=True, null=True)
    company = models.ForeignKey('Company', blank=True, null=True, on_delete=models.CASCADE, related_name="admin_bank_details_company")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        db_table = 'admin_bank_details_table'
        unique_together = ('user', 'priority')

    def __str__(self):
        return f"{self.user.username} {self.bank_name} {self.account_number}"

    def clean(self):
        if self.account_number != self.re_account_number:
            raise ValidationError("Re-entered account number must match the account number.")

        if AdminBankDetails.objects.filter(user=self.user, priority=self.priority).exclude(pk=self.pk).exists():
            raise ValidationError(f"Priority {self.priority} already exists for this user.")
    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)


class QcTable(BaseModel):
    question = models.TextField(null=False)
    # branch = models.ForeignKey('Branch', related_name="qc_branch", on_delete=models.CASCADE)
    # company = models.ForeignKey('Company', blank=False, default=1, null=False, on_delete=models.CASCADE, related_name="qc_company")
    created_at = models.DateTimeField(default=now)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        db_table='qc_table'
    def __str__(self):
        return self.question
    
    
class StickyNote(BaseModel):
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        db_table='sticky_note_table'
    def __str__(self):
        return self.content
    

class CompanyInquiry(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    full_name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=255)
    contact_number = models.CharField(max_length=15,unique=True)
    company_name = models.CharField(max_length=255,unique=True)
    company_email = models.EmailField(unique=True)
    company_phone = models.CharField(max_length=15,unique=True)
    company_website = models.URLField(unique=True)
    company_address = models.TextField()

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')  # New status field
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        db_table='company_inquiry'
    def __str__(self):
        return f"Inquiry from {self.full_name} for {self.company_name}"
    

class Enquiry(models.Model):
    full_name = models.CharField(max_length=255)
    email = models.EmailField()
    phone_number = models.CharField(max_length=15)
    message = models.TextField()
    admin_message = models.TextField(blank=True, null=True)
    status = models.BooleanField(default=False)  # Default is False
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Enquiry from {self.full_name} ({self.email})"
    

class CompanyMessageUsage(models.Model):
    company = models.ForeignKey("Company", on_delete=models.CASCADE, related_name="message_usage")
    package = models.ForeignKey(Package, on_delete=models.CASCADE, related_name="package_usage")
    month = models.IntegerField(default=now().month)
    year = models.IntegerField(default=now().year)
    sms_used = models.IntegerField(default=0)
    whatsapp_used = models.IntegerField(default=0)

    class Meta:
        unique_together = ("company", "month", "year")

    def __str__(self):
        return f"{self.company.name} - {self.month}/{self.year} SMS: {self.sms_used}, WhatsApp: {self.whatsapp_used}"




# def send_message(company, message_type):
#     """
#     Function to send SMS or WhatsApp message and deduct from the company's monthly quota.
#     """
#     package = company.package  # Get the assigned package

#     # Get or create usage record for current month
#     usage, created = CompanyMessageUsage.objects.get_or_create(
#         company=company,
#         package=package,
#         month=now().month,
#         year=now().year,
#     )

#     if message_type == "sms":
#         if usage.sms_used >= package.sms_credit:
#             raise PermissionDenied("SMS credit limit reached for this month.")
#         usage.sms_used += 1  # Increment SMS usage

#     elif message_type == "whatsapp":
#         if usage.whatsapp_used >= package.whatsapp_credit:
#             raise PermissionDenied("WhatsApp credit limit reached for this month.")
#         usage.whatsapp_used += 1  # Increment WhatsApp usage

#     usage.save()  # Save updated usage record
#     return f"{message_type.capitalize()} message sent successfully!"

class ReminderNotes(BaseModel):
    order_id = models.CharField(max_length=100)
    waybill_number = models.CharField(max_length=100)
    attempt_status = models.CharField(max_length=50)
    remark = models.TextField(blank=True, null=True)
    subject = models.CharField(max_length=200, blank=True, null=True)
    attempt = models.CharField(max_length=200, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    branch = models.ForeignKey('Branch', related_name="remindernotes", on_delete=models.CASCADE,blank=True, null=True)
    company = models.ForeignKey('Company', blank=True, null=True, on_delete=models.CASCADE)
    def __str__(self):
        return f"{self.order_id} - {self.attempt_status}"


class Agreement(models.Model):
    title = models.CharField(max_length=255, blank=False, null=False)
    text = models.TextField()
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Agreement created by {self.created_by.username} on {self.created_at}"
    

class Others(models.Model):
    name = models.CharField(max_length=50)
    class Meta:
        permissions = (
            ('allow_otp_login_others', 'Can Allow Otp Login Others'),
            ('login_allow_Ip_others', 'Can login Allow IP Others'),
            ('view_number_masking_others', 'Can view Number Masking Others'),
            ('view_own_lead_others', 'Can view own lead others'),
            ('view_all_lead_others', 'Can view all lead others'),
            ('view_manager_lead_others', 'Can view manager lead others'),
            ('view_teamlead_lead_others', 'Can view team lead lead others'),
            ('view_own_followup_others', 'Can view own followup others'),
            ('view_all_followup_others', 'Can view all followup others'),
            ('view_manager_followup_others', 'Can view manager followup others'),
            ('view_teamlead_followup_others', 'Can view team lead followup others'),
            ('chat_user_permission_others', 'Chat user permission others'),
            ('view_own_Notice_others', 'Can view own Notice others'),
            ('view_all_Notice_others', 'Can view all Notice others'),
            ('view_customer_information_others', ' view Customer Information other'),
            ('view_order_status_tracking_others', ' view Order Status Tracking ohter'),
            ('view_order_payment_status_others', ' view Order Payment Status other'),
            ('view_Product_Information_others', ' view Product Information other'),
            ('view_own_order_others', 'Can view own order others'),
            ('view_all_order_others', 'Can view all order others'),
            ('view_own_branch_order_others','Can view own branch order others'),
            ('view_manager_order_others', 'Can view manager order others'),
            ('view_teamlead_order_others', 'Can view teamlead order others'),
            ('edit_order_others', 'Can edit order others'),
            ('edit_order_status_others', 'Can edit order status others'),
            ('edit_order_payment_status_others', 'Can Order Payment Statusothers'),
            ('view_search_bar_others', 'view search bar others'),
            ('force_attendance_others', 'Can force attendance others'),
            ('create_group_chat_others', 'create group chat others'),
            ('view_click_team_order_others', 'Can click team order others'),
            ('view_branch_switcher_others', 'view branch switcher others'),
            ('view_team_deliverd_performance_others', 'view team deliverd performance others'),
            ('force_appointment_others', 'Can force appointment others'),
            ('view_own_appointment_others', 'Can view own appointment others'),
            ('view_all_appointment_others', 'Can view all appointment others'),
            ('view_manager_appointment_others', 'Can view manager appointment others'),
            ('view_teamlead_appointment_others', 'Can view team lead appointment others'),
            ('edit_appointment_status_others', 'Can edit appointment status others'),

            )
    def __str__(self):
        return self.name
    
class Extra(models.Model):
    name = models.CharField(max_length=50)
    class Meta:
        permissions = (
            ('can_import_employee_extra', 'Can import employee extra'),
            ('can_import_order_extra', 'Can import order extra'),
            ('can_import_follow_up_extra', 'Can import follow up extra'),
            ('can_import_lead_extra', 'Can import lead extra'),
            ('can_export_employee_extra', 'Can export employee extra'),
            ('can_export_lead_extra', 'Can export lead extra'),
            ('can_export_order_extra', 'Can export order extra'),
            ('can_export_follow_up_extra', 'Can export follow up extra'),
            ('can_export_leave_extra', 'Can export leave extra'),
            ('can_export_shift_extra', 'Can export shift extra'),
            ('can_export_shiftroster_extra', 'Can export shiftroster extra'),
            ('can_export_apperciation_extra', 'Can export apperciation extra'),
           
            )
    def __str__(self):
        return self.name
    

class QcScore(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='qc_scores')
    question = models.ForeignKey('QcTable', on_delete=models.CASCADE, related_name='question_scores')
    score = models.FloatField()  # store AVERAGE score
    feedback = models.TextField(null=True, blank=True)
    rating_count = models.PositiveIntegerField(default=0)
    scored_at = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'qc_score'
        # unique_together = ('user', 'question')  # Prevent duplicate scoring

    def __str__(self):
        return f"{self.user.username} - Q{self.question.id} Score: {self.score}"

import uuid

class CompanyUserAPIKey(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    api_key = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    status = models.BooleanField(default=True)
    class Meta:
        unique_together = ('user', 'company')

    def __str__(self):
        return f"{self.user} - {self.company}"
    
from rest_framework.authtoken.models import Token
class ExpiringToken(models.Model):
    key = models.CharField(max_length=40, primary_key=True)
    user = models.OneToOneField(
        User,
        related_name='auth_token_data',
        on_delete=models.CASCADE
    )
    created = models.DateTimeField(auto_now_add=True)
    last_used = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'expiring_token_data'

    def save(self, *args, **kwargs):
        if not self.key:
            self.key = self.generate_key()
        return super().save(*args, **kwargs)

    def generate_key(self):
        return binascii.hexlify(os.urandom(20)).decode() 




class LoginLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    username_attempt = models.CharField(max_length=200, null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=[("success", "Success"), ("failed", "Failed")])
    reason = models.CharField(max_length=255, null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user} - {self.status} - {self.timestamp}"

# from django.utils.timezone import now, timedelta

class LoginAttempt(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)


class OTPAttempt(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    used = models.BooleanField(default=False)
    timestamp = models.DateTimeField(auto_now_add=True)



class InterviewApplication(BaseModel):
    # -------------------------
    # BASIC DETAILS (Mandatory)
    # -------------------------
    name = models.CharField(max_length=255)            # required
    mobile = models.CharField(max_length=20)           # required

    email = models.EmailField(blank=True, null=True)
    location = models.CharField(max_length=255, blank=True, null=True)
    preferred_location = models.CharField(max_length=255, blank=True, null=True)

   
    gender = models.CharField(max_length=20, blank=True, null=True)
    dob = models.DateField(blank=True, null=True)
    qualification = models.CharField(max_length=255, blank=True, null=True)

    total_exp = models.DecimalField(max_digits=4, decimal_places=1, blank=True, null=True)
    current_salary = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    expected_salary = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    notice_period = models.CharField(max_length=100, blank=True, null=True)

    position = models.CharField(max_length=255, blank=True, null=True)
    job_code = models.CharField(max_length=50, blank=True, null=True)
 
    designation = models.CharField(max_length=255, blank=True, null=True)
    source = models.CharField(max_length=255, blank=True, null=True)  # Referral, LinkedIn, Naukri

    interview_date = models.DateField(blank=True, null=True)
  

    interview_mode = models.CharField(max_length=100, blank=True, null=True)  # Online, Offline, Phone
   

    remarks = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=255, blank=True, null=True)  # simple text

    offered_salary = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    offer_status = models.CharField(max_length=100, blank=True, null=True)

    joining_date = models.DateField(blank=True, null=True)


    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    branch = models.ForeignKey(Branch, related_name="interview_branch", on_delete=models.CASCADE, null=True, blank=True)
    company = models.ForeignKey(Company, related_name="interview_company", on_delete=models.CASCADE, null=True, blank=True)
    def __str__(self):
        return self.name



class CompanySalary(BaseModel):
    company = models.OneToOneField(
        Company,
        on_delete=models.CASCADE,
        related_name="salary"
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.company.name} - {self.amount}"



class Doctor(BaseModel):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="doctor_profile"
    )

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="doctors"
        
    )

    # ✅ Multiple branches + nullable
    branches = models.ManyToManyField(
        Branch,
        related_name="doctors"
    )

    registration_number = models.CharField(
        max_length=100,
        unique=True,
        null=True,
        blank=True
    )

    degree = models.CharField(
        max_length=255,
        null=True,
        blank=True
    )

    specialization = models.CharField(
        max_length=255,
        null=True,
        blank=True
    )

    experience_years = models.PositiveIntegerField(
        default=0,
        null=True,
        blank=True
    )

    address = models.TextField(null=True, blank=True)

    # ✅ Doctor Signature
    doctor_sign = models.ImageField(
        upload_to="doctor/signatures/",
        null=True,
        blank=True
    )

    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.user.username if self.user else f"Doctor - {self.id}"


class Crud(models.Model):
    name = models.CharField(max_length=50)
    class Meta:
        permissions = (
            ('can_edit_lead_crud', 'Can edit lead crud'),
            ('can_delete_lead_crud', 'Can delete lead crud'),
            ('can_edit_follow_up_crud', 'Can edit follow up crud'),
            ('can_delete_follow_up_crud', 'Can delete follow up crud'),
            ('can_edit_appointment_crud', 'Can edit appointment crud'),
            ('can_delete_appointment_crud', 'Can delete appointment crud'),
            )
    def __str__(self):
        return self.name


class CallQcTable(BaseModel):
    question = models.TextField(null=False)
    # branch = models.ForeignKey('Branch', related_name="qc_branch", on_delete=models.CASCADE)
    # company = models.ForeignKey('Company', blank=False, default=1, null=False, on_delete=models.CASCADE, related_name="qc_company")
    created_at = models.DateTimeField(default=now)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        db_table='call_qc_table'
    def __str__(self):
        return self.question
    

class CallQcScore(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='call_qc_scores')
    question = models.ForeignKey('CallQcTable', on_delete=models.CASCADE, related_name='call_question_scores')
    score = models.FloatField()  # store AVERAGE score
    feedback = models.TextField(null=True, blank=True)
    rating_count = models.PositiveIntegerField(default=0)
    scored_at = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'call_qc_score'
        # unique_together = ('user', 'question')  # Prevent duplicate scoring

    def __str__(self):
        return f"{self.user.username} - Q{self.question.id} Score: {self.score}"


class EmailSchedule(BaseModel):
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="email_schedules",
        null=True,
        blank=True
    )
    email = models.EmailField()
    branch = models.ForeignKey(
        Branch,
        on_delete=models.CASCADE,
        related_name="email_schedules"
    )
    time_interval = models.CharField(
        max_length=10,
        choices=TIME_INTERVAL_CHOICES
    )
    template_type = models.CharField(
        max_length=20,
        choices=TEMPLATE_TYPE_CHOICES
    )

    is_active = models.BooleanField(default=True)
    last_sent_at = models.DateTimeField(null=True, blank=True)
    next_run_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "email_schedules"
        ordering = ["-created_at"]
        # unique_together = (
        #     "email",
        #     "branch",
        #     "time_interval",
        #     "template_type"
        # )

    def __str__(self):
        return f"{self.email} | {self.branch.name} | {self.time_interval} | {self.template_type}"