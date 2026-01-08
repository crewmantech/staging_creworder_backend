from datetime import datetime
from datetime import timedelta
from django.utils import timezone
import pdb
import re
from django.contrib.auth.models import Group,Permission 
from django.contrib.contenttypes.models import ContentType
from rest_framework import serializers
# from rest_framework.authtoken.models import Token
from accounts.models import ExpiringToken as Token
from staging_creworder_backend import settings
from lead_management.models import Lead, LeadSourceModel
from orders.models import  Products
from services.email.email_service import send_email
from .models import  Agreement, AttendanceSession, CompanyInquiry, CompanySalary, CompanyUserAPIKey, Doctor, Enquiry, InterviewApplication, QcScore, ReminderNotes, StickyNote, User, Company, Package,Employees, Notice1, Branch, FormEnquiry, SupportTicket, Module, \
    Department, Designation, Leaves, Holiday, Award, Appreciation, ShiftTiming, Attendance,Shift_Roster,PackageDetailsModel,CustomAuthGroup,\
    PickUpPoint,UserTargetsDelails,AdminBankDetails,AllowedIP,QcTable
import string
import random
from superadmin_assets.serializers import SubMenuSerializer,MenuSerializer
from superadmin_assets.models import SubMenusModel,MenuModel
from phonenumbers import parse, is_valid_number, format_number, PhoneNumberFormat, NumberParseException

class BranchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Branch
        fields = ['name', 'address', 'company', 'id']

class ModuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Module
        fields = '__all__'

class CompanySerializer(serializers.ModelSerializer):
    total_user_count = serializers.SerializerMethodField()
    package_name = serializers.SerializerMethodField()
    branches = BranchSerializer(many=True, read_only=True)
    company_phone = serializers.CharField(max_length=15)
    class Meta:
        model = Company
        fields = ['id', 'name', 'company_email', 'company_phone', 'company_website', 'company_address', 'status',
                  'created_at', 'updated_at', 'company_id', 'company_image', 'package_name', 'package', 'payment_mode',
                  'total_user_count', 'branches', 'gst', 'pan', 'cin', 'fssai', 'bank_account_no', 'bank_account_type',
                  'bank_name', 'bank_branch_name', 'bank_ifsc_code', 'support_email','is_verify','state','city','pincode','is_agree','basic_step']
        read_only_fields = ('id', 'company_id')
    def validate_company_phone(self, value):
        """
        Validate the phone number and normalize it to E.164 format.
        """
        phone_number_str = str(value)  # Convert to string if not already

        # Add "+91" if the phone number does not start with "+"
        if not phone_number_str.startswith("+"):
            phone_number_str = f"+91{phone_number_str}"

        try:
            # Parse and validate the phone number
            parsed_phone = parse(phone_number_str, "IN")
            if not is_valid_number(parsed_phone):
                raise serializers.ValidationError("The phone number entered is not valid.")
            # Return formatted phone number in E.164 format
            return format_number(parsed_phone, PhoneNumberFormat.E164)
        except NumberParseException:
            raise serializers.ValidationError("The phone number entered is not valid.")

    def get_total_user_count(self, obj):
        count = Employees.objects.filter(company_id=obj.id).count()
        return count

    def get_package_name(self, obj):
        name = obj.package.name
        return name

class PackageDetailsSerializer(serializers.ModelSerializer):
    menu_name=serializers.SerializerMethodField()
    menu_url=serializers.SerializerMethodField()
    menu_icon=serializers.SerializerMethodField()
    sub_menu_name=serializers.SerializerMethodField()
    sub_menu_url=serializers.SerializerMethodField()
    module_name=serializers.SerializerMethodField()
    sub_menu_module_name =serializers.SerializerMethodField()
    class Meta:
        model = PackageDetailsModel
        fields = '__all__'
    def get_menu_url(self, data):
        return data.menu.url if data.menu else None
    def get_sub_menu_url(self,data):
        return data.submenu.url if data.submenu else None
    def get_menu_name(self,data):
        return data.menu.name if data.menu else None
    def get_module_name(self,data):
        return data.menu.module_name if data.menu  else None
    def get_sub_menu_module_name(self,data):
        return data.menu.module_name if data.menu  else None
    def get_sub_menu_name(self,data):
        return data.submenu.name if data.submenu else None
    def get_menu_icon(self,data):
        return data.menu.icon if data.menu else None


class PackageSerializer(serializers.ModelSerializer):
    packagedetails = PackageDetailsSerializer(many=True, read_only=True)
    class Meta:
        model = Package
        fields = '__all__'
        read_only_fields = ['id']

class FormEnquirySerializer(serializers.ModelSerializer):
    phone = serializers.CharField(max_length=15)
    class Meta:
        model = FormEnquiry
        fields = '__all__'
        read_only_fields = ['id']
    def validate_phone(self, value):
        """
        Validate the phone number and normalize it to E.164 format.
        """
        phone_number_str = str(value)  # Convert to string if not already

        # Add "+91" if the phone number does not start with "+"
        if not phone_number_str.startswith("+"):
            phone_number_str = f"+91{phone_number_str}"

        try:
            # Parse and validate the phone number
            parsed_phone = parse(phone_number_str, "IN")
            if not is_valid_number(parsed_phone):
                raise serializers.ValidationError("The phone number entered is not valid.")
            # Return formatted phone number in E.164 format
            return format_number(parsed_phone, PhoneNumberFormat.E164)
        except NumberParseException:
            raise serializers.ValidationError("The phone number entered is not valid.")

# class UserRoleSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = UserRole
#         fields = '__all__'


# class UserRoleCreateSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = UserRole
#         exclude = ['user']


class UserProfileSerializer(serializers.ModelSerializer):
    contact_no = serializers.CharField(max_length=15)
    class Meta:
        model = Employees
        fields = '__all__'
    def validate_contact_no(self, value):
        """
        Validate the phone number and normalize it to E.164 format.
        """
        phone_number_str = str(value)  # Convert to string if not already

        # Add "+91" if the phone number does not start with "+"
        if not phone_number_str.startswith("+"):
            phone_number_str = f"+91{phone_number_str}"

        try:
            # Parse and validate the phone number
            parsed_phone = parse(phone_number_str, "IN")
            if not is_valid_number(parsed_phone):
                raise serializers.ValidationError("The phone number entered is not valid.")
            # Return formatted phone number in E.164 format
            return format_number(parsed_phone, PhoneNumberFormat.E164)
        except NumberParseException:
            raise serializers.ValidationError("The phone number entered is not valid.")

class UserProfileCreateSerializer(serializers.ModelSerializer):
    contact_no = serializers.CharField(max_length=15)
    department_name = serializers.SerializerMethodField()
    designation_name = serializers.SerializerMethodField()

    class Meta:
        model = Employees
        exclude = ["user"]  # keep existing behaviour, extra SerializerMethodFields will be included

    def validate_contact_no(self, value):
        """
        Validate the phone number and normalize it to E.164 format.
        If user provided number without country code, assume India (+91).
        """
        phone_number_str = str(value).strip()

        # If it doesn't start with +, assume Indian number and prepend +91
        if not phone_number_str.startswith("+"):
            # remove any leading zeros / spaces before prefixing
            phone_number_str = phone_number_str.lstrip("0").replace(" ", "")
            phone_number_str = f"+91{phone_number_str}"

        try:
            # Parse and validate the phone number
            parsed_phone = parse(phone_number_str, "IN")
            if not is_valid_number(parsed_phone):
                raise serializers.ValidationError("The phone number entered is not valid.")
            # Return formatted phone number in E.164 format
            return format_number(parsed_phone, PhoneNumberFormat.E164)
        except NumberParseException:
            raise serializers.ValidationError("The phone number entered is not valid.")

    def get_department_name(self, obj):
        try:
            if obj and getattr(obj, "department", None):
                dept = obj.department
                return getattr(dept, "name", dept)  # return name if FK, else raw value
            return None
        except Exception:
            return None

    def get_designation_name(self, obj):
        try:
            if obj and getattr(obj, "designation", None):
                desg = obj.designation
                return getattr(desg, "name", desg)
            return None
        except Exception:
            return None
class TeamUserProfile(serializers.ModelSerializer):
    user_id = serializers.IntegerField(source="user.id")  # Fetch User ID from User table
    first_name = serializers.SerializerMethodField()
    last_name = serializers.SerializerMethodField()
    email = serializers.SerializerMethodField()
    manager_name = serializers.SerializerMethodField()
    contact_no = serializers.CharField(max_length=15)
    username = serializers.SerializerMethodField()

    class Meta:
        model = Employees
        exclude = ['user']  # Excluding 'user' field from the serializer

    def get_first_name(self, obj):
        return obj.user.first_name if obj.user else None

    def get_last_name(self, obj):
        return obj.user.last_name if obj.user else None

    def get_email(self, obj):
        return obj.user.email if obj.user else None
    
    def get_username(self, obj):
        return obj.user.username if obj.user else None
    
    def get_manager_name(self, obj):
        if obj.manager:
            return f"{obj.manager.first_name} {obj.manager.last_name}"
        return None

    def validate_contact_no(self, value):
        """
        Validate the phone number and normalize it to E.164 format.
        """
        phone_number_str = str(value)  # Convert to string if not already

        if not phone_number_str.startswith("+"):
            phone_number_str = f"+91{phone_number_str}"

        try:
            parsed_phone = parse(phone_number_str, "IN")
            if not is_valid_number(parsed_phone):
                raise serializers.ValidationError("The phone number entered is not valid.")
            return format_number(parsed_phone, PhoneNumberFormat.E164)
        except NumberParseException:
            raise serializers.ValidationError("The phone number entered is not valid.")

        
class NoticeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notice1
        fields = '__all__'


class UserSerializer(serializers.ModelSerializer):
    profile = UserProfileCreateSerializer()
    role = serializers.SerializerMethodField()
    activity = serializers.SerializerMethodField()
    branch_name = serializers.SerializerMethodField() 
    
    class Meta:
        model = User
        fields = ['id', 'username', 'password',  'first_name', 'last_name', 'email', 'last_login', 'date_joined',
                  'is_staff', 'profile','role','activity','branch_name']
        extra_kwargs = {
            'password': {'write_only': True}
        }
    def get_branch_name(self, user):
        try:
            return user.profile.branch.name if user.profile.branch else None
        except:
            return None
    def get_role(self, user):
        # Get all groups assigned to this user
        user_groups = user.groups.all()

        # Fetch CustomAuthGroups linked to these groups
        custom_groups = CustomAuthGroup.objects.filter(group__in=user_groups)

        # Serialize using your CustomAuthGroupSerializer
        return CustomAuthGroupSerializer(custom_groups, many=True, context=self.context).data
    
    def get_activity(self, user):
        token = Token.objects.filter(user=user).first()
        if not token:
            existing_token =  False  # No token means inactive

        # Check if token is older than 15 minutes (inactivity timeout)
        elif timezone.now() - token.last_used > timedelta(minutes=15):
            existing_token =  False  # Token expired
        else:
            existing_token =  True
        return "online" if existing_token else "offline"
    def create(self, validated_data):
        profile_data = validated_data.pop("profile")
        user = User.objects.create_user(**validated_data)
        Employees.objects.create(user=user, **profile_data)
        return user
    

    # def update(self, instance, validated_data):
    #     profile_data = validated_data.pop('profile', None)
    #     instance.username = validated_data.get('username', instance.username)
    #     instance.first_name = validated_data.get('first_name', instance.first_name)
    #     instance.last_name = validated_data.get('last_name', instance.last_name)
    #     instance.email = validated_data.get('email', instance.email)
    #     instance.is_staff = validated_data.get('is_staff', instance.is_staff)
    #     instance.save()
    #     if profile_data:
    #         profile = instance.profile
    #         pdb.set_trace()
    #         for attr, value in profile_data.items():
    #             setattr(profile, attr, value)
    #         profile.save()
    #     return instance
    def update(self, instance, validated_data):
    # Pop profile data from validated data
        profile_data = validated_data.pop('profile', None)

        # Update User fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value if value is not None else getattr(instance, attr))
        instance.save()

        # Update UserProfile fields, if provided
        if profile_data:
            profile = instance.profile
            for attr, value in profile_data.items():
                # Use the current value of the field if it's not provided in the request
                setattr(profile, attr, value if value is not None else getattr(profile, attr))
            profile.save()

        return instance

class UserSignupSerializer(serializers.ModelSerializer):
    company = CompanySerializer()
    contact_no = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'password', 'email', 'company', 'contact_no']

    def create(self, validated_data):
        company_data = validated_data.pop("company")
        contact_no = validated_data.pop("contact_no")
        package = Package.objects.get(id=1)
        company = Company.objects.create(package=package, **company_data)
        user = User.objects.create_user(**validated_data)
        Employees.objects.create(
            user=user,
            contact_no=contact_no,
            gender="m",
            status=True,
            marital_status="unmarried",
            company=company
        )

        return user


class SupportTicketSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupportTicket
        fields = '__all__'
        read_only_fields = ('company', 'agent', 'ticket_id')


class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = ['id', 'name', 'company', 'created_by', 'updated_by', 'created_at', 'updated_at']
        read_only_fields = ['company', 'created_by', 'updated_by', 'created_at', 'updated_at','id']







class DesignationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Designation
        fields = ['id', 'name', 'company', 'created_by', 'updated_by', 'created_at', 'updated_at']
        read_only_fields = ['company', 'created_by', 'updated_by', 'created_at', 'updated_at','id']


class LeaveSerializer(serializers.ModelSerializer):
    class Meta:
        model = Leaves
        fields = '__all__'
        read_only_fields = ['id']

class HolidaySerializer(serializers.ModelSerializer):
    class Meta:
        model = Holiday
        fields = '__all__'
        read_only_fields = ['id']


class AwardSerializer(serializers.ModelSerializer):
    class Meta:
        model = Award
        fields = '__all__'
        read_only_fields = ['id']


class AppreciationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Appreciation
        fields = '__all__'
        read_only_fields = ['id']


class ShiftSerializer(serializers.ModelSerializer):
    branches = serializers.PrimaryKeyRelatedField(
        queryset=Branch.objects.all(),
        many=True
    )

    class Meta:
        model = ShiftTiming
        fields = [
            "id",
            "name",
            "company",
            "branches",
            "start_time",
            "end_time",
            "created_at",
        ]

class ShiftRosterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Shift_Roster
        fields = ['user', 'branch', 'ShiftTiming', 'date', 'remark']  # Added 'ShiftTiming'
        read_only_fields = ['id']
    def validate(self, data):
        # Validate start and end dates
        start_date = self.context['request'].data.get('startdate', None)
        end_date = self.context['request'].data.get('enddate', None)

        if not start_date:
            raise serializers.ValidationError({"startdate": "Start date is required."})

        try:
            data['start_date'] = datetime.strptime(start_date, "%Y-%m-%d").date()
        except ValueError:
            raise serializers.ValidationError({"startdate": "Invalid date format. Expected 'YYYY-MM-DD'."})

        if end_date:
            try:
                data['end_date'] = datetime.strptime(end_date, "%Y-%m-%d").date()
            except ValueError:
                raise serializers.ValidationError({"enddate": "Invalid date format. Expected 'YYYY-MM-DD'."})

        # Ensure end date is after start date if provided
        if end_date and data['start_date'] > data['end_date']:
            raise serializers.ValidationError({"enddate": "End date must be after start date."})

        # Validate ShiftTiming
        shift_id = self.context['request'].data.get('ShiftTiming', None)
        if not shift_id:
            raise serializers.ValidationError({"ShiftTiming": "ShiftTiming is required."})
        try:
            ShiftTiming.objects.get(id=shift_id)
        except ShiftTiming.DoesNotExist:
            raise serializers.ValidationError({"ShiftTiming": "Invalid ShiftTiming ID."})

        return data

class AttendanceSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AttendanceSession
        fields = ["id", "clock_in", "clock_out", "duration"]


class AttendanceSerializer(serializers.ModelSerializer):
    sessions = AttendanceSessionSerializer(many=True, read_only=True)
    user_name = serializers.SerializerMethodField()
    clock_in_active = serializers.SerializerMethodField()
    clock_out_active = serializers.SerializerMethodField()
    shift_name = serializers.SerializerMethodField()

    class Meta:
        model = Attendance
        fields = "__all__"
        read_only_fields = ["id", "user", "company", "branch", "total_active_hours",
                            "first_clock_in", "last_clock_out"]

    def get_user_name(self, obj):
        return getattr(obj.user, "username", None)

    def get_shift_name(self, obj):
        return obj.shift.name if obj.shift else None

    def get_clock_in_active(self, obj):
        return obj.sessions.filter(clock_out__isnull=True).exists()

    def get_clock_out_active(self, obj):
        last_session = obj.sessions.order_by("-clock_in").first()
        return bool(last_session and last_session.clock_out)
    
class AuthGroupSerializers(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = '__all__'

class BranchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Branch
        fields = ['id', 'name', 'address']   


class CompanySerializer1(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = ['id', 'name']  # Include relevant fields from Company


class PermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permission
        fields = ['id', 'name', 'codename']

class GroupSerializer(serializers.ModelSerializer):
    permissions = PermissionSerializer(many=True, read_only=True)

    class Meta:
        model = Group
        fields = ['id', 'name', 'permissions']

class CustomAuthGroupSerializer(serializers.ModelSerializer):
    group = GroupSerializer()
    branch = BranchSerializer(read_only=True)
    company = CompanySerializer1(read_only=True)
    branch_id = serializers.PrimaryKeyRelatedField(
        queryset=Branch.objects.all(), source='branch', write_only=True, required=False, allow_null=True
    )
    company_id = serializers.PrimaryKeyRelatedField(
        queryset=Company.objects.all(), source='company', write_only=True, required=False, allow_null=True
    )

    class Meta:
        model = CustomAuthGroup
        fields = ['id', 'group', 'name','branch', 'company', 'remark', 'branch_id', 'company_id', 'created_at', 'updated_at','for_user']
        read_only_fields = ['id']

    def create(self, validated_data):
        request = self.context.get('request')
        if request and request.user.profile.user_type == 'superadmin':
            # Set branch and company to None if superadmin
            validated_data['branch'] = None
            validated_data['company'] = None

        group_data = validated_data.pop('group')
        group = Group.objects.create(**group_data)

        custom_auth_group = CustomAuthGroup.objects.create(group=group, **validated_data)
        return custom_auth_group

    def update(self, instance, validated_data):
        request = self.context.get('request')
        if request and request.user.profile.user_type == 'superadmin':
            # Set branch and company to None if superadmin
            validated_data['branch'] = None
            validated_data['company'] = None

        group_data = validated_data.pop('group', None)
        if group_data:
            group_serializer = GroupSerializer(instance.group, data=group_data, partial=True)
            group_serializer.is_valid(raise_exception=True)
            group_serializer.save()

        return super().update(instance, validated_data)
    



class PickUpPointSerializer(serializers.ModelSerializer):
    contact_number = serializers.CharField(max_length=15)
    alternate_contact_number = serializers.CharField(max_length=15, required=False, allow_blank=True)
    vendor_name = serializers.CharField(source='vendor.shipment_vendor.name', read_only=True)
    class Meta:
        model = PickUpPoint
        fields = '__all__'
        read_only_fields = ['id']

    def validate_contact_number(self, value):
        """
        Validate the phone number and normalize it to E.164 format.
        """
        phone_number_str = str(value)
        if not phone_number_str.startswith("+"):
            phone_number_str = f"+91{phone_number_str}"
        try:
            parsed_phone = parse(phone_number_str, "IN")
            if not is_valid_number(parsed_phone):
                raise serializers.ValidationError("The phone number entered is not valid.")
            return format_number(parsed_phone, PhoneNumberFormat.E164)
        except NumberParseException:
            raise serializers.ValidationError("The phone number entered is not valid.")

    def validate_alternate_contact_number(self, value):
        if not value:
            return None
        phone_number_str = str(value)
        if not phone_number_str.startswith("+"):
            phone_number_str = f"+91{phone_number_str}"
        try:
            parsed_phone = parse(phone_number_str, "IN")
            if not is_valid_number(parsed_phone):
                raise serializers.ValidationError("The alternate phone number is not valid.")
            return format_number(parsed_phone, PhoneNumberFormat.E164)
        except NumberParseException:
            raise serializers.ValidationError("The alternate phone number is not valid.")

    def validate(self, data):
        """
        Ensure pickup_location_name is unique per company + branches.
        """
        pickup_location_name = data.get('pickup_location_name')
        company = data.get('company')
        branches = data.get('branches')  # this is a related field (ManyToMany)

        if pickup_location_name and company and branches:
            qs = PickUpPoint.objects.filter(
                pickup_location_name=pickup_location_name,
                company=company,
            )

            if self.instance:
                qs = qs.exclude(id=self.instance.id)

            qs = qs.filter(branches__in=branches).distinct()

            if qs.exists():
                raise serializers.ValidationError(
                    f"A pickup point with name '{pickup_location_name}' already exists for the same company and branch."
                )

        return data


class PermissionSerializer1(serializers.ModelSerializer):
    class Meta:
        model = Permission
        fields = ['id', 'name', 'codename', 'content_type']


class UserTargetSerializer(serializers.ModelSerializer):
    username = serializers.SerializerMethodField()
    name = serializers.SerializerMethodField()
    company_name = serializers.CharField(source='company.name', read_only=True)
    branch_name = serializers.CharField(source='branch.name', read_only=True)
    user_name = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = UserTargetsDelails
        fields = '__all__'
    

    def get_username(self, obj):
        try:
            return obj.user.username
        except User.DoesNotExist:
            return None
        except Exception:
            return None
    def get_name(self, obj):
        try:
            return f"{obj.user.first_name} {obj.user.last_name}" if obj.user else None
        except User.DoesNotExist:
            return None
        except Exception:
            return None
        
class AdminBankDetailsSerializers(serializers.ModelSerializer):
    class Meta:
        model = AdminBankDetails
        fields = '__all__'

class AllowedIPSerializers(serializers.ModelSerializer):
    class Meta:
        model = AllowedIP
        fields = '__all__'
        read_only_fields = ['id']

    def validate(self, data):
        """Check if the IP address already exists for the same branch."""
        ip_address = data.get("ip_address")
        branch = data.get("branch")

        if AllowedIP.objects.filter(ip_address=ip_address, branch=branch).exists():
            raise serializers.ValidationError("Duplicate IP not allowed for the same branch.")

        return data
        
class QcSerialiazer(serializers.ModelSerializer):
    class Meta:
        model =QcTable
        fields='__all__'


class UpdateTeamLeadManagerSerializer(serializers.ModelSerializer):
    contact_no = serializers.CharField(max_length=15)
    class Meta:
        model = Employees
        fields = ['teamlead', 'manager','contact_no']

    # def validate_contact_no(self, value):
    #     """
    #     Validate the phone number and normalize it to E.164 format.
    #     """
    #     phone_number_str = str(value)  # Convert to string if not already

    #     # Add "+91" if the phone number does not start with "+"
    #     if not phone_number_str.startswith("+"):
    #         phone_number_str = f"+91{phone_number_str}"

    #     try:
    #         # Parse and validate the phone number
    #         parsed_phone = parse(phone_number_str, "IN")
    #         if not is_valid_number(parsed_phone):
    #             raise serializers.ValidationError("The phone number entered is not valid.")
    #         # Return formatted phone number in E.164 format
    #         return format_number(parsed_phone, PhoneNumberFormat.E164)
    #     except NumberParseException:
    #         raise serializers.ValidationError("The phone number entered is not valid.")
 # You can make `created_at` and `updated_at` read-only





class NewPasswordSerializer(serializers.Serializer):
    new_password = serializers.CharField(required=True, write_only=True)

    def validate_new_password(self, value):
        if len(value) < 8:
            raise serializers.ValidationError("The new password must be at least 8 characters long.")
        return value
    

class StickyNoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = StickyNote
        fields = '__all__'




class CompanyInquirySerializer(serializers.ModelSerializer):
    class Meta:
        model = CompanyInquiry
        fields = '__all__'


from dj_rest_auth.serializers import PasswordResetSerializer
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.contrib.sites.shortcuts import get_current_site
from django.contrib.auth.tokens import default_token_generator
from django.template.loader import render_to_string
class CustomPasswordResetSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        """
        Validate if a user with this email exists.
        """
        if not User.objects.filter(email=value).exists():
            raise serializers.ValidationError("User with this email does not exist.")
        return value

    def save(self, request=None):
        """
        Generate password reset token and send email.
        """
        email = self.validated_data.get('email')  # Use validated data
        user = User.objects.get(email=email)

        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)

        protocol = 'https' if request and request.is_secure() else 'http'
        frontend_domain = settings.FRONTEND_DOMAIN
        reset_url = f"{protocol}://{frontend_domain}/login/forgot-password/?id={uid}&token={token}"  # Fixed trailing `/`

        context = {
            'user': user,
            'uid': uid,
            'token': token,
            'protocol': protocol,
            'domain': frontend_domain,
            'reset_password_url': reset_url  # Add the reset URL to the context
        }

        subject = "Password Reset Request"
        email_template = 'emails/forgot_password.html'
        message = render_to_string(email_template, context)

        recipient_list = [email]
        send_email(subject, message, recipient_list,"default")






class EnquirySerializer(serializers.ModelSerializer):
    class Meta:
        model = Enquiry
        fields = ['id', 'full_name', 'email', 'phone_number', 'message', 'admin_message', 'created_at','status']


class MonthlyCompanyStatsSerializer(serializers.Serializer):
    month = serializers.IntegerField()
    year = serializers.IntegerField()
    total_companies = serializers.IntegerField()

class AgreementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Agreement
        fields = ['id', 'text','title', 'created_by', 'created_at', 'updated_at']
        read_only_fields = ['created_by', 'created_at', 'updated_at']


class QcScoreSerializer(serializers.ModelSerializer):
    class Meta:
        model = QcScore
        fields = [
            'id',
            'user',
            'question',
            'score',
            'rating_count',
            'feedback',
            'scored_at',
            'created_at',
            'updated_at'
        ]




class UserTargetsDelailsSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source='company.name', read_only=True)
    branch_name = serializers.CharField(source='branch.name', read_only=True)
    user_name = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = UserTargetsDelails
        fields = '__all__'



class CompanyUserAPIKeySerializer(serializers.ModelSerializer):
    class Meta:
        model = CompanyUserAPIKey
        fields = ['id', 'user', 'company', 'api_key','status']
        read_only_fields = ['company', 'api_key','status']

    def create(self, validated_data):
        instance, created = CompanyUserAPIKey.objects.get_or_create(**validated_data)
        return instance
    

class ReminderNotesSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReminderNotes
        fields = '__all__'


class InterviewApplicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = InterviewApplication
        fields = "__all__"
        read_only_fields = ("company", "branch", "created_at", "updated_at")


class CompanySalarySerializer(serializers.ModelSerializer):
    class Meta:
        model = CompanySalary
        fields = ["id", "amount", "created_at", "updated_at"]


class DoctorSerializer(serializers.ModelSerializer):
    branches = serializers.PrimaryKeyRelatedField(
        queryset=Branch.objects.all(),
        many=True,
        required=False
    )

    branch_names = serializers.SerializerMethodField()
    company_name = serializers.CharField(source="company.name", read_only=True)

    # User details (read-only)
    username = serializers.CharField(source="user.username", read_only=True)
    email = serializers.EmailField(source="user.email", read_only=True)
    full_name = serializers.SerializerMethodField()
    phone_number = serializers.SerializerMethodField()

    # ✅ Signature field
    doctor_sign = serializers.ImageField(required=False, allow_null=True)

    class Meta:
        model = Doctor
        fields = [
            "id",
            "user",
            "username",
            "full_name",
            "email",
            "phone_number",
            "company",
            "company_name",
            "branches",
            "branch_names",
            "registration_number",
            "degree",
            "specialization",
            "experience_years",
            "address",
            "doctor_sign",
            "is_active",
        ]
        read_only_fields = ["company"]

    def get_branch_names(self, obj):
        return list(obj.branches.values_list("name", flat=True))

    def get_full_name(self, obj):
        first = obj.user.first_name or ""
        last = obj.user.last_name or ""
        return f"{first} {last}".strip()

    def get_phone_number(self, obj):
        if hasattr(obj.user, "profile") and obj.user.profile.contact_no:
            return str(obj.user.profile.contact_no)
        return None

    def validate(self, data):
        request = self.context.get("request")
        user = request.user if request else None
        company = getattr(user.profile, "company", None)

        branches = data.get("branches", [])

        if company and branches:
            for branch in branches:
                if branch.company != company:
                    raise serializers.ValidationError(
                        "All selected branches must belong to your company."
                    )
        return data


