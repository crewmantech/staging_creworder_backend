import io
from venv import logger
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
# from rest_framework.authtoken.models import Token
from accounts.models import ExpiringToken as Token
from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied, ValidationError
from django.contrib.contenttypes.models import ContentType
from guardian.shortcuts import get_objects_for_user
from rest_framework import generics, status
from django.contrib.auth.models import Group,Permission
from django.db import IntegrityError, transaction
import pdb
import sys
from datetime import datetime ,timedelta,time
import random
from rest_framework.decorators import action

from chat.models import Notification
from cloud_telephony.models import CloudTelephonyChannelAssign
from orders.models import Category, OrderValueSetting, Products
from kyc.models import KYC
from kyc.serializers import KYCSerializer
from orders.views import OrderPagination
from services.email.email_service import send_email
from services.shipment.schedule_orders import ShiprocketScheduleOrder,TekipostService
from shipment.models import ShipmentModel, ShipmentVendor
from shipment.serializers import ShipmentSerializer
from .models import  Agreement, AttendanceSession, CompanyInquiry, CompanyUserAPIKey, Enquiry, QcScore, ReminderNotes, StickyNote, User, Company, Package, Employees, Notice, Branch, FormEnquiry, SupportTicket, Module, \
    Department, Designation, Leaves, Holiday, Award, Appreciation, ShiftTiming, Attendance, AllowedIP,Shift_Roster,CustomAuthGroup,PickUpPoint, UserStatus,\
    UserTargetsDelails,AdminBankDetails,QcTable
from .serializers import  AgreementSerializer, CompanyInquirySerializer, CompanyUserAPIKeySerializer, CustomPasswordResetSerializer, EnquirySerializer, NewPasswordSerializer,  QcScoreSerializer, ReminderNotesSerializer, StickyNoteSerializer, UpdateTeamLeadManagerSerializer, UserSerializer, CompanySerializer, PackageSerializer, \
    UserProfileSerializer, NoticeSerializer, BranchSerializer, UserSignupSerializer, FormEnquirySerializer, \
    SupportTicketSerializer, ModuleSerializer, DepartmentSerializer, DesignationSerializer, LeaveSerializer, \
    HolidaySerializer, AwardSerializer, AppreciationSerializer, ShiftSerializer, AttendanceSerializer,ShiftRosterSerializer, \
    PackageDetailsSerializer,CustomAuthGroupSerializer,PermissionSerializer,PickUpPointSerializer,UserTargetSerializer,AdminBankDetailsSerializers,\
    AllowedIPSerializers,QcSerialiazer,TeamUserProfile , UserTargetsDelailsSerializer

from rest_framework.parsers import JSONParser, MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated, AllowAny, DjangoObjectPermissions
from django.db.models import Q, Count,Avg
from dj_rest_auth.views import LoginView
from .permissions import CanChangeCompanyStatusPermission, CanEditOwnCompanyPermission,CanLeaveApproveAndDisapprove, HasPermission,IsAdminOrSuperAdmin, IsAuthenticatedOrReadOnly, IsSuperAdmin
from django.core.files.storage import default_storage
import csv
from rest_framework.decorators import permission_classes
from django.utils.timezone import now
from django.db.models import Exists, OuterRef

from datetime import date
from dj_rest_auth.views import PasswordResetView
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_decode
from django.contrib.auth import get_user_model
from django.template.loader import render_to_string
from rest_framework.response import Response
from rest_framework import status, viewsets
from .models import Enquiry
from rest_framework.views import exception_handler
from io import TextIOWrapper
from accounts import models
from rest_framework.pagination import PageNumberPagination


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is not None:
        response.data['status_code'] = response.status_code  # Include status code in JSON response
    return response

class IPRestrictedLoginView(LoginView):
    def post(self, request, *args, **kwargs):
        username = request.data.get('username')
        if username:
            try:
                user = User.objects.get(username=username)
                branch = user.profile.branch

                ip_address = self.get_client_ip(request)
                pdb.set_trace()

                # Check if the IP address is allowed for the user's branch
                if not AllowedIP.objects.filter(branch=branch, ip_address=ip_address).exists():
                    return Response({'error': 'Login from this IP address is not allowed'},
                                    status=status.HTTP_403_FORBIDDEN)

            except User.DoesNotExist:
                # Proceed with the standard response, the user may not exist
                pass

        return super().post(request, *args, **kwargs)

    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')

        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    def get_permissions(self):
        permission_map = {
            'create': ['superadmin_assets.show_submenusmodel_employee', 'superadmin_assets.add_submenusmodel'],
            'update': ['superadmin_assets.show_submenusmodel_employee', 'superadmin_assets.change_submenusmodel'],
            'destroy': ['superadmin_assets.show_submenusmodel_employee', 'superadmin_assets.delete_submenusmodel'],
            'retrieve': ['superadmin_assets.show_submenusmodel_employee', 'superadmin_assets.view_submenusmodel'],
            'list': ['superadmin_assets.show_submenusmodel_employee', 'superadmin_assets.view_submenusmodel']
        }
        
        action = self.action
        if action in permission_map:
            permissions = permission_map[action]
            return [HasPermission(perm) for perm in permissions]  # Return a list of permission checks
    
        return super().get_permissions()
    @action(detail=True, methods=['post','patch'], url_path='update-password', url_name='update_password')
    def update_password(self, request, pk=None):
        """
        Update the password of a particular user.
        Accessible only to authorized users (e.g., superadmin).
        """
        user = self.get_object()  # Fetch the user by primary key (pk)
        
        serializer = NewPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Update the user's password
        user.set_password(serializer.validated_data['new_password'])
        user.save()

        return Response({"detail": f"Password updated successfully for user {user.username}."}, status=status.HTTP_200_OK)
    
    def create(self, request, *args, **kwargs):
        user = request.user
        if not hasattr(request.user, 'profile') or request.user.profile.user_type != 'superadmin':
            company = user.profile.company  # Assuming Profile model has a OneToOneField to User and ForeignKey to Company


            # Extract role/type from the incoming request data
            user_type = request.data.get('profile', {}).get('user_type', 'agent')
            # Expected: 'admin' or 'user'

            # Get company package limits
            package = company.package
            max_employees = package.max_employees or 0
            max_admins = package.max_admin or 0

            # Count current users under the company
            from django.contrib.auth import get_user_model
            User = get_user_model()

            company_users = User.objects.filter(profile__company=company,profile__status=1)
            admin_count = company_users.filter(profile__user_type='admin').count()
            employee_count = company_users.filter(profile__user_type='agent').count()

            # Enforce limits
            if  user_type=='admin' and max_admins and admin_count >= max_admins:
                raise ValidationError({"detail": "Your plan has reached the maximum number of allowed Admins. Please contact support to upgrade your plan."})

            if user_type=='agent' and max_employees and employee_count >= max_employees:
                raise ValidationError({"detail": "Your plan has reached the maximum number of allowed Agent. Please contact support to upgrade your plan."})
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(data=serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        status1 = request.data['profile']['status'] if 'profile' in request.data and 'status' in request.data['profile'] else None
        if status1 == 2:
            self._send_admin_notification(instance)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        return Response(serializer.data, status=status.HTTP_200_OK)

    def perform_update(self, serializer):
        user = self.request.user

        if not hasattr(user, 'profile') or user.profile.user_type != 'superadmin':
            company = user.profile.company  # Profile has ForeignKey to Company


            # Get user_type from profile data or default to 'agent'
            profile_data = self.request.data.get('profile', {})
            user_type = profile_data.get('user_type', 'agent')  # default to 'agent'

            # Get limits from company's package
            package = company.package
            max_employees = package.max_employees or 0
            max_admins = package.max_admin or 0

            # Count current users under the company
            from django.contrib.auth import get_user_model
            User = get_user_model()
            company_users = User.objects.filter(profile__company=company,profile__status=1)
            admin_count = company_users.filter(profile__user_type='admin').count()
            employee_count = company_users.filter(profile__user_type='agent').count()

            # Enforce limits
            if user_type == 'admin' and max_admins and admin_count > max_admins:
                raise ValidationError({
                    "detail": "Your plan has reached the maximum number of allowed Admins. Please contact support to upgrade your plan."
                })
            elif user_type == 'agent' and max_employees and employee_count > max_employees:
                raise ValidationError({
                    "detail": "Your plan has reached the maximum number of allowed Users. Please contact support to upgrade your plan."
                })

        # Save the serializer (user update)
        serializer.save()

    def get_queryset(self):
        user = self.request.user
        try:
            # Base queryset
            queryset = User.objects.all()

            # Only filter active for list/retrieve
            if self.action in ["list", "retrieve"]:
                queryset = queryset.filter(profile__status=1)

            if user.profile.user_type == "superadmin":
                company_id = self.request.query_params.get("company_id")
                if company_id:
                    queryset = queryset.filter(profile__company_id=company_id)
                else:
                    queryset = queryset.filter(profile__company=None)

            elif user.profile.user_type == "admin":
                queryset = queryset.filter(profile__company=user.profile.company)

            elif user.profile.user_type == "agent":
                queryset = queryset.filter(profile__branch=user.profile.branch)
                try:
                    user_permissions = user.user_permissions.values_list('codename', flat=True)

                    # 🟢 1. Full Access: All departments
                    if 'department_can_view_all_department' in user_permissions:
                        pass  # full access

                    # 🟡 2. Own Department Access
                    elif 'department_can_view_own_department' in user_permissions:
                        queryset = queryset.filter(profile__department=user.profile.department)

                    else:
                        # 🔵 3. Specific Department(s) Access
                        department_permissions = [
                            perm.split('department_can_view_department_')[1]
                            for perm in user_permissions
                            if perm.startswith('department_can_view_department_')
                        ]

                        if department_permissions:
                            queryset = queryset.filter(
                                profile__department__name__in=department_permissions
                            )
                        else:
                            # 🔴 4. Default: Only self (no permission)
                            queryset = queryset.filter(id=user.id)

                except Exception as e:
                    print("Agent filtering error:", e)
                    queryset = queryset.none()
        except Exception as e:
            print(f"Error in get_queryset: {e}")
        return queryset


    def _send_admin_notification(self, instance):
        try:
            suspension_reason = "Violation of our terms of service, including but not limited to inappropriate content, misuse of services, or failure to comply with our usage policies."
            subject = "Account Suspension"
            template = "emails/account_suspension.html"  # Your HTML email template
            context = {
                'full_name': instance.first_name + ' ' + instance.last_name,
                'suspension_reason': suspension_reason,
                
            }
            
            html_message = render_to_string(template, context)
            recipient_list = [instance.email]
            a = send_email(subject, html_message, recipient_list,"default")
            logger.info(f"Email sent successfully to {instance.email}")
        except Exception as email_error:
            logger.error(f"Error sending email to {instance.email}: {email_error}")

class CompanyViewSet(viewsets.ModelViewSet):
    queryset = Company.objects.all()
    serializer_class = CompanySerializer
    parser_classes = [JSONParser, FormParser, MultiPartParser]
    permission_classes = [IsAuthenticated, DjangoObjectPermissions]
    
    def get_permissions(self):
        user = self.request.user
        # If the user is an admin and the action is 'retrieve', bypass permission check
        if user.profile.user_type == 'admin' and self.action == 'retrieve':
            return [IsAuthenticated()]  # Only require authentication for admin during 'retrieve'
        permission_map = {
            'create': 'accounts.add_company',
            'update': 'accounts.change_company',
            'destroy': 'accounts.delete_company',
            'retrieve': 'accounts.view_company',
            'list': 'accounts.view_company'
        }
        action = self.action
        if action in permission_map:
            return [HasPermission(permission_map[action])]
        return super().get_permissions()
    def handle_exception(self, exc):
        response = super().handle_exception(exc)
        if isinstance(response, Response):
            response.data = {'error': response.data}  # Wrap errors in JSON
        return response
    def get_queryset(self):
        user = self.request.user
        if user.profile.user_type == 'admin':
            company = user.profile.company  # Assuming there's a company relationship on the profile
            return Company.objects.filter(id=company.id)
        queryset = get_objects_for_user(user, 'accounts.view_company', klass=Company)

        # Add user's own companies if they have the permission
        if user.has_perm('accounts.can_view_own_company') or user.profile.user_type == 'admin':
            own_queryset = Company.objects.filter(created_by=user)
            queryset = queryset | own_queryset

        # Check if the user has permissions but no companies exist
        if not queryset.exists():
            # Check if the user has any permission to view companies
            if (
                user.has_perm('accounts.view_company')
                or user.has_perm('accounts.can_view_own_company') or user.profile.user_type == 'admin'
            ):
                # Return an empty queryset if the user has permission but no data exists
                return queryset
            else:
                # Otherwise, raise a permission error
                raise PermissionDenied("You do not have permission to view any companies.")

        return queryset

    def retrieve(self, request, *args, **kwargs):
        """Override retrieve to include KYC data."""
        company = self.get_object()
        kyc_data = KYC.objects.filter(company=company).first()
        bank_detils = AdminBankDetails.objects.filter(company=company, priority=1).first()
        company_data = self.get_serializer(company).data
        bank_detils = AdminBankDetailsSerializers(bank_detils).data
        if kyc_data:
            company_data['kyc'] = KYCSerializer(kyc_data).data
        else:
            company_data['kyc'] = None
        if bank_detils:
            company_data['bank_detils'] = bank_detils
        else:
            company_data['bank_detils'] = None
        return Response(company_data)
    
    @action(detail=True, methods=['post'], permission_classes=[CanChangeCompanyStatusPermission])
    def change_status(self, request, pk=None):
        company = self.get_object()
        if 'status' not in request.data:
            raise ValidationError({"detail": "The status field is required."})
        else:
            company_status = request.data['status']
            if company_status not in [True, False]:
                raise ValidationError({"detail": "The value provided is not a valid choice."})
            company.status = company_status
            company.save()

        return Response({"detail": 'Status changed successfully.'})
    def update(self, request, *args, **kwargs):
        self.permission_classes = [CanEditOwnCompanyPermission]
        self.check_permissions(request)
        return super().update(request, *args, **kwargs)
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def check_company_data(self, request):
        user = request.user
        if not hasattr(user, 'profile') or not user.profile.company:
            return Response({"success": False, "message": "Company not associated with user"}, status=400)
        
        company = user.profile.company
        
        data = {
            "roles_exist": CustomAuthGroup.objects.filter(company=company).exists(),
            "designations_exist": Designation.objects.filter(company=company).exists(),
            "departments_exist": Department.objects.filter(company=company).exists(),
            "users_exist": Employees.objects.filter(company=company).exists(),
            "pickup_locations_exist": PickUpPoint.objects.filter(company=company).exists(),
            "order_settings_exist": OrderValueSetting.objects.filter(company=company).exists(),
            "categories_exist": Category.objects.filter(company=company).exists(),
            "products_exist": Products.objects.filter(category__company=company).exists(),
            "shipment_channels_exist": ShipmentModel.objects.filter(company=company).exists(),
        }
        data["company_id"] = company.id  

        return Response({"success": True, "data": data})
class BranchViewSet(viewsets.ModelViewSet):
    queryset = Branch.objects.all()
    serializer_class = BranchSerializer
    permission_classes = [IsAuthenticated, DjangoObjectPermissions]
    def get_permissions(self):
        permission_map = {
            'create': ['superadmin_assets.show_settingsmenu_branch_settings', 'superadmin_assets.add_settingsmenu'],
            'update': ['superadmin_assets.show_settingsmenu_branch_settings', 'superadmin_assets.change_settingsmenu'],
            'destroy': ['superadmin_assets.show_settingsmenu_branch_settings', 'superadmin_assets.delete_settingsmenu'],
            'retrieve': ['superadmin_assets.show_settingsmenu_branch_settings', 'superadmin_assets.view_settingsmenu'],
            'list': ['superadmin_assets.show_settingsmenu_branch_settings', 'superadmin_assets.view_settingsmenu']
        }
        
        action = self.action
        if action in permission_map:
            permissions = permission_map[action]
            return [HasPermission(perm) for perm in permissions]  # Return a list of permission checks
    
        return super().get_permissions()
    # def get_permissions(self):
    #     permission_map = {
    #         'create': 'accounts.add_branch',
    #         'update': 'accounts.change_branch',
    #         'destroy': 'accounts.delete_branch',
    #         'retrieve': 'accounts.view_branch',
    #         'list': 'accounts.view_branch'
    #     }
    #     action = self.action
    #     if action in permission_map:
    #         return [HasPermission(permission_map[action])]
    #     return super().get_permissions()
    def get_queryset(self):
        user = self.request.user

        if not hasattr(user, 'profile'):
            logger.warning(f"User {user.id} has no profile.")
            return Branch.objects.none()

        if not user.profile.company:
            logger.warning(f"User {user.id} has no associated company.")
            return Branch.objects.none()

        if user.profile.user_type in ["admin", "agent"]:
            return Branch.objects.filter(company=user.profile.company)

        return Branch.objects.none()

    def perform_create(self, serializer):
        # Automatically set the company field based on the user's profile
        user = self.request.user
        company = user.profile.company
        serializer.save(company=company)  # Pass company to serializer

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        user = self.request.user
        # Check if the user has the delete permission
        if not user.has_perm('accounts.delete_branch'):
            raise PermissionDenied("You do not have permission to delete this branch.")
        # Perform deletion if the user has permission
        self.perform_destroy(instance)
        return Response({"detail": "Branch deleted successfully."}, status=status.HTTP_204_NO_CONTENT)
   
        

class PackageViewSet(viewsets.ModelViewSet):
    queryset = Package.objects.all()
    serializer_class = PackageSerializer
    permission_classes = [IsAuthenticated, DjangoObjectPermissions]
    def get_permissions(self):
        permission_map = {
            'create': 'accounts.add_package',
            'update': 'accounts.change_package',
            'destroy': 'accounts.delete_package',
            'retrieve': 'accounts.view_package',
            'list': 'accounts.view_package'
        }
        action = self.action
        if action in permission_map:
            return [HasPermission(permission_map[action])]
        return super().get_permissions()
    @transaction.atomic
    def create(self, request, *args, **kwargs):
        data = request.data
        package_data = data.get('package')
        package_details_data = data.get('package_details')
        package_serializer = PackageSerializer(data=package_data)
        
        if package_serializer.is_valid():
            package = package_serializer.save()
            for detail_data in package_details_data:
                detail_data['package'] = package.id
                package_detail_serializer = PackageDetailsSerializer(data=detail_data)
                if package_detail_serializer.is_valid():
                    package_detail_serializer.save()
                else:
                    return Response(package_detail_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

            package_serializer = PackageSerializer(package)
            return Response(package_serializer.data, status=status.HTTP_201_CREATED)
        else:
            return Response(package_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)
    
    @transaction.atomic
    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        data = request.data
        package_data = data.get('package')
        package_details_data = data.get('package_details')
        package_serializer = PackageSerializer(instance, data=package_data, partial=True)
        if package_serializer.is_valid():
            package = package_serializer.save()
            existing_details = {detail.id: detail for detail in instance.packagedetails.all()}
            for detail_data in package_details_data:
                detail_id = detail_data.get('id')
                if detail_id and detail_id in existing_details:
                    package_detail_instance = existing_details.pop(detail_id)
                    package_detail_serializer = PackageDetailsSerializer(package_detail_instance, data=detail_data, partial=True)
                else:
                    detail_data['package'] = package.id 
                    package_detail_serializer = PackageDetailsSerializer(data=detail_data)
                if package_detail_serializer.is_valid():
                    package_detail_serializer.save()
                else:
                    return Response(package_detail_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            for remaining_detail in existing_details.values():
                remaining_detail.delete()
            package_serializer = PackageSerializer(package)
            return Response(package_serializer.data, status=status.HTTP_200_OK)
        else:
            return Response(package_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
# class UserRoleViewSet(viewsets.ModelViewSet):
#     queryset = UserRole.objects.all()
#     serializer_class = UserRoleSerializer
#     permission_classes = [IsAuthenticated]


class UserProfileViewSet(viewsets.ModelViewSet):
    queryset = Employees.objects.all()
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]


class NoticeViewSet(viewsets.ModelViewSet):
    queryset = Notice.objects.all()
    serializer_class = NoticeSerializer
    permission_classes = [IsAuthenticated]
    def get_permissions(self):
        permission_map = {
            'create': ['superadmin_assets.show_menumodel_notice', 'superadmin_assets.add_menumodel'],
            'update': ['superadmin_assets.show_menumodel_notice', 'superadmin_assets.change_menumodel'],
            'destroy': ['superadmin_assets.show_menumodel_notice', 'superadmin_assets.delete_menumodel'],
            'retrieve': ['superadmin_assets.show_menumodel_notice', 'superadmin_assets.view_menumodel'],
            'list': ['superadmin_assets.show_menumodel_notice', 'superadmin_assets.view_menumodel']
        }
        
        action = self.action
        if action in permission_map:
            permissions = permission_map[action]
            return [HasPermission(perm) for perm in permissions]  # Return a list of permission checks
    
        return super().get_permissions()
    def get_queryset(self):
        user = self.request.user
        queryset = Notice.objects.filter(created_by=user)
        return queryset

    def perform_create(self, serializer):
        notice = serializer.save(created_by=self.request.user)

        # Create notification for each user in 'users' field
        for user in serializer.validated_data['users']:
            Notification.objects.create(
                user=user,
                message=f"You have a new notice: {notice.title}",
                url=f"/notice-board",  # Adjust as per your frontend route
                notification_type="chat_message"  # Or a new type like "notice"
            )

# for all permisson given user
class UserPermissionsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        guardian_permissions = user.get_all_permissions()
        user_data = UserSerializer(user, many=False).data
        profile = UserProfileSerializer(user.profile, many=False).data
        user_data['profile'] = profile
        role = user.profile.user_type
        response_data = {"user": user_data, "role": role, "permissions": guardian_permissions}
        return Response(response_data)


class GetSpecificUsers(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        if user.role.role == "superadmin":
            users = User.objects.filter(role__role="admin")
        elif user.role.role == "admin":
            company = user.profile.company
            users = User.objects.filter(profile__company=company).exclude(id=user.id)
        users_data = UserSerializer(users, many=True)
        # pdb.set_trace()

        return Response({"results": users_data.data})


class AdminSelfSignUp(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        user_data = request.data.get('user')

        user_serializer = UserSignupSerializer(data=user_data)

        if user_serializer.is_valid():
            user_serializer.save()

            return Response({
                'message': 'Signup Successful.'
            }, status=status.HTTP_201_CREATED)

        return Response(user_serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class FormEnquiryViewSet(viewsets.ModelViewSet):
    queryset = FormEnquiry.objects.all()
    serializer_class = FormEnquirySerializer


class SupportTicketViewSet(viewsets.ModelViewSet):
    queryset = SupportTicket.objects.all()
    serializer_class = SupportTicketSerializer


class ModuleViewSet(viewsets.ModelViewSet):
    queryset = Module.objects.all()
    serializer_class = ModuleSerializer


class GetNoticesForUser(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        data = user.notices.all()
        serialized_data = NoticeSerializer(data, many=True).data
        return Response({"results": serialized_data})


# class DepartmentViewSet(viewsets.ModelViewSet):
#     permission_classes = [IsAuthenticated]
#     queryset = Department.objects.all()
#     serializer_class = DepartmentSerializer


class DepartmentViewSet(viewsets.ModelViewSet):
    queryset = Department.objects.all()
    serializer_class = DepartmentSerializer
    permission_classes = [IsAuthenticated, IsAdminOrSuperAdmin]  # Only admin or superadmin can modify
    def get_permissions(self):
        permission_map = {
            'create': ['superadmin_assets.show_submenusmodel_department', 'superadmin_assets.add_submenusmodel'],
            'update': ['superadmin_assets.show_submenusmodel_department', 'superadmin_assets.change_submenusmodel'],
            'destroy': ['superadmin_assets.show_submenusmodel_department', 'superadmin_assets.delete_submenusmodel'],
            'retrieve': ['superadmin_assets.show_submenusmodel_department', 'superadmin_assets.view_submenusmodel'],
            'list': ['superadmin_assets.show_submenusmodel_department', 'superadmin_assets.view_submenusmodel']
        }
        
        action = self.action
        if action in permission_map:
            permissions = permission_map[action]
            return [HasPermission(perm) for perm in permissions]  # Return a list of permission checks
    
        return super().get_permissions()
    def perform_create(self, serializer):
        """
        Sets the user who created the department and optionally associates it with the user's company.
        Ensures that a user cannot create multiple departments with the same name.
        """
        user = self.request.user
        
        # Check if the user has already created a department with the same name
        department_name = serializer.validated_data.get('name')
        if Department.objects.filter(created_by=user, name=department_name).exists():
            raise ValidationError(f"A department with the name '{department_name}' already exists.")

        # Set the user who created the department (creator)
        department = serializer.save(created_by=user)

        # Optionally associate the department with the user's company
        if user.profile.company:
            department.company = user.profile.company
            department.save()

    def perform_update(self, serializer):
        """
        Sets the user who updated the department.
        """
        serializer.save(updated_by=self.request.user)

    def get_queryset(self):
        """
        Optionally filter departments based on the user role.
        Superadmins and admins can view all departments. Others can view only departments they've created.
        """
        
        user = self.request.user
        if  user.profile.user_type in ['admin','agent']:
            # Admin and superadmin see all departments
            # return Department.objects.all()
            return Department.objects.filter(company=user.profile.company)
        elif user.profile.user_type == 'superadmin':
            return Department.objects.filter(company=None)
            
        # Users with other profiles (if any) should see only their company's departments
        return Department.objects.filter(created_by=user.id)

# class DesignationViewSet(viewsets.ModelViewSet):
#     permission_classes = [IsAuthenticated]
#     queryset = Designation.objects.all()
#     serializer_class = DesignationSerializerNew
    
#     def get_queryset(self):
#         user = self.request.user
#         if user.profile.user_type == "admin" or user.profile.user_type == "agent":
#             branch = user.profile.branch
#             queryset = Designation.objects.filter(branch=branch)
#         else:
#             queryset = Designation.objects.all()
#         return queryset

class DesignationViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = Designation.objects.all()
    serializer_class = DesignationSerializer
    def get_permissions(self):
        permission_map = {
            'create': ['superadmin_assets.show_submenusmodel_designation', 'superadmin_assets.add_submenusmodel'],
            'update': ['superadmin_assets.show_submenusmodel_designation', 'superadmin_assets.change_submenusmodel'],
            'destroy': ['superadmin_assets.show_submenusmodel_designation', 'superadmin_assets.delete_submenusmodel'],
            'retrieve': ['superadmin_assets.show_submenusmodel_designation', 'superadmin_assets.view_submenusmodel'],
            'list': ['superadmin_assets.show_submenusmodel_designation', 'superadmin_assets.view_submenusmodel']
        }
        
        action = self.action
        if action in permission_map:
            permissions = permission_map[action]
            return [HasPermission(perm) for perm in permissions]  # Return a list of permission checks
    
        return super().get_permissions()
    def perform_create(self, serializer):
        """
        Automatically set the company (from the user's profile) and the user who created the designation.
        Ensures that a user cannot create multiple designations with the same name.
        """
        user = self.request.user

        # Check if a designation with the same name already exists for this user
        designation_name = serializer.validated_data.get('name')
        if Designation.objects.filter(created_by=user, name=designation_name).exists():
            raise ValidationError(f"A designation with the name '{designation_name}' already exists.")

        # Assuming the user has a `profile` attribute with a related company.
        company = user.profile.company
        # Save the designation with the user and company
        serializer.save(created_by=user, company=company)

    def perform_update(self, serializer):
        """
        Automatically set the user who updated the designation.
        """
        serializer.save(updated_by=self.request.user)

    def get_queryset(self):
        permissions = self.request.user.get_all_permissions()
        """
        Optionally filter designations based on the user's role.
        Superusers can see all designations. Regular users can see only designations associated with their company.
        """
        # if user.profile.user_type == "admin" or user.profile.user_type == "agent":
        user = self.request.user
        # if user.profile.user_type == "superadmin" :
            # Superuser can see all designations
        if  user.profile.user_type in ['admin','agent']:
            # Admin and superadmin see all departments
            # return Department.objects.all()
            return Designation.objects.filter(company=user.profile.company)
        elif user.profile.user_type == 'superadmin':
            return Designation.objects.filter(company=None)
            
        # return Designation.objects.filter(created_by=user.id)
            # return Designation.objects.all()

        # Regular users can only see designations related to their company
        # if hasattr(user.profile, 'company'):
            # return Designation.objects.filter(company=user.profile.company)
        
        return Designation.objects.none() 

class LeaveViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, DjangoObjectPermissions]
    queryset = Leaves.objects.all()
    serializer_class = LeaveSerializer
    def get_permissions(self):
        permission_map = {
            'create': ['superadmin_assets.show_submenusmodel_leave', 'superadmin_assets.add_submenusmodel'],
            'update': ['superadmin_assets.show_submenusmodel_leave', 'superadmin_assets.change_submenusmodel'],
            'destroy': ['superadmin_assets.show_submenusmodel_leave', 'superadmin_assets.delete_submenusmodel'],
            'retrieve': ['superadmin_assets.show_submenusmodel_leave', 'superadmin_assets.view_submenusmodel'],
            'list': ['superadmin_assets.show_submenusmodel_leave', 'superadmin_assets.view_submenusmodel'],
            'leave_action':['superadmin_assets.show_submenusmodel_leave', 'superadmin_assets.add_submenusmodel']
        }
        
        action = self.action
        if action in permission_map:
            permissions = permission_map[action]
            return [HasPermission(perm) for perm in permissions]  # Return a list of permission checks
    
        return super().get_permissions()
    # def get_permissions(self):
        
    #     if self.action == 'create':
    #         return [HasPermission('accounts.add_leaves')]
    #     elif self.action == 'update':
    #         return [HasPermission('accounts.change_leaves')]
    #     elif self.action == 'destroy':
    #         return [HasPermission('accounts.delete_leaves')]
    #     elif self.action == 'retrieve':  # For getting a specific email address
    #         return [HasPermission('accounts.view_leaves')]
    #     elif self.action == 'list':  # For listing all email addresses
    #         return [HasPermission('accounts.view_leaves')]
    #     elif self.action == 'leave_action':
    #         return [HasPermission('accounts.can_approve_disapprove_leaves')]
    #     return super().get_permissions()
    @action(detail=True, methods=['put'],permission_classes=[CanLeaveApproveAndDisapprove])
    def leave_action(self, request, pk=None):
        leaves = self.get_object()
        if 'status' not in request.data:
            raise ValidationError({"detail": "The status field is required."})
        leave_status = request.data['status']
        leaves.status = leave_status
        leaves.save()

        return Response({"detail": "Status changed successfully."}, status=status.HTTP_200_OK)
    # Handle the list operation
    def list(self, request, *args, **kwargs):
        """
        List leave requests:
        - If the user is admin or has permissions, return all leave requests within their branch.
        - Otherwise, return only the authenticated user's leave requests.
        """
        # Check if user is admin or has leave-view permission
        if request.user.profile.user_type == "admin" or request.user.profile.user_type == "superadmin" or request.user.groups.filter(name="view_leave_permissions").exists():
            # If user is an admin or has specific permissions, return all leaves within their branch
            branch_id = request.user.profile.branch_id if hasattr(request.user, 'profile') else None
            if branch_id:
                leaves = Leaves.objects.filter(branch=branch_id)
            else:
                leaves = Leaves.objects.filter(branch=branch_id)
        else:
            # Regular user - only show their own leaves
            leaves = Leaves.objects.filter(user=request.user)
        # Serialize and return the leaves
        return Response(LeaveSerializer(leaves, many=True).data, status=status.HTTP_200_OK)

    # Handle the create operation
    def create(self, request, *args, **kwargs):
        # Extract and process the `date` field
        date_range = request.data.get("date", None)
        if not date_range:
            raise ValidationError({"date": "The date field is required."})

        try:
            if "to" in date_range:  # Handle date ranges like "2025-01-26 to 2025-01-28"
                start_date_str, end_date_str = date_range.split(" to ")
                start_date = datetime.strptime(start_date_str.strip(), "%Y-%m-%d").date()
                end_date = datetime.strptime(end_date_str.strip(), "%Y-%m-%d").date()
            else:  # Handle single dates like "2025-01-28"
                start_date = end_date = datetime.strptime(date_range.strip(), "%Y-%m-%d").date()
        except ValueError:
            raise ValidationError({"date": "Invalid date format. Use 'YYYY-MM-DD' or 'YYYY-MM-DD to YYYY-MM-DD'."})

        # Prepare data for serialization
        mutable_data = request.data.copy()
        mutable_data["branch"] = request.user.profile.branch.id if hasattr(request.user, 'profile') and request.user.profile.branch else None
        mutable_data["start_date"] = start_date
        mutable_data["end_date"] = end_date
        mutable_data.pop("date", None)  # Remove original date string to prevent issues with serializer

        serializer = self.get_serializer(data=mutable_data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    # Handle the update operation
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()

        if "date" in request.data:
            date_range = request.data.get("date")
            try:
                if "to" in date_range:
                    start_date_str, end_date_str = date_range.split(" to ")
                    start_date = datetime.strptime(start_date_str.strip(), "%d %b, %Y").date()
                    end_date = datetime.strptime(end_date_str.strip(), "%d %b, %Y").date()
                else:
                    start_date = end_date = datetime.strptime(date_range.strip(), "%d %b, %Y").date()
                request.data["start_date"] = start_date
                request.data["end_date"] = end_date
            except ValueError:
                raise ValidationError({"date": "Invalid date format. Use 'DD MMM, YYYY' or 'DD MMM, YYYY to DD MMM, YYYY'."})

            request.data.pop("date", None)

        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        return Response(serializer.data, status=status.HTTP_200_OK)

class HolidayViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = Holiday.objects.all()
    serializer_class = HolidaySerializer
    def get_permissions(self):
        permission_map = {
            'create': ['superadmin_assets.show_submenusmodel_holiday', 'superadmin_assets.add_submenusmodel'],
            'update': ['superadmin_assets.show_submenusmodel_holiday', 'superadmin_assets.change_submenusmodel'],
            'destroy': ['superadmin_assets.show_submenusmodel_holiday', 'superadmin_assets.delete_submenusmodel'],
            'retrieve': ['superadmin_assets.show_submenusmodel_holiday', 'superadmin_assets.view_submenusmodel'],
            'list': ['superadmin_assets.show_submenusmodel_holiday', 'superadmin_assets.view_submenusmodel']
        }
        
        action = self.action
        if action in permission_map:
            permissions = permission_map[action]
            return [HasPermission(perm) for perm in permissions]  # Return a list of permission checks
    
        return super().get_permissions()

    def get_queryset(self):
            user = self.request.user
            branch = user.profile.branch  # assuming your user profile has a branch field

            if branch:
                return Holiday.objects.filter(branch=branch)
            return Holiday.objects.none()  # if no branch assigned, return empty queryset

class AwardViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = Award.objects.all()
    serializer_class = AwardSerializer



class AppreciationViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = Appreciation.objects.all()
    serializer_class = AppreciationSerializer
    def get_permissions(self):
        permission_map = {
            'create': ['superadmin_assets.show_submenusmodel_appreciation', 'superadmin_assets.add_submenusmodel'],
            'update': ['superadmin_assets.show_submenusmodel_appreciation', 'superadmin_assets.change_submenusmodel'],
            'destroy': ['superadmin_assets.show_submenusmodel_appreciation', 'superadmin_assets.delete_submenusmodel'],
            'retrieve': ['superadmin_assets.show_submenusmodel_appreciation', 'superadmin_assets.view_submenusmodel'],
            'list': ['superadmin_assets.show_submenusmodel_appreciation', 'superadmin_assets.view_submenusmodel']
        }
        
        action = self.action
        if action in permission_map:
            permissions = permission_map[action]
            return [HasPermission(perm) for perm in permissions]  # Return a list of permission checks
    
        return super().get_permissions()


class ShiftViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, DjangoObjectPermissions]
    queryset = ShiftTiming.objects.all()
    serializer_class = ShiftSerializer
    def get_permissions(self):
        permission_map = {
            'create': ['superadmin_assets.show_submenusmodel_shift', 'superadmin_assets.add_submenusmodel'],
            'update': ['superadmin_assets.show_submenusmodel_shift', 'superadmin_assets.change_submenusmodel'],
            'destroy': ['superadmin_assets.show_submenusmodel_shift', 'superadmin_assets.delete_submenusmodel'],
            'retrieve': ['superadmin_assets.show_submenusmodel_shift', 'superadmin_assets.view_submenusmodel'],
            'list': ['superadmin_assets.show_submenusmodel_shift', 'superadmin_assets.view_submenusmodel']
        }
        
        action = self.action
        if action in permission_map:
            permissions = permission_map[action]
            return [HasPermission(perm) for perm in permissions]  # Return a list of permission checks
    
        return super().get_permissions()

    # Override list method to fetch shifts for a specific branch or the user's shifts
    def list(self, request, *args, **kwargs):
        user = request.user
        # Check if user has admin permissions or is assigned a branch
        if request.user.profile.user_type == "admin" or request.user.profile.user_type == "superadmin" or request.user.groups.filter(name="view_leave_permissions").exists():
            # Fetch all shifts if admin or has permission
            branch_id = request.user.profile.branch.id if hasattr(request.user, 'profile') and request.user.profile.branch else None
            # shifts = ShiftTiming.objects.all()
            shifts = ShiftTiming.objects.filter(branch=branch_id)
        else:
            
            shifts = ShiftTiming.objects.none()
        # else:
        #     # Otherwise, filter by user's branch
        #     if hasattr(user, 'profile') and user.profile.branch:
        #         shifts = ShiftTiming.objects.filter(branch=user.profile.branch)
        #     else:
        #         shifts = ShiftTiming.objects.none()

        # Serialize filtered data
        serializer = self.get_serializer(shifts, many=True)
        return Response({"results":serializer.data}, status=status.HTTP_200_OK)

    # Create ShiftTiming with the branch automatically assigned from user's profile
    def create(self, request, *args, **kwargs):
        # Assign branch automatically from the user's profile
        
        request.data["branch"] = request.user.profile.branch.id if hasattr(request.user, 'profile') and request.user.profile.branch else None
        

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response({"results":serializer.data}, status=status.HTTP_201_CREATED)

    # Update ShiftTiming with branch permission logic
    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        # Ensure only users in the same branch or admin can edit
        # if not (request.user.profile.user_type == "admin" or (hasattr(request.user, 'profile') and request.user.profile.branch == instance.branch)):
        #     raise PermissionDenied({"detail": "You do not have permission to edit this ShiftTiming."})
        serializer = self.get_serializer(instance, data=request.data, partial=kwargs.pop('partial', False))
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response({"results":serializer.data}, status=status.HTTP_200_OK)

class ShiftRosterViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, DjangoObjectPermissions]
    queryset = Shift_Roster.objects.all()
    serializer_class = ShiftRosterSerializer
    def get_permissions(self):
        permission_map = {
            'create': ['superadmin_assets.show_submenusmodel_shift_roster', 'superadmin_assets.add_submenusmodel'],
            'update': ['superadmin_assets.show_submenusmodel_shift_roster', 'superadmin_assets.change_submenusmodel'],
            'destroy': ['superadmin_assets.show_submenusmodel_shift_roster', 'superadmin_assets.delete_submenusmodel'],
            'retrieve': ['superadmin_assets.show_submenusmodel_shift_roster', 'superadmin_assets.view_submenusmodel'],
            'list': ['superadmin_assets.show_submenusmodel_shift_roster', 'superadmin_assets.view_submenusmodel']
        }
        
        action = self.action
        if action in permission_map:
            permissions = permission_map[action]
            return [HasPermission(perm) for perm in permissions]  # Return a list of permission checks
    
        return super().get_permissions()
    def create(self, request, *args, **kwargs):
        # Extract start and end dates
        start_date = request.data.get('startdate')
        end_date = request.data.get('enddate', start_date)  # Default to start_date if end_date is not provided

        # Ensure dates are strings and parse them
        try:
            start_date = datetime.strptime(str(start_date), "%Y-%m-%d").date()
            end_date = datetime.strptime(str(end_date), "%Y-%m-%d").date()
        except ValueError:
            raise ValidationError({"detail": "Dates must be in 'YYYY-MM-DD' format."})

        # Validate branch and ShiftTiming
        branch_instance = request.user.profile.branch if hasattr(request.user, 'profile') and request.user.profile.branch else None
        shift_id = request.data.get('ShiftTiming')
        try:
            shift_instance = ShiftTiming.objects.get(id=shift_id) if shift_id else None
        except ShiftTiming.DoesNotExist:
            raise ValidationError({"detail": "Invalid ShiftTiming ID."})

        # Create roster entries for each day in the range
        rosters = []
        for single_date in (start_date + timedelta(days=i) for i in range((end_date - start_date).days + 1)):
            roster = Shift_Roster(
                user_id=request.data.get('user'),
                branch=branch_instance,
                ShiftTiming=shift_instance,
                date=single_date,
                remark=request.data.get('remark', '')
            )
            rosters.append(roster)

        # Bulk create rosters
        Shift_Roster.objects.bulk_create(rosters)
        return Response({"detail": "ShiftTiming roster created successfully."}, status=status.HTTP_201_CREATED)

    def list(self, request, *args, **kwargs):
        user = request.user
        queryset = self.get_queryset()

        # Superadmin sees all
        if user.profile.user_type == 'superadmin':
            queryset = queryset
        elif user.profile.user_type == 'admin':
            queryset = queryset.filter(branch=user.profile.branch)
        else:
            queryset = queryset.filter(user=user)

        # Apply additional filters
        branch_id = request.query_params.get('branch', None)
        shift_id = request.query_params.get('ShiftTiming', None)

        if branch_id:
            queryset = queryset.filter(branch_id=branch_id)
        if shift_id:
            queryset = queryset.filter(shift_id=shift_id)

        start_date = request.query_params.get('startdate', None)
        end_date = request.query_params.get('enddate', None)

        if start_date:
            queryset = queryset.filter(date__gte=start_date)
        if end_date:
            queryset = queryset.filter(date__lte=end_date)

        # Serialize and return the filtered data
        serializer = self.get_serializer(queryset, many=True)
        return Response({"results": serializer.data}, status=status.HTTP_200_OK)
        
class StandardResultsSetPagination(PageNumberPagination):
    page_size = 10000                     # default page size = 20
    page_size_query_param = "page_size"  # allow client to override
    max_page_size = 10000

class AttendanceViewSet(viewsets.ModelViewSet):
    """
    A viewset for handling Attendance data with roles: Super Admin, Admin, Agent.
    """
    queryset = Attendance.objects.all()
    serializer_class = AttendanceSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    def get_permissions(self):
        permission_map = {
            'destroy': ['superadmin_assets.show_submenusmodel_attendance', 
                        'superadmin_assets.delete_submenusmodel'],
        }
        action = self.action
        if action in permission_map:
            permissions = permission_map[action]
            return [HasPermission(perm) for perm in permissions]  # list of permission checks
        return super().get_permissions()

    def get_queryset(self):
        """
        Customize queryset based on user role, permissions, and safe date filtering.
        Handles exact date, month/year, and date_range.
        """
        user = self.request.user
        today = date.today()
        filters = Q()

        try:
            if user.profile.user_type == 'superadmin':
                filters = Q(company=None, branch=None)
            else:
                branch = getattr(user.profile.branch, "id", None)
                company = getattr(user.profile.company, "id", None)
                filters = Q(company=company)
                if user.profile.user_type == 'admin':
                    filters &= Q(branch=branch)
                elif not user.has_perm('accounts.view_attendance'):
                    filters &= Q(user=user)
        except Exception as e:
            print(f"[Role Filter Error] {e}")
            # fallback: return nothing if profile is broken
            return Attendance.objects.none()

        exact_date = self.request.query_params.get("date")
        if exact_date:
            filters &= Q(date=exact_date)
        else:
            month = self.request.query_params.get("date__month")
            year = self.request.query_params.get("date__year")

            if month and year:
                filters &= Q(date__year=int(year), date__month=int(month))
            else:
                # Default to current month
                filters &= Q(date__year=today.year, date__month=today.month)

        return Attendance.objects.filter(filters)

    def perform_create(self, serializer):
        user = self.request.user
        profile = getattr(user, "profile", None)
        branch = getattr(profile, "branch", None)
        company = getattr(profile, "company", None)
        today = date.today()

        # Find or create attendance record for today
        attendance, created = Attendance.objects.get_or_create(
            user=user, date=today,
            defaults={'branch': branch, 'company': company}
        )

        # Find active session
        active_session = attendance.sessions.filter(clock_out__isnull=True).first()
        current_time = datetime.now().time()

        if active_session:
            # Perform clock-out
            active_session.clock_out = current_time
            active_session.save()
        else:
            # Perform clock-in
            AttendanceSession.objects.create(attendance=attendance, clock_in=current_time)

        # Update summary
        attendance.update_summary()
        serializer.instance = attendance



class AttendanceView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        date_range = request.query_params['date_range'].split(' - ')
        if len(date_range) != 2:
            return Response(
                {"Success": False, "Error": "Invalid date range format. Expected format: MM/DD/YYYY - MM/DD/YYYY"},
                status=status.HTTP_400_BAD_REQUEST
            )
        try:
            start_date = datetime.strptime(date_range[0], '%m/%d/%Y')
            end_date = datetime.strptime(date_range[1], '%m/%d/%Y')
            start_datetime = datetime.combine(start_date, time.min)
            end_datetime = datetime.combine(end_date, time.max)
            date_filter = Q(date__range=(start_datetime, end_datetime))
            tableData = Attendance.objects.filter(date_filter)
            attendance_counts = tableData.values('user__id','user__username').annotate(
                total_absent=Count('id', filter=Q(attendance='A')),
                total_present=Count('id', filter=Q(attendance='P'))
            )
            orderTableData = AttendanceSerializer(tableData, many=True).data
            user_by_data={}
            for row in orderTableData:
                present_title='Absent'
                if row['user'] not in user_by_data:
                    user_by_data[row['user']]=[]

                start_time = datetime.strptime(row['shift_start_time'], "%H:%M:%S")
                end_time = datetime.strptime(row['shift_end_time'], "%H:%M:%S")
                time_difference = end_time - start_time
                hours = time_difference.total_seconds() / 3600
                clock_in_time_str = row.get('clock_in', '')
                clock_out_time_str = row.get('clock_out', '')

                T1 = datetime.strptime(row['shift_start_time'], "%H:%M:%S")
                T2 = datetime.strptime(row['clock_in'], "%H:%M:%S")
                time_difference = T2 - T1
                difference_in_minutes = time_difference.total_seconds() / 60
                if not clock_out_time_str:
                    present_title = 'Not_Clock_Out'
                else:
                    user_start_time = datetime.strptime(clock_in_time_str, "%H:%M:%S")
                    user_end_time = datetime.strptime(clock_out_time_str, "%H:%M:%S")
                    user_time_difference = user_end_time - user_start_time
                    working_hours = user_time_difference.total_seconds() / 3600
                    if clock_out_time_str=='':
                        present_title = 'Not_Clock_Out'
                    if difference_in_minutes > 11:
                        present_title = 'Late'
                    elif working_hours >= hours and row['attendance'] !='A':
                        present_title = 'Full_Day'
                    elif working_hours >= hours / 2 and row['attendance'] !='A':
                        present_title = 'Half_Day'
                    elif working_hours >= hours / 4 and row['attendance'] !='A':
                        present_title = 'Short_Day'
                    else:
                        pass
                    if row['attendance'] =='A':
                        present_title = 'Absent'


                user_by_data[row['user']].append({
                    "id": row['id'],
                    "date": datetime.strptime(str(row['date']), '%Y-%m-%d').strftime('%Y-%m-%d'),
                    "clock_in": str(row['clock_in']),
                    "clock_out": str(row['clock_out']),
                    "working_from": row['working_from'],
                    "attendance": row['attendance'],
                    "ShiftTiming": row['ShiftTiming'],
                    "shift_name": row['shift_name'],
                    "shift_start_time": row['shift_start_time'],
                    "shift_end_time": row['shift_end_time'],
                    "shift_hours":str(hours),
                    "working_hours":str(working_hours),
                    "present_title":present_title
                })
            return Response(
                {
                    "Success": True,
                    "Data": user_by_data,
                    "Attendance_Counts": list(attendance_counts),
                },
                status=status.HTTP_200_OK
            )

        except ValueError:
            return Response(
                {"Success": False, "Error": "Invalid date format. Expected MM/DD/YYYY"},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {"Success": False, "Error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class GetUsernameSuggestions(APIView):
    permission_classes = [IsAuthenticated]

    def generate_username_suggestions(self, firstname, lastname, date_of_birth):
        base_username = (firstname + lastname[:random.randint(1, 5)] + date_of_birth.strftime('%Y')).lower()
        base_username = base_username[:20]

        existing_usernames = set(
            User.objects.filter(username__startswith=base_username)
                .values_list('username', flat=True)
        )

        suggestions = []
        for i in range(1, 30):
            suggestion = base_username[:15] + str(random.randint(100, 999))
            if suggestion not in existing_usernames and len(suggestions) < 5:
                suggestions.append(suggestion)
            if len(suggestions) == 5:
                break

        return suggestions

    def post(self, request):
        firstname = request.data.get('firstname', '')
        lastname = request.data.get('lastname', '')
        date_of_birth = request.data.get('date_of_birth', '')

        try:
            dob = datetime.strptime(date_of_birth, '%Y-%m-%d')
        except ValueError:
            return Response({"error": "Invalid date_of_birth format. Use 'YYYY-MM-DD'."}, status=400)

        suggestions = self.generate_username_suggestions(firstname, lastname, dob)

        return Response({"results": suggestions})

# class GetPackageModule(viewsets.ModelViewSet):
#     queryset = Package.objects.all()
#     serializer_class = PackageSerializer
#     permission_classes = [IsAuthenticated, DjangoObjectPermissions]
#     def retrieve(self, request, *args, **kwargs):
#         userData = UserProfile.objects.filter(user_id=request.user.id).values("branch", "company").first()
#         CompanyData=Company.objects.filter(id=userData['company']).values("package").first()
#         print(CompanyData['package'])
#         showDataDict={}
#         instance = self.get_object()
#         serializer = self.get_serializer(instance)
#         for data in serializer.data['packagedetails']:
#             if f"{data['menu_name']}" in showDataDict:
#                 print("yes")
#                 if isinstance(showDataDict[f"{data['menu_name']}"], list):
#                     print(data['menu_name'])
#                     showDataDict[f"{data['menu_name']}"].append({f"{data['sub_menu_name']}":f"{data['sub_menu_url']}"})
#             else:
#                 if data['sub_menu_name']==None:
#                     showDataDict[f"{data['menu_name']}"]={f"{data['menu_name']}":f"{data['menu_url']}"}
#                 else:
#                     showDataDict[f"{data['menu_name']}"]=[{f"{data['sub_menu_name']}":f"{data['sub_menu_url']}"}]
#         data = dict(serializer.data)
#         data['sidebardata'] = showDataDict
#         return Response(data)
class GetPackageModule(viewsets.ModelViewSet):
    queryset = Package.objects.all()
    serializer_class = PackageSerializer
    permission_classes = [IsAuthenticated, DjangoObjectPermissions]

    def retrieve(self, request, *args, **kwargs):
        # Get user-related data
        userData = Employees.objects.filter(user_id=request.user.id).values("branch", "company").first()
        
        # Check if userData is valid
        if not userData:
            return Response({"error": "User data not found"}, status=400)

        company_id = userData.get('company')
        if not company_id:
            return Response({"error": "Company ID not found for the user"}, status=400)

        CompanyData = Company.objects.filter(id=company_id).values("package").first()

        # Check if CompanyData is valid
        if not CompanyData or 'package' not in CompanyData:
            return Response({"error": "Package not found for the company"}, status=400)

        package_id = CompanyData['package']
        
        try:
            package_instance = Package.objects.get(id=package_id)
        except Package.DoesNotExist:
            return Response({"error": "Package not found"}, status=400)

        serializer = self.get_serializer(package_instance)

        # Show data for menus and sub-menus
        showDataDict = {}
        
        # Check each menu and submenu permission dynamically
        for data in serializer.data.get('packagedetails', []):
            menu_name = data['menu_name']
            sub_menu_name = data['sub_menu_name']
            sub_menu_url = data['sub_menu_url']
            menu_url = data['menu_url']
            icon = data['menu_icon']
            module_name = data['module_name']  # Added module_name
            menu_namea =menu_name.replace(' ','_').lower()
            # Create a base permission string for each menu/sub-menu
            menu_permission = f"superadmin_assets.show_menumodel_{menu_namea}"
            sub_menu_permission = f"superadmin_assets.show_submenusmodel_{sub_menu_name.replace(' ','_').lower()}" if sub_menu_name else None
            # Check if the user has the necessary permissions
            has_menu_permission = request.user.has_perm(menu_permission)
            has_sub_menu_permission = request.user.has_perm(sub_menu_permission) if sub_menu_permission else True
            if has_menu_permission or request.user.profile.user_type != 'agent':
                if menu_name in showDataDict:
                    if has_sub_menu_permission or request.user.profile.user_type != 'agent':
                        if isinstance(showDataDict[menu_name], list):
                            showDataDict[menu_name].append({
                                sub_menu_name: sub_menu_url,
                        })
                else:
                    if sub_menu_name is None:
                        showDataDict[menu_name] = {
                            menu_name: menu_url,
                            "icon": icon,
                            "module_name": module_name
                        }
                    else:
                        if has_sub_menu_permission or request.user.profile.user_type != 'agent':
                            showDataDict[f"{menu_name}_icon"] = icon
                            showDataDict[menu_name] = [{
                                sub_menu_name: sub_menu_url,
                            }]

        # Include sidebardata in the response
        data = dict(serializer.data)
        data['sidebardata'] = showDataDict

        return Response(data)



class Testing(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        # attendances = user.attendances.all()
        # queryset = AttendanceSerializer(attendances, many=True).data
        appreciations = user.appreciations.all()
        queryset = AppreciationSerializer(appreciations, many=True).data
        pdb.set_trace()
        return Response({"results": queryset})
    
class CustomAuthGroupViewSetold(viewsets.ModelViewSet):
    queryset = CustomAuthGroup.objects.all()
    serializer_class = CustomAuthGroupSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        request.data['company_id'] = request.user.profile.company.id
        # request.data['branch_id'] = request.user.profile.branch.id
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
    
class CustomAuthGroupViewSet(viewsets.ModelViewSet):
    queryset = CustomAuthGroup.objects.all()
    serializer_class = CustomAuthGroupSerializer
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        if request.user.profile.user_type == 'superadmin':
            request.data['company_id'] = None
            branch = 'super'
            company = 'super'
        else:
            company = request.user.profile.company.id
            request.data['company_id'] = company
            branch= (request.data['branch_id'])
        # Uncomment if branch_id is required for non-superadmins
        # request.data['branch_id'] = request.user.profile.branch.id
        name = request.data['group']['name']
        if request.data['group']['name']:
            request.data['group']['name'] = f"{company}-{branch}-{name}"
            request.data['name'] = name
        permission_ids = request.data.get('permission_ids', [])
        if not isinstance(permission_ids, list) or not permission_ids:
            return Response(
                {"error": "permission_ids must be a non-empty list."},
                status=status.HTTP_400_BAD_REQUEST
            )

        permissions = Permission.objects.filter(id__in=permission_ids)
        if not permissions.exists():
            return Response(
                {"error": "No valid permissions found."},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            with transaction.atomic():
                custom_auth_group = serializer.save()
                group_id = custom_auth_group.group.id
                group = Group.objects.get(id=group_id)
                group.permissions.add(*permissions)
                group.save()
                return Response(
                    {
                        "message": f"Group '{group.name}' created and permissions added.",
                        "data": serializer.data,
                    },
                    status=status.HTTP_201_CREATED,
                    headers=self.get_success_headers(serializer.data)
                )
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @transaction.atomic
    def update(self, request, pk=None ,*args, **kwargs,):
        """
        Update group permissions.
        """
        instance = self.get_object()
        # request.data['branch_id'] = request.user.profile.branch.id
        order = CustomAuthGroup.objects.get(id=pk)
        serializer = CustomAuthGroupSerializer(order)
        serialized_data = serializer.data
        if request.user.profile.user_type == 'superadmin':
            request.data['company_id'] = None
            branch = 'super'
            company = 'super'
        else:
            company = request.user.profile.company.id
            request.data['company_id'] = company
            branch= (request.data['branch_id'])
        if 'group' in request.data:
            name = request.data['group']['name']
            request.data['name'] = name
            request.data['group']['name'] = f"{company}-{branch}-{name}"
            request.data['name'] = name
            if serialized_data['group']['name']==request.data['group']['name']:
                request.data.pop('group', None)
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        permission_ids = request.data.get('permission_ids', [])
        if permission_ids:
            permissions = Permission.objects.filter(id__in=permission_ids)
            if not permissions.exists():
                return Response(
                    {"error": "No valid permissions found."},
                    status=status.HTTP_404_NOT_FOUND
                )

        try:
            with transaction.atomic():
                serializer.save()
                group = Group.objects.get(id=serializer.data['group']['id'])
                group.permissions.clear()
                group.permissions.add(*permissions)
                group.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @transaction.atomic
    def destroy(self, request, *args, **kwargs):
        """
        Delete a group and its CustomAuthGroup — prevent deletion if assigned to users.
        """
        instance = self.get_object()

        if instance.group.user_set.exists():
            return Response(
                {"error": f"Cannot delete role '{instance.name}' because it is assigned to one or more users."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            with transaction.atomic():
                instance.group.permissions.clear()
                instance.group.delete()
                instance.delete()
                return Response({"message": "Deleted successfully."}, status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
    # def destroy(self, request, *args, **kwargs):
    #     """
    #     Delete a group and its associated permissions.
    #     """
        
    #     instance = self.get_object()
    #     try:
    #         with transaction.atomic():
    #             group = Group.objects.get(id=instance.group.id)
    #             group.permissions.clear()
    #             group.delete()
    #             instance.delete()
    #             return Response({"massage": "Deleted."},status=status.HTTP_204_NO_CONTENT)
    #     except Group.DoesNotExist:
    #         return Response({"error": "Group not found."}, status=status.HTTP_404_NOT_FOUND)
    #     except Exception as e:
    #         return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        

    def list(self, request, *args, **kwargs):
        """
        Get a list of CustomAuthGroup instances with their associated group, branch, and company details.
        """
        user = self.request.user
        if user.profile.user_type == 'superadmin':
            # Superadmins can access all CustomAuthGroup instances
            queryset =  CustomAuthGroup.objects.filter(company=None)
        else:
            # Filter CustomAuthGroup instances by the user's company
            queryset =  CustomAuthGroup.objects.filter(company=user.profile.company)
        # queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
class UserGroupViewSet(viewsets.ViewSet):
    """
    A ViewSet for managing user group memberships using user_id and group_id.
    """
    permission_classes = [IsAuthenticated]
    @action(detail=False, methods=['post'], url_path='add-user-to-group')
    def add_user_to_group(self, request):
        """
        Custom action to add a user to a group using user_id and group_id.
        """
        user_id = request.data.get('user_id')
        group_id = request.data.get('group_id')
        try:
            user = User.objects.get(id=user_id)
            group = Group.objects.get(id=group_id)
            user.groups.add(group)
            user.save()
            return Response({"message": f"User '{user.username}' added to group '{group.name}'."}, status=status.HTTP_200_OK)
        except User.DoesNotExist:
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)
        except Group.DoesNotExist:
            return Response({"error": "Group not found."}, status=status.HTTP_404_NOT_FOUND)
            
    @action(detail=False, methods=['post'], url_path='remove-group-from-user')
    def remove_group_from_user(self, request):
        """
        Remove a user from a specific group.
        """
        user_id = request.data.get('user_id')
        group_id = request.data.get('group_id')

        try:
            user = User.objects.get(id=user_id)
            group = Group.objects.get(id=group_id)

            user.groups.remove(group)  # Remove user from group
            return Response(
                {"message": f"User '{user.username}' removed from group '{group.name}'."},
                status=status.HTTP_200_OK
            )
        except User.DoesNotExist:
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)
        except Group.DoesNotExist:
            return Response({"error": "Group not found."}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['get'], url_path='list-group-members/(?P<group_id>\d+)')
    def list_group_members(self, request, group_id=None):
        """
        Custom action to list all members of a specific group using group_id.
        """
        try:
            group = Group.objects.get(id=group_id)
            users = group.user_set.all()
            serializer = UserSerializer(users, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Group.DoesNotExist:
            return Response({"error": "Group not found."}, status=status.HTTP_404_NOT_FOUND)
        
    @action(detail=False, methods=['get'], url_path='list-user-groups/(?P<user_id>\d+)')
    def list_user_groups(self, request, user_id=None):
        """
        Get all groups assigned to a specific user using user_id.
        """
        try:
            user = User.objects.get(id=user_id)
            groups = user.groups.all()
            group_data = [{"id": group.id, "name": group.name} for group in groups]
            return Response(group_data, status=status.HTTP_200_OK)
        except User.DoesNotExist:
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)
        
    @action(detail=False, methods=['post'], url_path='update-user-groups')
    def update_user_groups(self, request):
        user_id = request.data.get('user_id')
        new_group_id = request.data.get('group_id')

        try:
            user = User.objects.get(id=user_id)  # Fetch the user by ID
            new_group = Group.objects.get(id=new_group_id)

            # Remove the user from all existing groups
            user.groups.clear()

            # Add the user to the new group
            user.groups.add(new_group)
            user.save()

            return Response(
                {
                    "message": f"User '{user.username}' removed from all groups and added to group '{new_group.name}'."
                },
                status=status.HTTP_200_OK
            )
        except User.DoesNotExist:
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)
        except Group.DoesNotExist:
            return Response({"error": "New group not found."}, status=status.HTTP_404_NOT_FOUND)

        
class GroupPermissionViewSet(viewsets.ViewSet):
    """
    A ViewSet for managing permissions within a group.
    """
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['post'], url_path='add-permissions-to-group')
    def add_permissions_to_group(self, request):
        """
        Add multiple permissions to a group.
        """
        group_id = request.data.get('group_id')
        permission_ids = request.data.get('permission_ids', [])

        if not isinstance(permission_ids, list):
            return Response({"error": "permission_ids must be a list."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            group = Group.objects.get(id=group_id)
            permissions = Permission.objects.filter(id__in=permission_ids)
            if permissions.exists():
                group.permissions.add(*permissions)
                group.save()
                return Response(
                    {"message": f"Permissions added to group '{group.name}'."},
                    status=status.HTTP_200_OK
                )
            else:
                return Response({"error": "No valid permissions found."}, status=status.HTTP_404_NOT_FOUND)
        except Group.DoesNotExist:
            return Response({"error": "Group not found."}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['put'], url_path='update-permissions-of-group')
    def update_permissions_of_group(self, request):
        """
        Update (replace) the permissions of a group with new permissions.
        """
        group_id = request.data.get('group_id')
        permission_ids = request.data.get('permission_ids', [])

        if not isinstance(permission_ids, list):
            return Response({"error": "permission_ids must be a list."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            group = Group.objects.get(id=group_id)
            new_permissions = Permission.objects.filter(id__in=permission_ids)

            if new_permissions.exists():
                group.permissions.set(new_permissions)
                group.save()
                return Response(
                    {"message": f"Permissions updated for group '{group.name}'."},
                    status=status.HTTP_200_OK
                )
            else:
                return Response({"error": "No valid permissions found."}, status=status.HTTP_404_NOT_FOUND)
        except Group.DoesNotExist:
            return Response({"error": "Group not found."}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['delete'], url_path='delete-permissions-from-group')
    def delete_permissions_from_group(self, request):
        """
        Delete specific permissions from a group.
        """
        group_id = request.data.get('group_id')
        permission_ids = request.data.get('permission_ids', [])

        if not isinstance(permission_ids, list):
            return Response({"error": "permission_ids must be a list."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            group = Group.objects.get(id=group_id)
            permissions_to_remove = Permission.objects.filter(id__in=permission_ids)

            if permissions_to_remove.exists():
                group.permissions.remove(*permissions_to_remove)
                group.save()
                return Response(
                    {"message": f"Permissions removed from group '{group.name}'."},
                    status=status.HTTP_200_OK
                )
            else:
                return Response({"error": "No valid permissions found."}, status=status.HTTP_404_NOT_FOUND)
        except Group.DoesNotExist:
            return Response({"error": "Group not found."}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['get'], url_path='list-group-permissions/(?P<group_id>\d+)')
    def list_group_permissions(self, request, group_id=None):
        """
        List all permissions of a specific group using group_id.
        """
        try:
            group = Group.objects.get(id=group_id)
            permissions = group.permissions.all()
            serializer = PermissionSerializer(permissions, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Group.DoesNotExist:
            return Response({"error": "Group not found."}, status=status.HTTP_404_NOT_FOUND)

class PermmisionViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = Permission.objects.all()
    serializer_class = PermissionSerializer
    pagination_class = None 

class FetchPermissionView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request, model_name=None):
        request.data['name_list'].extend([])
        if not request.data or 'name_list' not in request.data or not request.data['name_list']:
            return Response({"detail": "Request body must contain a non-empty 'name_list'."}, status=400)
        name_list = [name.replace(" ", "_").lower() for name in request.data.get('name_list', [])]
        content_type_ids = ContentType.objects.filter(Q(model__in=name_list) | Q(model__startswith='settings_')).values_list('id', flat=True)
        permissions = Permission.objects.filter(content_type__in=content_type_ids)
        permissions_dict = {}
        company_name = "SuperAdmin"  # Default if no company exists
        try:
            if self.request.user.profile.company:  
                company_name = str(self.request.user.profile.company.name)
        except AttributeError:
            pass 
        for permission in permissions:
            if "Products Can work on this" in permission.name and str(company_name) not in permission.name:
                continue
            if (
                    "Department Can view" in permission.name
                    and str(company_name) not in permission.name
                    and permission.name not in [
                        "Department Can view all departments",
                        "Department Can view own department"
                    ]
                ):
                    continue
            if request.user.profile.user_type != "superadmin" and permission.name.lower().startswith("show_settingsmenu") and not request.user.has_perm(f"{permission.content_type.app_label}.{permission.codename}"):
                continue
            permissions_dict[permission.codename] = permission.id

        # for permission in permissions:
        #     if "Products Can work on this" in permission.name:
        #         print(permission.name)
        #         if str(company_name) not in permission.name:
        #             print("000000000condiotn")
        #             continue
        #     permissions_dict[permission.codename] = permission.id
        return Response(permissions_dict)
        
class PickUpPointView(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = PickUpPoint.objects.all()
    serializer_class = PickUpPointSerializer
    def get_permissions(self):
        permission_map = {
            'create': ['superadmin_assets.show_settingsmenu_pick_up_point', 'superadmin_assets.add_settingsmenu'],
            'update': ['superadmin_assets.show_settingsmenu_pick_up_point', 'superadmin_assets.change_settingsmenu'],
            'destroy': ['superadmin_assets.show_settingsmenu_pick_up_point', 'superadmin_assets.delete_settingsmenu'],
            'retrieve': ['superadmin_assets.show_settingsmenu_pick_up_point', 'superadmin_assets.view_settingsmenu'],
            'list': ['superadmin_assets.show_settingsmenu_pick_up_point', 'superadmin_assets.view_settingsmenu']
        }
        
        action = self.action
        if action in permission_map:
            permissions = permission_map[action]
            return [HasPermission(perm) for perm in permissions]  # Return a list of permission checks
    
        return super().get_permissions()
    def get_queryset(self):
        """
        Filter pickup points based on the authenticated user's company.
        """
        user = self.request.user
        vendor_id = self.request.query_params.get('vendor_id', None)
        # Ensure user has a company field
        if hasattr(user.profile, 'company') and user.profile.company:
            queryset = PickUpPoint.objects.filter(company=user.profile.company)
        else:
            queryset = PickUpPoint.objects.filter(company=None)
        
        if vendor_id:
            queryset = queryset.filter(vendor_id=vendor_id)
            
        return queryset
        # If no company is associated, return an empty queryset
        return PickUpPoint.objects.none()
    @transaction.atomic
    def create(self, request, *args, **kwargs):
        user = request.user
        vendor_id = request.data.get("vendor")
        if not vendor_id:
            return Response({"error": "Vendor ID is required."}, status=status.HTTP_400_BAD_REQUEST)        
        # ✅ Create a mutable copy of request.data
        mutable_data = request.data.copy()
        # Set company and branch based on the authenticated user
        mutable_data["company"] = user.profile.company.id
        if "branches" not in mutable_data:
            mutable_data["branches"] = [user.profile.branch.id]

        mutable_data["vendor"] = vendor_id
        vendor_id = mutable_data.get("vendor")
        trackdata = ShipmentModel.objects.get(
                id=vendor_id
            )
        serializer = ShipmentSerializer(trackdata)
        serialized_data = serializer.data
        if not serialized_data:
            return Response({"error": "Vendor not found", "data": {}}, status=status.HTTP_400_BAD_REQUEST)
        
        api_response = None
        if serialized_data['shipment_vendor']['name'].lower() == "other":
            serializer = self.get_serializer(data=mutable_data)
            if serializer.is_valid():
                instance = serializer.save()  # Save to DB
                return Response(
                    {
                        "status": True,
                        "message": "Data saved successfully!",
                        "data": serializer.data,
                        "api_response": api_response,
                    },
                    status=status.HTTP_201_CREATED,
                )
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        elif serialized_data['shipment_vendor']['name'].lower() == 'shiprocket':
            shiprocket_payload = {
                "pickup_location": mutable_data["pickup_location_name"],
                "name": mutable_data["contact_person_name"],
                "email": mutable_data["contact_email"],
                "phone": mutable_data["contact_number"],
                "address": mutable_data["complete_address"],
                "address_2": mutable_data.get("landmark", ""),
                "city": mutable_data["city"],
                "state": mutable_data["state"],
                "country": mutable_data["country"],
                "pin_code": mutable_data["pincode"],
                "is_default": False,
            }
            if serialized_data['credential_username']:
                shiprocket_service = ShiprocketScheduleOrder(
                    serialized_data['credential_username'], serialized_data['credential_password']
                )
                api_response = shiprocket_service.add_pickup_location(shiprocket_payload)
                # Handle Shiprocket API response
                if not api_response.get("success"):
                    return Response(
                        {
                            "error": "Failed to create pickup location in Shiprocket.",
                            "details": api_response,
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                pickup_code = api_response.get("address", {}).get("pickup_code")
                if pickup_code:
                    mutable_data["pickup_code"] = pickup_code
                # mutable_data['vendor_response'] = api_response
            # api_response = self.send_to_shiprocket(shiprocket_payload)
        elif serialized_data['shipment_vendor']['name'].lower() == "tekipost":
            tekipost_payload = {
                "warehouse_name": mutable_data["pickup_location_name"],
                "contact_person_name": mutable_data["contact_person_name"],
                "contact_no": mutable_data["contact_number"],
                "address_line_1": mutable_data["complete_address"],
                "address_line_2": mutable_data.get("landmark", ""),
                "landmark": mutable_data.get("landmark", ""),
                "pincode": mutable_data["pincode"],
                "city": mutable_data["city"],
                "state": mutable_data["state"]
            }
            if serialized_data['credential_username']:
                takipost_service = TekipostService(
                    serialized_data['credential_username'], serialized_data['credential_password']
                )
                api_response = takipost_service.add_warehouse(tekipost_payload)
                # Handle Shiprocket API response
                if not api_response.get("success"):
                    return Response(
                        {
                            "error": "Failed to create pickup location in takipost.",
                            "details": api_response,
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                pickup_code = api_response.get("data", {}).get("id")
                if pickup_code:
                    mutable_data["pickup_code"] = pickup_code
                # mutable_data['vendor_response'] = api_response
       # The above code snippet is a part of a Python function that processes serialized data related
       # to a shipment vendor.
        elif serialized_data['shipment_vendor']['name'].lower() == "nimbuspost":
            tekipost_payload = {
                "warehouse_name": mutable_data["pickup_location_name"],
                "contact_person_name": mutable_data["contact_person_name"],
                "contact_no": mutable_data["contact_number"],
                "address_line_1": mutable_data["complete_address"],
                "address_line_2": mutable_data.get("landmark", ""),
                "landmark": mutable_data.get("landmark", ""),
                "pincode": mutable_data["pincode"],
                "city": mutable_data["city"],
                "state": mutable_data["state"]
            }
            # api_response = self.send_to_tekipost(tekipost_payload)
            api_response = {
                "success": True,
                "message": "Simulated API success for Nimbuspost",
                "data": {}  # Add any mock data here if needed
            }
            
        
        else:
            return Response({"error": "Invalid vendor specified"}, status=status.HTTP_400_BAD_REQUEST)
        # ✅ Only Save Data in DB if API Call is Successful
        if api_response.get("success"):
            serializer = self.get_serializer(data=mutable_data)
            if serializer.is_valid():
                instance = serializer.save()
                return Response(
                    {
                        "status": True,
                        "message": "Data saved successfully!",
                        "data": serializer.data,
                        "api_response": api_response,
                    },
                    status=status.HTTP_201_CREATED,
                )
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({"error": "Third-party API failed", "details": api_response}, status=status.HTTP_400_BAD_REQUEST)

        






class TargetView(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = UserTargetsDelails.objects.all()
    serializer_class = UserTargetSerializer
    def get_permissions(self):
        permission_map = {
            'create': ['superadmin_assets.show_submenusmodel_targets', 'superadmin_assets.add_submenusmodel'],
            'update': ['superadmin_assets.show_submenusmodel_targets', 'superadmin_assets.change_submenusmodel'],
            'destroy': ['superadmin_assets.show_submenusmodel_targets', 'superadmin_assets.delete_submenusmodel'],
            'retrieve': ['superadmin_assets.show_submenusmodel_targets', 'superadmin_assets.view_submenusmodel'],
            'list': ['superadmin_assets.show_submenusmodel_targets', 'superadmin_assets.view_submenusmodel']
        }
        
        action = self.action
        if action in permission_map:
            permissions = permission_map[action]
            return [HasPermission(perm) for perm in permissions]  # Return a list of permission checks
    
        return super().get_permissions()
    def get_queryset(self):
        user = self.request.user
        base_queryset = UserTargetsDelails.objects.filter(user__profile__status=1)

        if user.profile.user_type == 'admin':
            return base_queryset.filter(company=user.profile.company, branch=user.profile.branch)
        elif user.profile.user_type == 'superadmin':
            return base_queryset.filter(company=None)

        return base_queryset.filter(created_by=user)
    
    def perform_create(self, serializer):
        instance = serializer.save(created_by=self.request.user)

        # ✅ Send notification to the assigned user
        Notification.objects.create(
            user=instance.user,
            message=f"You have been assigned a new target for {instance.monthyear}.",
            url=f"#",  
            notification_type="chat_message"  # You can use "notice" or define a new type like "target"
        )

    @action(detail=False, methods=['post'], url_path='upload-csv')
    def upload_csv(self, request):
        file = request.FILES.get('file')
        if not file:
            return Response({'error': 'CSV file is required.'}, status=400)

        csv_file = TextIOWrapper(file.file, encoding='utf-8')
        reader = csv.DictReader(csv_file)
        errors = []
        instances = []

        try:
            with transaction.atomic():
                for i, row in enumerate(reader, start=1):
                    try:
                        user = User.objects.get(id=row['user_id'])
                        branch = Branch.objects.get(id=row['branch_id'])
                        company = request.user.profile.company

                        target = UserTargetsDelails(
                            daily_amount_target=row['daily_amount_target'],
                            daily_orders_target=row['daily_orders_target'],
                            monthly_amount_target=row['monthly_amount_target'],
                            monthly_orders_target=row['monthly_orders_target'],
                            user=user,
                            monthyear=row['monthyear'],
                            branch=branch,
                            company=company,
                            created_by=request.user
                        )
                        instances.append(target)
                    except Exception as e:
                        raise ValueError(f"Row {i}: {str(e)}")  # Force rollback on any row error

                UserTargetsDelails.objects.bulk_create(instances)

                for target in instances:
                    Notification.objects.create(
                        user=target.user,
                        message=f"You have been assigned a new target for {target.monthyear}.",
                        url="#",
                        notification_type="target"
                    )

        except Exception as e:
            return Response({'error': str(e)}, status=400)

        return Response({'message': f'{len(instances)} targets created successfully.'}, status=201)

class AdminBankDetailsViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = AdminBankDetails.objects.all()
    serializer_class = AdminBankDetailsSerializers
    def get_permissions(self):
        permission_map = {
            'create': ['superadmin_assets.show_settingsmenu_bank_details_setting', 'superadmin_assets.add_settingsmenu'],
            'update': ['superadmin_assets.show_settingsmenu_bank_details_setting', 'superadmin_assets.change_settingsmenu'],
            'destroy': ['superadmin_assets.show_settingsmenu_bank_details_setting', 'superadmin_assets.delete_settingsmenu'],
            'retrieve': ['superadmin_assets.show_settingsmenu_bank_details_setting', 'superadmin_assets.view_settingsmenu'],
            'list': ['superadmin_assets.show_settingsmenu_bank_details_setting', 'superadmin_assets.view_settingsmenu']
        }
        
        action = self.action
        if action in permission_map:
            permissions = permission_map[action]
            return [HasPermission(perm) for perm in permissions]  # Return a list of permission checks
    
        return super().get_permissions()
    def create(self, request, *args, **kwargs):
        data = request.data
        user_profile = Employees.objects.get(user__id=request.data['user'])
        branch_id = user_profile.branch.id if user_profile.branch else None
        company_id = user_profile.company.id if user_profile.company else None

        # Add branch and company to the data
        data = request.data.copy()
        data['branch'] = branch_id
        data['company'] = company_id
        if data.get('account_number') != data.get('re_account_number'):
            return Response(
                {"error": "Account number and re-entered account number must match."},
                status=status.HTTP_400_BAD_REQUEST
            )
        user = request.user
        priority = data.get('priority')
        if AdminBankDetails.objects.filter(user=user, priority=priority).exists():
            return Response(
                {"error": f"Priority {priority} already exists for this user."},
                status=status.HTTP_400_BAD_REQUEST
            )
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    def get_queryset(self):
        """
        Optionally filter accounts based on the user role.
        Superadmins and admins can view all accounts. Others can view only accounts they've created.
        """
        user = self.request.user
        if user.profile.user_type == 'admin':
            # Admin can view all accounts within their company
            return AdminBankDetails.objects.filter(company=user.profile.company)
        elif user.profile.user_type == 'superadmin':
            # Superadmin can view accounts not associated with any company
            return AdminBankDetails.objects.filter(company=None)

        # Other users (if any) can only view accounts they've created
        return AdminBankDetails.objects.filter(created_by=user)
    
class AddAllowIpViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = AllowedIP.objects.all()
    serializer_class = AllowedIPSerializers
    def get_permissions(self):
        permission_map = {
            'create': ['superadmin_assets.show_settingsmenu_ip_access_setting', 'superadmin_assets.add_settingsmenu'],
            'update': ['superadmin_assets.show_settingsmenu_ip_access_setting', 'superadmin_assets.change_settingsmenu'],
            'destroy': ['superadmin_assets.show_settingsmenu_ip_access_setting', 'superadmin_assets.delete_settingsmenu'],
            'retrieve': ['superadmin_assets.show_settingsmenu_ip_access_setting', 'superadmin_assets.view_settingsmenu'],
            'list': ['superadmin_assets.show_settingsmenu_ip_access_setting', 'superadmin_assets.view_settingsmenu']
        }
        
        action = self.action
        if action in permission_map:
            permissions = permission_map[action]
            return [HasPermission(perm) for perm in permissions]  # Return a list of permission checks
    
        return super().get_permissions()
    def get_queryset(self):
        """
        Filter pickup points based on the authenticated user's company.
        """
        user = self.request.user

        # Ensure user has a company field
        if hasattr(user.profile, 'company') and user.profile.company:
            return AllowedIP.objects.filter(company=user.profile.company)
        else:
            return AllowedIP.objects.filter(company=None)
        
    # @transaction.atomic
    # def create(self, request, *args, **kwargs):
    #     user = request.user
    #     request.data['company'] = user.profile.company.id
    #     return super().create(request, *args, **kwargs)
    @transaction.atomic
    def create(self, request, *args, **kwargs):
        user = request.user
        request.data['company'] = user.profile.company.id
        try:
            return super().create(request, *args, **kwargs)
        except IntegrityError:
            return Response({"error": "Duplicate IP not allowed for the same branch."}, status=status.HTTP_400_BAD_REQUEST)
class QcViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset =QcTable.objects.all()
    serializer_class= QcSerialiazer

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        user = request.user
        return super().create(request, *args, **kwargs)
    
    @transaction.atomic
    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data)
    
class AssignRole(APIView):
    def post(self, request, *args, **kwargs):
        # Get the teamlead, manager, and agent_list from the request data
        teamlead_id = request.data.get('teamlead')
        manager_id = request.data.get('manager')
        agent_list = request.data.get('agent_list')

        # Validate if teamlead and manager are provided
        if not teamlead_id:
            return Response({"Success": False, "Message": "Teamlead required."},
                            status=status.HTTP_400_BAD_REQUEST)
        if not manager_id:
            return Response({"Success": False, "Message": "Manager required."},
                            status=status.HTTP_400_BAD_REQUEST)
        
        if not agent_list or not isinstance(agent_list, list):
            return Response({"Success": False, "Message": "Agent list is required and should be a list."},
                            status=status.HTTP_400_BAD_REQUEST)

        # Try to get the teamlead and manager instances
        try:
            teamlead = Employees.objects.get(user_id=teamlead_id)
        except Employees.DoesNotExist:
            return Response({"Success": False, "Message": "Teamlead not found."},
                            status=status.HTTP_404_NOT_FOUND)

        try:
            manager = Employees.objects.get(user_id=manager_id)
        except Employees.DoesNotExist:
            return Response({"Success": False, "Message": "Manager not found."},
                            status=status.HTTP_404_NOT_FOUND)

        # List to hold updated agents
        updated_profiles = []
        teamlead_profile = Employees.objects.get(user_id=teamlead_id)
        # teamlead_profile.teamlead = teamlead.user
        teamlead_profile.manager = manager.user
        teamlead_profile.save()
        for agent_id in agent_list:
            try:
                agent_profile = Employees.objects.get(user_id=agent_id)

                # Assign the teamlead and manager to the agent
                agent_profile.teamlead = teamlead.user
                agent_profile.manager = manager.user
                agent_profile.save()

                # Add the updated agent username to the list
                updated_profiles.append(agent_profile.user.username)
            except Employees.DoesNotExist:
                return Response({"Success": False, "Message": f"Agent with ID {agent_id} not found."},
                                status=status.HTTP_404_NOT_FOUND)

        return Response(
            {"Success": True, "Data": {"Updated Agents": updated_profiles,"updated_teamlead": teamlead_profile.user.username}},
            status=status.HTTP_200_OK,
        )

class TeamleadViewSet(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user
        branch_id = request.GET.get("branch_id")
        company_id = getattr(user.profile, "company_id", None)
        manager_id = request.GET.get("manager_id")

        if not company_id:
            return Response(
                {"success": False, "message": "Company ID is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        filters = {"company_id": company_id}

        if branch_id:
            filters["branch_id"] = branch_id
        if user.profile.user_type == "admin" or user.has_perm("dashboard.view_all_dashboard_team_order_list"):
            pass  # No changes to manager/teamlead filters
        elif user.has_perm("dashboard.view_manager_dashboard_team_order_list"):
            filters["manager_id"] = user.id
        elif user.has_perm("dashboard.view_own_team_dashboard_team_order_list"):
            filters["user_id"] = user.id
        else:
            return Response(
                {"success": False, "message": "You do not have permission to view this data."},
                status=status.HTTP_403_FORBIDDEN
            )

        if manager_id:
            try:
                manager_id = int(manager_id)
                filters["manager_id"] = manager_id
            except ValueError:
                return Response(
                    {"success": False, "message": "Invalid manager_id"},
                    status=status.HTTP_400_BAD_REQUEST
                )
        else:
            filters["manager__isnull"] = False
        filters['teamlead__isnull'] = True
        filters['status'] = 1
        teamleads = Employees.objects.filter(**filters)
        # print(teamleads,"-----------------------2266")
        # teamlead_set = set()
        # for emp in teamleads:
        #     teamlead_set.add(emp.teamlead.id)
        # teamleads = Employees.objects.filter(user_id__in=teamlead_set)
        # Debugging
       

        if not teamleads.exists():
            return Response(
                {"success": False, "message": "No team leads found for the given manager."},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = TeamUserProfile(teamleads, many=True)
        return Response(
            {"success": True, "teamlead_list": serializer.data},
            status=status.HTTP_200_OK
        )

class ManagerViewSet(APIView):
   
    permission_classes = [IsAuthenticated]  # Only authenticated users can access this view
    
    def get(self, request, *args, **kwargs):
        # Get company_id and branch_id from the request query parameters
        # company_id = request.query_params.get('company_id', None)
        # branch_id = request.query_params.get('branch_id', None)
        user = request.user
        branch_id = request.GET.get("branch_id")
        company_id = user.profile.company.id
        # Ensure that either company_id or branch_id is provided
        if not company_id:
            return Response(
                {"Success": False, "Message": "Either company_id  is required."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Query to get distinct manager values, filtered by company_id and branch_id
        managers = Employees.objects.exclude(manager=None,status=1)
        
        if company_id:
            managers = managers.filter(company=company_id)
        if branch_id:
            managers = managers.filter(branch=branch_id)

        manager_users = Employees.objects.filter(user__id__in=managers.values_list("manager", flat=True)).distinct()

        # managers = managers.values('manager').distinct()

        # Fetching the manager users based on the distinct IDs
        # manager_users = Employees.objects.filter(user__in=[manager['manager'] for manager in managers])
        
        # Serialize the manager users
        serializer = TeamUserProfile(manager_users, many=True)
        
        # Return the response with the serialized data
        return Response(
            {"Success": True, "Data":  serializer.data},
            status=status.HTTP_200_OK
        )



class AgentListByTeamleadAPIView(APIView):

    permission_classes = [IsAuthenticated] 
    """
    Returns the list of agents for a specific teamlead.
    Accepts 'teamlead_id' as a query parameter.
    """
    def get(self, request, *args, **kwargs):
        teamlead_id = request.query_params.get('teamlead_id', None)
        
        # Ensure that teamlead_id is provided
        if not teamlead_id:
            return Response(
                {"Success": False, "Error": "teamlead_id must be provided."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Filter agents based on teamlead_id
        agents = Employees.objects.filter(teamlead_id=teamlead_id,status=1)
        
        # Serialize the result and return the response
        serializer = TeamUserProfile(agents, many=True)
        return Response(
            {"Success": True, "Data": {"Agents": serializer.data}},
            status=status.HTTP_200_OK
        )
    

class AgentListByManagerAPIView(APIView):
   
    def get(self, request, *args, **kwargs):
        manager_id = request.query_params.get('manager_id', None)
        
        if not manager_id:
            return Response(
                {"Success": False, "Error": "manager_id must be provided."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Filter agents based on manager_id
        agents = Employees.objects.filter(manager_id=manager_id,status=1)
        
        # Serialize the result and return the response
        serializer = TeamUserProfile(agents, many=True)
        return Response(
            {"Success": True, "Data": {"Agents": serializer.data}},
            status=status.HTTP_200_OK
        )


class UpdateTeamLeadManagerAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        user_id = request.data.get('user_id')  # Get the user_id from the request data

        if not user_id:
            return Response(
                {"Success": False, "Message": "user_id is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user_profile = Employees.objects.get(user__id=user_id)  # Get the UserProfile by user_id
        except Employees.DoesNotExist:
            return Response(
                {"Success": False, "Message": "UserProfile not found for the given user_id"},
                status=status.HTTP_404_NOT_FOUND
            )

        # Update the teamlead and manager to None
        user_profile.teamlead = None
        user_profile.manager = None
        user_profile.save()

        # Prepare the response
        serializer = UpdateTeamLeadManagerSerializer(user_profile)

        return Response(
            {
                "Success": True,
                "Data": {
                    "Agents": serializer.data
                }
            },
            status=status.HTTP_200_OK
        )
    



class StickyNoteViewSet(viewsets.ModelViewSet):
    serializer_class = StickyNoteSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
            Filter sticky notes by the authenticated user.
        """
        # time_threshold = timezone.now() - timedelta(hours=24)
        return StickyNote.objects.filter(created_by=self.request.user)

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


def merge_and_format_date_ranges(leaves):
    """
    Merges overlapping date ranges and formats them in 'DD MMM, YYYY to DD MMM, YYYY' format.
    :param leaves: Queryset of leave entries with `start_date` and `end_date`.
    :return: Merged and formatted date ranges.
    """
    # Sort by start date
    sorted_leaves = sorted(leaves, key=lambda x: x.start_date)

    merged_ranges = []
    for leaves in sorted_leaves:
        if not merged_ranges:
            merged_ranges.append(leaves)
        else:
            # Merge ranges if overlapping or consecutive
            if leaves.start_date <= merged_ranges[-1].end_date + timedelta(days=1):
                merged_ranges[-1].end_date = max(merged_ranges[-1].end_date, leaves.end_date)
            else:
                merged_ranges.append(leaves)

    # Format the merged date ranges to the desired string format
    formatted_ranges = []
    for leaves in merged_ranges:
        formatted_range = f"{leaves.start_date.strftime('%d %b, %Y')} to {leaves.end_date.strftime('%d %b, %Y')}"
        formatted_ranges.append({
            "date_range": formatted_range,
            "reason": leaves.reason,
            "type": leaves.type,
            "status": leaves.status
        })

    return formatted_ranges


class IsSuperAdminPermission(IsAuthenticated):
    def has_permission(self, request, view):
        # Check if the user is authenticated
        if not request.user.is_authenticated:
            return False
        
        # Only allow superadmins to list inquiries or update status
        if view.action == 'list' and hasattr(request.user, 'profile') and request.user.profile.user_type != 'superadmin':
            return False
        
        # Allow status change only for superadmins
        if view.action == 'update_status' and hasattr(request.user, 'profile') and request.user.profile.user_type != 'superadmin':
            return False
        
        return super().has_permission(request, view)

class CompanyInquiryViewSet(viewsets.ModelViewSet):
    queryset = CompanyInquiry.objects.all()
    serializer_class = CompanyInquirySerializer
    permission_classes = [IsSuperAdminPermission]  # Restrict access to superadmin for list and status change

    def get_permissions(self):
        if self.action == 'create':
            self.permission_classes = []  # Allow anyone to create inquiries
        return super().get_permissions()

    def create(self, request, *args, **kwargs):
        """Allow anyone to submit an inquiry."""
        return super().create(request, *args, **kwargs)

    @action(detail=True, methods=['patch'], permission_classes=[IsSuperAdminPermission])
    def update_status(self, request, pk=None):
        inquiry = self.get_object()
        new_status = request.data.get('status')

        if new_status == "approved":
            # Create the company
            company_data = {
                'name': inquiry.company_name,
                'company_email': inquiry.company_email,
                'company_phone': inquiry.company_phone,
                'company_website': inquiry.company_website,
                'company_address': inquiry.company_address,
            }
            package = Package.objects.get(name="demo")
            company = Company.objects.create(package=package,**company_data)

            # Generate username by combining full name and company name
            username = f"{inquiry.full_name.split()[0]}_{inquiry.company_name.replace(' ', '').lower()}"

            # Create the user
            user = User.objects.create_user(
                username=username,
                email=inquiry.email,
                password= inquiry.password,  # Ensure this password is securely handled in a real app
            )

            # Create the user profile
            Employees.objects.create(
                user=user,
                contact_no=inquiry.contact_number,
                gender='m',  # Default gender
                marital_status="unmarried",  # Default marital status
                user_type="admin",  # Automatically set user type as 'admin'
                company=company
            )

            # Update the inquiry status to 'approved'
            inquiry.status = new_status
            inquiry.company = company  # Link to the created company
            inquiry.save()

            return Response({
                'message': 'Status updated to approved, user and company created.',
                'inquiry': CompanyInquirySerializer(inquiry).data
            }, status=status.HTTP_200_OK)

        else:
            # If the status is not 'approved', just update the status
            inquiry.status = new_status
            inquiry.save()

            return Response({
                'message': f'Status updated to {new_status}.'
            }, status=status.HTTP_200_OK)



class ForceLogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, user_id):
        # Check if the user is superadmin or admin
        if request.user.profile.user_type not in ['admin', 'superadmin']:
            raise PermissionDenied(detail="You do not have permission to force logout a user.")

        try:
            user_to_logout = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)

        # Delete the user's existing token (Force logout)
        existing_token = Token.objects.filter(user=user_to_logout).first()
        if existing_token:
            existing_token.delete()  # Deleting the existing token will force the user to logout

        # Respond that the user has been logged out
        return Response({"detail": f"User {user_to_logout.username} has been logged out."}, status=status.HTTP_200_OK)
    



class CSVUserUploadView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrSuperAdmin]

    def post(self, request, *args, **kwargs):
        if 'file' not in request.FILES:
            return Response({"Error": "No file provided"}, status=status.HTTP_400_BAD_REQUEST)

        csv_file = request.FILES['file']

        # Ensure it's a CSV
        if not csv_file.name.endswith('.csv'):
            return Response({"Error": "File is not a CSV"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            file_data = csv_file.read().decode('utf-8')
            io_string = io.StringIO(file_data)
            reader = csv.DictReader(io_string)

            users_data = []

            with transaction.atomic():
                for row in reader:
                    try:
                        # Extract profile fields
                        profile_data = {
                            "gender": row.get("gender"),
                            "contact_no": row.get("contact_no"),
                            "marital_status": row.get("marital_status"),
                            "user_type": row.get("user_type"),
                            "company": row.get("company"),
                            "branch": row.get("branch"),
                            "designation": row.get("designation"),
                            "department": row.get("department"),
                        }

                        # Extract user fields
                        user_data = {
                            "username": row.get("username"),
                            "password": row.get("password"),
                            "first_name": row.get("first_name"),
                            "last_name": row.get("last_name"),
                            "email": row.get("email"),
                            "profile": profile_data,
                        }

                        users_data.append(user_data)

                    except Exception as e:
                        return Response({"Error": f"Error processing row: {row}. Error: {str(e)}"},
                                        status=status.HTTP_400_BAD_REQUEST)

                # Save all users
                serializer = UserSerializer(data=users_data, many=True)
                if serializer.is_valid():
                    saved_users = serializer.save()

                    # Assign groups after users are created
                    io_string.seek(0)  # Reset CSV reader to first row
                    next(reader)  # Skip headers

                    for user, row in zip(saved_users, reader):
                        group_id = row.get('role')  # CSV column "role" must have Group ID
                        if group_id:
                            try:
                                group = Group.objects.get(id=group_id)
                                user.groups.add(group)
                            except Group.DoesNotExist:
                                return Response({
                                    "Error": f"Group with ID '{group_id}' not found for user '{user.username}'."
                                }, status=status.HTTP_400_BAD_REQUEST)

                    return Response({
                        "Success": True,
                        "Message": "Users uploaded and groups assigned successfully.",
                        "Data": serializer.data
                    }, status=status.HTTP_201_CREATED)

                else:
                    return Response({
                        "Success": False,
                        "Message": "Invalid data.",
                        "Errors": serializer.errors
                    }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({"Error": f"An error occurred: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)

# class CSVUserUploadView(APIView):
#     permission_classes = [IsAuthenticated, IsAdminOrSuperAdmin]

#     def post(self, request, *args, **kwargs):
#         if 'file' not in request.FILES:
#             return Response({"Error": "No file provided"}, status=status.HTTP_400_BAD_REQUEST)

#         csv_file = request.FILES['file']

#         # Ensure the file is a CSV
#         if not csv_file.name.endswith('.csv'):
#             return Response({"Error": "File is not a CSV"}, status=status.HTTP_400_BAD_REQUEST)

#         try:
#             # Read the CSV file
#             file_data = csv_file.read().decode('utf-8')
#             io_string = io.StringIO(file_data)
#             reader = csv.DictReader(io_string)

#             users_data = []
#             user_index = 0  # For round-robin logic if needed
#             roles_in_use = []  # To track user roles, if required for additional logic

#             with transaction.atomic():  # Start a database transaction
#                 for row in reader:
#                     try:
#                         # Extract user data and profile data from CSV
#                         profile_data = {
#                             "gender": row.get("gender"),
#                             "contact_no": row.get("contact_no"),
#                             "marital_status": row.get("marital_status"),
#                             "user_type": row.get("user_type"),
#                             "company": row.get("company"),
#                             "branch": row.get("branch"),
#                             "designation": row.get("designation"),
#                             "department": row.get("department"),
#                         }

#                         user_data = {
#                             "username": row.get("username"),
#                             "password": row.get("password"),
#                             "first_name": row.get("first_name"),
#                             "last_name": row.get("last_name"),
#                             "email": row.get("email"),
#                             "profile": profile_data,
#                         }

#                         users_data.append(user_data)

#                     except Exception as e:
#                         # Log and rollback on row-level error
#                         return Response({"Error": f"Error processing row: {row}. Error: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)

#                 # Save users in bulk using the serializer
#                 serializer = UserSerializer(data=users_data, many=True)
#                 if serializer.is_valid():
#                     serializer.save()
#                     return Response({
#                         "Success": True,
#                         "Message": "Users uploaded successfully.",
#                         "Data": serializer.data
#                     }, status=status.HTTP_201_CREATED)
#                 else:
#                     # Serializer errors will trigger rollback
#                     return Response({
#                         "Success": False,
#                         "Message": "Invalid data.",
#                         "Errors": serializer.errors
#                     }, status=status.HTTP_400_BAD_REQUEST)

#         except Exception as e:
#             # Catch general errors
#             return Response({"Error": f"An error occurred: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)


class UserExportView(APIView):
    """
    API endpoint to export users based on a filter (e.g., by company, user type).
    """
    permission_classes = [IsAuthenticated, IsAdminOrSuperAdmin]

    def get(self, request, *args, **kwargs):
        # Get the filters from query parameters
        user = self.request.user
        company_id = user.profile.company
        # user_type = request.query_params.get('user_type', None)
        # branch_id = request.query_params.get('branch_id', None)

        # Start with all users
        queryset = User.objects.all()
        
        # Apply filters based on query parameters
        if user.profile.user_type != "superadmin":
            queryset = queryset.filter(profile__company_id=company_id)
        # if user_type:
        #     queryset = queryset.filter(profile__user_type=user_type)
        # if branch_id:
        #     queryset = queryset.filter(profile__branch_id=branch_id)

        # Prepare CSV response
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="user_data.csv"'

        writer = csv.writer(response)
        # Write the CSV header
        writer.writerow([
            'Username', 'First Name', 'Last Name', 'Email', 'Gender', 'Contact No', 
            'User Type', 'Company', 'Branch', 'Date Joined', 'Last Login', 'Status'
        ])

        # Write user data
        for user in queryset:
            profile = user.profile  # Access related profile data
            writer.writerow([
                user.username,
                user.first_name,
                user.last_name,
                user.email,
                profile.gender,
                profile.contact_no,
                profile.user_type,
                profile.company.name if profile.company else '',
                profile.branch.name if profile.branch else '',
                user.date_joined,
                user.last_login,
                user.is_active
            ])

        return response

class CustomPasswordResetView(PasswordResetView):
    def post(self, request, *args, **kwargs):
        # Pass request to the serializer explicitly
        serializer = CustomPasswordResetSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(request=request)  # Ensure request is passed
            return Response({'detail': 'Password reset email sent.'}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ResetPasswordAPIView(APIView):
    def post(self, request, uidb64, token):
        try:
            # Decode the uid to get the user ID
            uid = urlsafe_base64_decode(uidb64).decode()
            user = get_user_model().objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return Response({"detail": "Invalid or expired link."}, status=status.HTTP_400_BAD_REQUEST)

        # Validate the reset token
        if not default_token_generator.check_token(user, token):
            return Response({"detail": "Invalid or expired token."}, status=status.HTTP_400_BAD_REQUEST)

        # Proceed to reset the password
        new_password = request.data.get('new_password')
        if new_password:
            user.set_password(new_password)
            user.save()
            return Response({"detail": "Password has been successfully updated."}, status=status.HTTP_200_OK)

        return Response({"detail": "New password not provided."}, status=status.HTTP_400_BAD_REQUEST)



import logging

logger = logging.getLogger(__name__)

class EnquiryViewSet(viewsets.ModelViewSet):
    queryset = Enquiry.objects.all()
    serializer_class = EnquirySerializer

    def get_permissions(self):
        """
        Override to apply different permissions for specific actions.
        """
        if self.action == 'create':  # Allow anyone to create inquiries
            return [AllowAny()]
        elif self.action == 'list':  # Only superadmins can list all inquiries
            return [IsSuperAdmin()]
        elif self.action == 'update':  # Only superadmins can update inquiries
            return [IsSuperAdmin()]
        else:  # Default to authenticated-only for other actions
            return [IsAuthenticatedOrReadOnly()]

    def create(self, request, *args, **kwargs):
        """
        Override create method to handle customer submissions.
        """
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save()  # Save data to the database
            return Response({"message": "Enquiry submitted successfully."}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, **kwargs):
        """
        Override update method to handle admin updates.
        """
        instance = self.get_object()
        partial = kwargs.pop('partial', False)
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        if serializer.is_valid():
            # If status is being updated, set it to True
            if not instance.status:  # If it's False (not updated yet)
                instance.status = True  # Update status to True
                instance.save()
             # Update the status to True when the admin updates it
                
            serializer.save()

            # Notify customer if admin_message is updated
            if 'admin_message' in request.data:
                self._send_admin_notification(instance)

            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    def _send_admin_notification(self, instance):
        """
        Send email to customer when admin_message is updated.
        """
        try:
            subject = "Welcome to Creworder"
            template = "emails/query.html"  # Your HTML email template
            context = {
                'full_name': instance.full_name,
                'resolution_details': instance.admin_message,
                'query_summary': instance.message,
                'query_id': instance.id,
            }
            html_message = render_to_string(template, context)
            recipient_list = [instance.email]
            a = send_email(subject, html_message, recipient_list,"default")
            logger.info(f"Email sent successfully to {instance.email}")
        except Exception as email_error:
            logger.error(f"Error sending email to {instance.email}: {email_error}")



class CompanyUserViewSet(viewsets.ViewSet):
    """
    A viewset to get all users and admins by company_id, including user count
    """
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated, IsSuperAdmin] 
    @action(detail=False, methods=['get'])
    def get_admin_and_user_count(self, request):
        company_id = request.query_params.get('company_id')

        if not company_id:
            return Response({'error': 'company_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            company = Company.objects.get(id=company_id)
        except Company.DoesNotExist:
            return Response({'error': 'Company not found'}, status=status.HTTP_404_NOT_FOUND)

        # Get all users linked to the company (both admins and users)
        company_users = User.objects.filter(profile__company=company)

        # Get user count
        user_count = company_users.count()

        # Get admins only
        admins = company_users.filter(profile__user_type="admin")
        serialized_admins = UserSerializer(admins, many=True)

        # Serialize all company users
        serialized_company_users = UserSerializer(company_users, many=True)

        return Response({
            'company': company.name,
            'user_count': user_count,
            'admins': serialized_admins.data,
            # 'company_users': serialized_company_users.data  # Include all users as well
        })


from django.utils import timezone
from .serializers import MonthlyCompanyStatsSerializer
from django.db.models.functions import ExtractMonth
import calendar
class MonthlyCompanyStatsView(APIView):

    def get(self, request, *args, **kwargs):
        # Get the 'year' parameter from the query parameters, default to current year if not provided
        year = request.query_params.get('year', timezone.now().year)

        # Ensure that the 'year' is a valid integer
        try:
            year = int(year)
        except ValueError:
            return Response({"error": "Invalid year format."}, status=status.HTTP_400_BAD_REQUEST)

        # Query to count the companies grouped by month and filtered by the provided year
        stats = (Company.objects.filter(created_at__year=year)
                 .annotate(month=ExtractMonth('created_at'))  # Extract month from 'created_at' field
                 .values('month')  # Group by month
                 .annotate(total_companies=Count('id'))  # Count the companies per month
                 .order_by('month'))  # Sort by month

        # If no companies are found for the given year, return an empty list
        if not stats:
            return Response([], status=status.HTTP_200_OK)

        # Prepare the serialized data with month names instead of numbers
        stats_data = [
            {
                'month': calendar.month_name[stat['month']][:3],  # Convert month number to abbreviated month name (e.g., 'Jan')
                'year': year,
                'total_companies': stat['total_companies'],
            }
            for stat in stats
        ]

        # Return the data in the response
        return Response(stats_data, status=status.HTTP_200_OK)
    


class AgreementViewSet(viewsets.ModelViewSet):
    queryset = Agreement.objects.all().order_by('-created_at')
    serializer_class = AgreementSerializer
    permission_classes = [IsAuthenticated]
    # pagination_class = StandardResultsSetPagination
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def get_queryset(self):
        return Agreement.objects.all()


    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def latest(self, request):
        latest_agreement = Agreement.objects.filter(created_by=request.user).order_by('-created_at').first()
        if latest_agreement:
            serializer = self.get_serializer(latest_agreement)
            return Response(serializer.data)
        return Response({"message": "No agreements found"}, status=404)

from superadmin_assets.models import SettingsMenu
class GetPackagesModule(viewsets.ModelViewSet):
    queryset = Package.objects.all()
    serializer_class = PackageSerializer
    permission_classes = [IsAuthenticated, DjangoObjectPermissions]

    
    def list(self, request, *args, **kwargs):
        # Get user-related data
        if self.request.user.profile.user_type == "superadmin":
            return Response({"role": "superadmin",
            "sidebardata": ['/dashboard']})
        userData = Employees.objects.filter(user_id=request.user.id).values("branch", "company").first()
        
        # Check if userData is valid
        if not userData:
            return Response({"error": "User data not found"}, status=400)

        company_id = userData.get('company')
        if not company_id:
            return Response({"error": "Company ID not found for the user"}, status=400)

        CompanyData = Company.objects.filter(id=company_id).values("package").first()

        # Check if CompanyData is valid
        if not CompanyData or 'package' not in CompanyData:
            return Response({"error": "Package not found for the company"}, status=400)

        package_id = CompanyData['package']
        
        try:
            package_instance = Package.objects.get(id=package_id)
        except Package.DoesNotExist:
            return Response({"error": "Package not found"}, status=400)

        serializer = self.get_serializer(package_instance)

        # Show data for menus and sub-menus
        showDataDict = {}
        url_dict=["/dashboard"]
        my_set = set()
        my_set.add("/dashboard")
        my_set.add("/profile/companyprofile")
        my_set.add("/profile")
        my_set.add("/signup")
        my_set.add("/admin/search")
        my_set.add("/admin/get-started")
        my_set.add("/admin/get-started/two-step-login")
        my_set.add("/notepad")
        my_set.add("/admin/shipment/manifestlabelpage")
        my_set.add("/admin/shipment/LabelPreviewPage")
        my_set.add("/admin/manage/edit-target")
        my_set.add("/view-profile")
        my_set.add("/admin/manage/editassignrole")
        my_set.add('/admin/performance/agent-order')
        my_set.add('/admin/orders')
        if self.request.user.profile.user_type == "admin" or  self.request.user.has_perm("accounts.chat_user_permission_others"):
            my_set.add("/chat")
        user_type = self.request.user.profile.user_type
        all_menus = SettingsMenu.objects.filter(
            Q(for_user=user_type) | Q(for_user='both'),
            status=1
        )

        # If user is a superadmin, return all menus directly
        # if user_type == 'superadmin':
        #     return all_menus

        # Filter menus based on user permissions
        menu_ids = []
        for menu in all_menus:
            menu_name_key = menu.name.replace(' ', '_').lower()
            menu_permission = f"superadmin_assets.show_settingsmenu_{menu_name_key}"
            
            if self.request.user.has_perm(menu_permission):
                menu_ids.append(menu.id)
                my_set.add(menu.url)
        # Check each menu and submenu permission dynamically
        for data in serializer.data.get('packagedetails', []):
            menu_name = data['menu_name']
            sub_menu_name = data['sub_menu_name']
            sub_menu_url = data['sub_menu_url']
            menu_url = data['menu_url']
            icon = data['menu_icon']
            module_name = data['module_name']  # Added module_name
            menu_namea =menu_name.replace(' ','_').lower()
            # Create a base permission string for each menu/sub-menu
            menu_permission = f"superadmin_assets.show_menumodel_{menu_namea}"
            sub_menu_permission = f"superadmin_assets.show_submenusmodel_{sub_menu_name.replace(' ','_').lower()}" if sub_menu_name else None
            # Check if the user has the necessary permissions
            has_menu_permission = request.user.has_perm(menu_permission)
            has_sub_menu_permission = request.user.has_perm(sub_menu_permission) if sub_menu_permission else True
            if has_menu_permission or request.user.profile.user_type != 'agent':
                if menu_name in showDataDict:
                    if has_sub_menu_permission or request.user.profile.user_type != 'agent':
                        if isinstance(showDataDict[menu_name], list):
                            url_dict.append(sub_menu_url) 
                            my_set.add(sub_menu_url)        
                else:
                    if sub_menu_name is None:
                        my_set.add(menu_url) 
                        url_dict.append(menu_url)
        
                    else:
                        if has_sub_menu_permission or request.user.profile.user_type != 'agent':
                            url_dict.append(sub_menu_url)
                            my_set.add(sub_menu_url) 

        # Include sidebardata in the response
        data['sidebardata'] = my_set
        data["role"] = "admin"
        return Response(data)




class ManagerTeamLeadAgentAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        manager_id = request.query_params.get("manager_id")
        teamlead_id = request.query_params.get("tl_id")
        if self.request.user.profile.user_type == 'superadmin':
            company_id = None
            branch_id = None
        else:
            company_id = self.request.user.profile.company
            branch_id = self.request.user.profile.branch

        # Filter managers based on input
        if manager_id:
            managers = Employees.objects.filter(user_id=manager_id, company_id=company_id, branch_id=branch_id, status=1)
        else:
            # Get all managers if not filtered
            manager_query = Employees.objects.filter(
                company_id=company_id,
                branch_id=branch_id
            ).exclude(manager__isnull=True).values_list('manager', flat=True).distinct()
            managers = Employees.objects.filter(user__id__in=manager_query, company_id=company_id, branch_id=branch_id,status=1)

        result = []

        for manager in managers:
            # Get all team leads under this manager
            teamleads = Employees.objects.filter(
                manager=manager.user,
                company_id=company_id,
                branch_id=branch_id,
                teamlead_id=None,status=1
            )

            teamlead_list = []
            for tl in teamleads:
                agents = Employees.objects.filter(
                    teamlead=tl.user,
                    company_id=company_id,
                    branch_id=branch_id,status=1
                )

                agent_list = [
                    {
                        "agent_id": agent.user.id,
                        "agent_name": agent.user.get_full_name() or agent.user.username,
                        "username": agent.user.username
                    }
                    for agent in agents
                ]
                if teamlead_id: 
                    if str(teamlead_id)==str(tl.user.id):
                        teamlead_list.append({
                        "tl_id": tl.user.id,
                        "tl_name": tl.user.get_full_name() or tl.user.username,
                        "agent_under_teamlead": agent_list,
                        "username":tl.user.username
                    })
                else:
                    teamlead_list.append({
                        "tl_id": tl.user.id,
                        "tl_name": tl.user.get_full_name() or tl.user.username,
                        "agent_under_teamlead": agent_list,
                        "username":tl.user.username
                    })

            result.append({
                "manager_id": manager.user.id,
                "manager_name": manager.user.get_full_name() or manager.user.username,
                "teamlead_under_manager": teamlead_list,
                "username":manager.user.username
                
            })

        return Response(
            {"Success": True, "Data": result},
            status=status.HTTP_200_OK
        )


class UserPermissionStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, format=None):
        user = request.user

        # If user is of type 'admin', grant all permissions
        if user.profile.user_type == 'admin':
            response_data = {
                "order_status_button": True,
                "order_payment_status_button": True,
                "order_edit_button": True,
                "team_data":True,
                "search_data":True,
                "click-to-call":True,
                "force_attendance" : user.has_perm('accounts.force_attendance_others'),
            }
        else:
            # Fallback to permission-based checks
            response_data = {
                "order_status_button": user.has_perm('accounts.edit_order_status_others'),
                "order_payment_status_button": user.has_perm('accounts.edit_order_payment_status_others'),
                "order_edit_button": user.has_perm('accounts.edit_order_others'),
                "force_attendance" : user.has_perm('accounts.force_attendance_others'),
                "team_data" : sum(user.has_perm(p) for p in ['dashboard.view_manager_dashboard_team_order_list', 'dashboard.view_all_dashboard_team_order_list', 'dashboard.view_own_team_dashboard_team_order_list']) >= 1,
                "search_data":user.has_perm('accounts.view_search_bar_others'),
                "click-to-call":CloudTelephonyChannelAssign.objects.filter(user=user).exists()
            }

        return Response(response_data)


class QcScoreViewSet(viewsets.ModelViewSet):
    queryset = QcScore.objects.all()
    serializer_class = QcScoreSerializer
    permission_classes = [IsAuthenticated]

    def list(self, request, *args, **kwargs):
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")
        user_id = request.query_params.get("user_id")

        today = now().date()
        if not start_date or not end_date:
            start_date = today.replace(day=1)
            end_date = today
        else:
            start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
            end_date = datetime.strptime(end_date, "%Y-%m-%d").date()

        queryset = []

        try:
            if user_id:
                user = get_object_or_404(User, id=user_id)
                queryset = [user]  # Use list to keep consistent with loop
            else:
                user = self.request.user
                if user.profile.user_type == "superadmin":
                    company_id = self.request.query_params.get("company_id")
                    if company_id:
                        queryset = User.objects.filter(profile__company_id=company_id)
                    else:
                        queryset = User.objects.filter(profile__company=None)

                elif user.profile.user_type == "admin":
                    company = user.profile.company
                    queryset = User.objects.filter(profile__company=company)

                elif user.profile.user_type == "agent":
                    branch = user.profile.branch
                    queryset = User.objects.filter(profile__branch=branch)

        except Exception as e:
            print(f"Error in get_queryset: {e}")

        response_data = []

        for emp in queryset:
            scores = QcScore.objects.filter(user=emp)

            # Apply filtering for date range on created_at or updated_at
            scores = scores.filter(
                Q(created_at__range=(start_date, end_date)) | Q(updated_at__range=(start_date, end_date))
            )

            avg_scores = scores.values('question__id', 'question__question').annotate(avg_rating=Avg('score'))

            questions_rating = [
                {
                    "question_id": item['question__id'],
                    "question": item['question__question'],
                    "question_rating": round(item['avg_rating'], 2)
                } for item in avg_scores
            ]

            response_data.append({
                "employee_name": emp.get_full_name() or emp.username,
                "employee_id": emp.id,
                "questions_rating": questions_rating
            })

        return Response(response_data)

    def create(self, request, *args, **kwargs):
        user_id = request.data.get('user')
        ratings = request.data.get('rating', [])

        if not user_id or not ratings:
            return Response({'error': 'User and rating are required.'}, status=status.HTTP_400_BAD_REQUEST)

        user = get_object_or_404(User, id=user_id)
        created_scores = []

        for entry in ratings:
            question_id = entry.get('id')
            score = entry.get('rating')
            if not question_id or score is None:
                continue

            question = get_object_or_404(QcTable, id=question_id)

            qc_score, created = QcScore.objects.update_or_create(
                user=user,
                question=question,
                defaults={
                    'score': score,
                    'scored_at': now()  # This will set the scored_at field, and updated_at will be automatically updated
                }
            )
            created_scores.append({
                'user': user.id,
                'question_id': question.id,
                'score': qc_score.score,
                'created': created
            })

        return Response({'created_scores': created_scores}, status=status.HTTP_201_CREATED)





class UserTargetsDelailsFilterAPIView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Extract query parameters
        user = request.GET.get('user')
        daily_amount_target = request.GET.get('daily_amount_target')
        daily_orders_target = request.GET.get('daily_orders_target')
        monthly_amount_target = request.GET.get('monthly_amount_target')
        monthly_orders_target = request.GET.get('monthly_orders_target')
        achieve_target = request.GET.get('achieve_target')

        # Build filter Q object
        filters = Q()
        if user:
            filters &= Q(user=user)
        if daily_amount_target:
            filters &= Q(daily_amount_target=daily_amount_target)
        if daily_orders_target:
            filters &= Q(daily_orders_target=daily_orders_target)
        if monthly_amount_target:
            filters &= Q(monthly_amount_target=monthly_amount_target)
        if monthly_orders_target:
            filters &= Q(monthly_orders_target=monthly_orders_target)
        if achieve_target is not None:
            if achieve_target.lower() in ['true', '1']:
                filters &= Q(achieve_target=True)
            elif achieve_target.lower() in ['false', '0']:
                filters &= Q(achieve_target=False)

        # Query the database
        queryset = UserTargetsDelails.objects.filter(filters)
        serializer = UserTargetsDelailsSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
from rest_framework.generics import ListAPIView
class UsersWithTargetsAPIView(ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserSerializer


    def get_queryset(self):
        user = self.request.user
        profile = user.profile

        target_subquery = UserTargetsDelails.objects.filter(
            user=OuterRef('pk'),
            in_use=True
        )

        if profile.user_type == "agent":
            return User.objects.annotate(
                has_targets=Exists(target_subquery)
            ).filter(
                profile__branch=profile.branch,
                profile__company=profile.company,
                has_targets=True,
                profile__status=1
            )

        elif profile.user_type == "admin":
            return User.objects.annotate(
                has_targets=Exists(target_subquery)
            ).filter(
                profile__company=profile.company,
                has_targets=True,
                profile__status=1
            )

        return User.objects.none()



class UsersTeamAPIView(ListAPIView):
    serializer_class = UserSerializer  # your serializer for the User model

    def get_queryset(self):
        user = self.request.user
        profile = user.profile
        company = profile.company

        if profile.user_type == "admin":
            target_subquery = UserTargetsDelails.objects.filter(
            user=OuterRef('pk'),
            in_use=True
        )
            return User.objects.annotate(
                has_targets=Exists(target_subquery)
            ).filter(
                profile__company=profile.company,
                has_targets=True
            )

        employee_qs = Employees.objects.filter(manager_id=user.id,status=1)
        if not employee_qs.exists():
            employee_qs = Employees.objects.filter(teamlead_id=user.id,status=1)
            if not employee_qs.exists():
                employee_qs = Employees.objects.filter(user_id=user.id,status=1)

        user_ids = employee_qs.values_list('user_id', flat=True)
        return User.objects.filter(id__in=user_ids)
    






class CompanyUserAPIKeyViewSet(viewsets.ModelViewSet):
    queryset = CompanyUserAPIKey.objects.all()
    serializer_class = CompanyUserAPIKeySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        
        # if user is superadmin → return all
        if hasattr(user, "profile") and getattr(user.profile, "user_type", "").lower() == "superadmin":
            return CompanyUserAPIKey.objects.all()
        
        # else filter by company
        if hasattr(user, "profile") and user.profile.company:
            return CompanyUserAPIKey.objects.filter(company=user.profile.company)
        
        # fallback empty queryset
        return CompanyUserAPIKey.objects.none()
    
    def perform_create(self, serializer):
        # Get the current user's company
        company = self.request.user.profile.company
        
        serializer.save(company=company)




class DeleteUserListView(ListAPIView):
    """API to list users based on role-based filtering"""
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        queryset = User.objects.none()  # Default empty queryset

        try:
            if hasattr(user, 'profile'):  # Ensure user has a profile
                if user.profile.user_type == "superadmin":
                    company_id = self.request.query_params.get("company_id")
                    if company_id:
                        queryset = User.objects.filter(profile__company_id=company_id).exclude(profile__status=1)
                    else:
                        queryset = User.objects.filter(profile__company=None).exclude(profile__status=1)

                elif user.profile.user_type == "admin":
                    company = user.profile.company
                    queryset = User.objects.filter(profile__company=company).exclude(profile__status=1)

                elif user.profile.user_type == "agent":
                    branch = user.profile.branch
                    queryset = User.objects.filter(profile__branch=branch).exclude(profile__status=1)

        except Exception as e:
            print(f"Error in get_queryset: {e}")

        return queryset

    def list(self, request, *args, **kwargs):
        """Custom response handling"""
        queryset = self.get_queryset()  # Exclude the requesting user
        serializer = self.get_serializer(queryset, many=True)
        data = serializer.data

        user_ids = [user['id'] for user in data]
        tokens = Token.objects.filter(user_id__in=user_ids).values_list('user_id', flat=True)

        for user in data:
            user['online'] = user['id'] in tokens  # Add online status

        return Response({"status": "success", "results": data}, status=status.HTTP_200_OK)


class CompanyMonthlySummaryView(APIView):
    """
    Returns the number of active companies created in a given or current month/year.
    """

    def get(self, request):
        try:
            # Use current month and year if not provided
            now = datetime.now()
            month = int(request.query_params.get('month', now.month))
            year = int(request.query_params.get('year', now.year))

            if not (1 <= month <= 12):
                return Response({"error": "Invalid month value."}, status=status.HTTP_400_BAD_REQUEST)

            count = Company.objects.filter(
                status=True,
                created_at__year=year,
                created_at__month=month
            ).count()

            return Response({
                "year": year,
                "month": datetime(year, month, 1).strftime("%B"),
                "active_companies": count
            })

        except (TypeError, ValueError):
            return Response({"error": "Month and year must be valid integers."}, status=status.HTTP_400_BAD_REQUEST)
        



class UsersNdrAPIView(ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserSerializer

    def get_queryset(self):
        user = self.request.user
        profile = user.profile

        # Subquery to check if the user has active targets
        target_subquery = UserTargetsDelails.objects.filter(
            user=OuterRef('pk'),
            in_use=True
        )

        # Get the permission object for 'edit_order_others'
        try:
            edit_permission = Permission.objects.get(codename='edit_order_others')
        except Permission.DoesNotExist:
            return User.objects.none()  # No such permission defined

        # Users who have 'edit_order_others' either directly or via groups
        users_with_permission = User.objects.filter(
            Q(user_permissions=edit_permission) | Q(groups__permissions=edit_permission)
        ).distinct()

        # Start with users who have active targets and proper status
        base_queryset = User.objects.annotate(
            has_targets=Exists(target_subquery)
        ).filter(
            has_targets=True,
            profile__status=1,
            id__in=users_with_permission
        ).select_related('profile')

        if profile.user_type == "agent":
            return base_queryset.filter(
                profile__branch=profile.branch,
                profile__company=profile.company
            )

        elif profile.user_type == "admin":
            return base_queryset.filter(
                profile__company=profile.company
            )

        return User.objects.none()
    

class ReminderNotesViewSet(viewsets.ModelViewSet):
    queryset = ReminderNotes.objects.all()
    serializer_class = ReminderNotesSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = OrderPagination

    def get_queryset(self):
        user = self.request.user
        return ReminderNotes.objects.filter(created_by=user)

    def perform_create(self, serializer):
        user = self.request.user
        serializer.save(company=user.profile.company, branch=user.profile.branch)




class AgentAttendanceUserWiseAPIView(ListAPIView):
    """
    User-wise attendance summary (present/absent counts)
    with branch & company info + pagination.
    Defaults to current month if no start_date & end_date given.
    """
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        company_id = self.request.user.profile.company
        branch_id = self.request.user.profile.branch
        start_date = self.request.query_params.get("start_date")
        end_date = self.request.query_params.get("start_date")

        qs = Attendance.objects.filter(user__profile__user_type="agent")

        if branch_id:
            qs = qs.filter(branch_id=branch_id)
        if company_id:
            qs = qs.filter(company_id=company_id)

        # ✅ If no dates given → use current month
        if not (start_date and end_date):
            today = date.today()
            start_date = today.replace(day=1)
            # last_day = calendar.monthrange(today.year, today.month)[1]
            end_date = today
        else:
            try:
                start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
                end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
            except ValueError:
                return Attendance.objects.none()
        
        qs = qs.filter(date__range=[start_date, end_date])
        total_employees_company = Employees.objects.filter(
            company=company_id,
            branch=branch_id,
            status=UserStatus.active,
            user_type="agent"
        ).count()
        # total_employees_company = Employees.objects.filter(company=company_id,branch=branch_id).count()
        # qs = {"qs":qs,"total_count":total_employees_company}
        # Group by user with counts + branch + company
        user_summary = (
            qs.values(
                "user__id",
                "user__username",
                "branch__id",
                "branch__name",
                "company__id",
                "company__name",
            )
            .annotate(
                present_count=Count("id", filter=Q(attendance="P")),
                absent_count=Count("id", filter=Q(attendance="A")),
            )
            .order_by("user__username")
        )

        return qs, user_summary,total_employees_company

    def list(self, request, *args, **kwargs):
        qs, user_summary, total_employees_company= self.get_queryset()
        # qs = qs.get("qs")
        # total_employees_company = qs.get("total_count")
        # ✅ Paginate user summary
        page = self.paginate_queryset(user_summary)
        if page is not None:
            user_data = self.get_paginated_response(page).data
        else:
            user_data = user_summary

        # ✅ Overall totals (all users, all days)
        total_present = qs.filter(attendance="P").count()
        total_absent = qs.filter(attendance="A").count()

        # ✅ Date-wise totals
        date_wise_summary = (
            qs.values("date")
            .annotate(
                present_count=Count("id", filter=Q(attendance="P")),
                absent_count=Count("id", filter=Q(attendance="A")),
            )
            .order_by("date")
        )

        return Response({
            "user_summary": user_data,
            "overall_totals": {
                "total_present": total_present,
                "total_absent": total_employees_company-int(total_present),
            },
            "date_wise_totals": date_wise_summary,
        })
