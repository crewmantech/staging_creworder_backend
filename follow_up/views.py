import csv
from django.http import HttpResponse
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import viewsets,status

from accounts.models import Employees
from accounts.permissions import HasPermission
from cloud_telephony.models import CloudTelephonyChannelAssign
from lead_management.models import Lead
from services.cloud_telephoney.cloud_telephoney_service import CloudConnectService, SansSoftwareService
from .models import Follow_Up
from .serializers import FollowUpSerializer,NotepadSerializer
from django.db import transaction
from services.follow_up.notepad_service import createOrUpdateNotepad,getNotepadByAuthid
from rest_framework.permissions import IsAuthenticated
from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError
from django.db import transaction
from django.utils.datastructures import MultiValueDict
from django.utils.dateparse import parse_date
import pdb
from django.db.models import Q
class FollowUpView(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = Follow_Up.objects.all()
    serializer_class = FollowUpSerializer
    def resolve_phone_number(self,call_id, phone_number, user):
        """
        Resolves the phone number from Lead or using external API.
        """
        if phone_number and "*" not in phone_number:
            return phone_number  # Already clean

        # -------- Try finding number in Lead Model --------
        try:
            lead = Lead.objects.get(lead_id=call_id)
            if lead.customer_phone:
                return lead.customer_phone
        except Lead.DoesNotExist:
            pass

        # -------- Try external API: GetNumberAPIView logic --------
        try:
            channel_assign = CloudTelephonyChannelAssign.objects.get(user_id=user.id)
            channel = channel_assign.cloud_telephony_channel
        except CloudTelephonyChannelAssign.DoesNotExist:
            return None

        vendor = channel.cloudtelephony_vendor.name.lower()
        tenent = channel.tenent_id
        token = channel.token

        # Cloud Connect
        if vendor == "cloud connect":
            # from telephony.cloud_connect import CloudConnectService
            service = CloudConnectService(token, tenent)
            resp = service.call_details(call_id)
            # if resp.get("code") == 200:
            print(resp,"==========62")
            return resp.get("result", {}).get("phone_number")

        # Sanssoftware
        elif vendor == "sanssoftwares":
            # from telephony.sans_service import SansSoftwareService
            service = SansSoftwareService(process_id=tenent)
            resp = service.get_number(call_id)
            print(resp, "--------------69")

            # Correct structure handling
            result = resp.get("result", [])
            if isinstance(result, list) and len(result) > 0:
                return result[0].get("Phone_number")

        return None

    def get_permissions(self):
        permission_map = {
            'create': ['superadmin_assets.show_submenusmodel_follow_up', 'superadmin_assets.add_submenusmodel'],
            'update': ['superadmin_assets.show_submenusmodel_follow_up', 'superadmin_assets.change_submenusmodel'],
            'destroy': ['superadmin_assets.show_submenusmodel_follow_up', 'superadmin_assets.delete_submenusmodel'],
            'retrieve': ['superadmin_assets.show_submenusmodel_follow_up', 'superadmin_assets.view_submenusmodel'],
            'list': ['superadmin_assets.show_submenusmodel_follow_up', 'superadmin_assets.view_submenusmodel']
        }
        
        action = self.action
        if action in permission_map:
            permissions = permission_map[action]
            return [HasPermission(perm) for perm in permissions]  # Return a list of permission checks
    
        return super().get_permissions() # Return a list of permission checks
    def get_queryset(self):
        """
        Retrieve follow-ups based on user role and assigned permissions.
        """
        user = self.request.user
        queryset = Follow_Up.objects.all()

        if hasattr(user, 'profile') and user.profile.company:
            queryset = queryset.filter(company=user.profile.company)
        if user.profile.user_type == 'admin':
            status_id = self.request.query_params.get('status')
            branch_id = self.request.query_params.get('branch')
            follow_add_by = self.request.query_params.get('follow_add_by')

            if status_id:
                queryset = queryset.filter(follow_status_id=status_id)

            if branch_id:
                queryset = queryset.filter(branch_id=branch_id)

            if follow_add_by:
                queryset = queryset.filter(follow_add_by_id=follow_add_by)
            search = self.request.query_params.get('search')

            if search:
                queryset = queryset.filter(
                    Q(follow_status__name__icontains=search) |
                    Q(follow_add_by__first_name__icontains=search) |
                    Q(follow_add_by__last_name__icontains=search) |
                    Q(follow_add_by__username__icontains=search) |
                    Q(customer_phone__icontains=search)
                )
            return queryset
        else:
            queryset=queryset.filter(branch= user.profile.branch)
        if hasattr(user, 'profile') and user.profile.user_type == 'agent':
            if user.has_perm("accounts.view_own_followup_others"):
                queryset = queryset.filter(follow_add_by=user)

            elif user.has_perm("accounts.view_teamlead_followup_others"):
                team_lead_users = Employees.objects.filter(teamlead=user).values_list('user', flat=True)
                queryset = queryset.filter(follow_add_by__in=team_lead_users)

            elif user.has_perm("accounts.view_manager_followup_others"):
                team_leads = Employees.objects.filter(manager=user).values_list('user', flat=True)
                team_lead_users = Employees.objects.filter(teamlead__in=team_leads).values_list('user', flat=True)
                all_users = list(team_leads) + list(team_lead_users)
                queryset = queryset.filter(follow_add_by__in=all_users)

            elif user.has_perm("accounts.view_all_followup_others"):
                pass  # View all allowed, no additional filtering.

        else:
            queryset = Follow_Up.objects.none()  # No permission, return empty.
        return queryset
    # def get_permissions(self):
    #     if self.action == 'create':
    #         return [HasPermission('add_followup')]
    #     elif self.action == 'update':
    #         return [HasPermission('change_follow_up')]
    #     elif self.action == 'destroy':
    #         return [HasPermission('delete_follow_up')]
    #     elif self.action == 'retrieve':  # For getting a specific email address
    #         return [HasPermission('view_follow_up')]
    #     elif self.action == 'list':  # For listing all email addresses
    #         return [HasPermission('view_follow_up')]
    #     return super().get_permissions()
    @transaction.atomic
    def create(self, request, *args, **kwargs):
        user = request.user
        data = request.data.copy()

        # Auto-assign company/branch if missing
        data.setdefault('branch', user.profile.branch.id)
        data.setdefault('company', user.profile.company.id)

        # Resolve phone number
        call_id = data.get("call_id")
        customer_phone = data.get("customer_phone")

        if call_id and (not customer_phone or "*" in customer_phone):
            resolved_number = self.resolve_phone_number(call_id, customer_phone, user)
            print(resolved_number,"-------------172")
            if resolved_number:
                data["customer_phone"] = resolved_number

        request._full_data = data
        return super().create(request, *args, **kwargs)
    
    @transaction.atomic
    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        user = request.user
        data = request.data.copy()

        data.setdefault('branch', user.profile.branch.id)
        data.setdefault('company', user.profile.company.id)

        # Resolve phone number
        call_id = data.get("call_id") or instance.call_id
        customer_phone = data.get("customer_phone") or instance.customer_phone

        if call_id and (not customer_phone or "*" in customer_phone):
            resolved_number = resolve_phone_number(call_id, customer_phone, user)
            if resolved_number:
                data["customer_phone"] = resolved_number

        serializer = self.get_serializer(instance, data=data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data)


class NotepadCreateOrUpdate(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        auth_id = request.data.get('authID')
        note = request.data.get('note')

        if not auth_id or not note:
            return Response(
                {"Success": False, "Error": "authID and note are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        notepad, updated = createOrUpdateNotepad(auth_id, note)

        if updated:
            return Response(
                {"Success": True, "Message": "Notepad updated successfully.", "Notepad": NotepadSerializer(notepad).data},
                status=status.HTTP_200_OK,
            )
        else:
            return Response(
                {"Success": True, "Message": "Notepad created successfully.", "Notepad": NotepadSerializer(notepad).data},
                status=status.HTTP_201_CREATED,
            )
        
class NotepadDetail(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, auth_id):
        notepad = getNotepadByAuthid(auth_id)
        
        if notepad:
            return Response(
                {"Success": True, "Notepad": NotepadSerializer(notepad).data},
                status=status.HTTP_200_OK,
            )
        else:
            return Response(
                {"Success": False, "Error": "No notepad entry found for the given authID."},
                status=status.HTTP_404_NOT_FOUND,
            )
        

class FollowUpExportAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def export_followups(self, request):
        """
        Export follow-ups as CSV with Date Range and Follow-Up Status filters.
        """
        try:
            # Get the user's follow-ups
            followups = Follow_Up.objects.all()

            # Apply date range filter if present
            start_date = request.query_params.get('start_date', None)
            end_date = request.query_params.get('end_date', None)

            if start_date:
                start_date = parse_date(start_date)
                followups = followups.filter(reminder_date__gte=start_date)

            if end_date:
                end_date = parse_date(end_date)
                followups = followups.filter(reminder_date__lte=end_date)

            # Apply follow-up status filter if present
            status1 = request.query_params.get('follow_status', None)
            if status1:
                followups = followups.filter(follow_status=status1)
            # Serialize the data
            followup_data = FollowUpSerializer(followups, many=True).data

            

            return Response( {"Success": True, "data": followup_data ,"message":"follow Export succesfully" },
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            return Response(
                {"Success": False, "Error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def get(self, request):
        """
        Export follow-ups as CSV if the export query parameter is set to "true".
        """
        if request.query_params.get("export") == "true":
            return self.export_followups(request)
        else:
            return Response(
                {"Success": False, "Error": "Invalid request for export."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        

class GetPhoneByReferenceAPIView(APIView):
    """
    GET phone number using a single reference_id
    reference_id can be Lead.lead_id OR Follow_Up.followup_id
    """

    def get(self, request):
        reference_id = request.query_params.get("reference_id")

        if not reference_id:
            return Response(
                {"error": "reference_id query param is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # ✅ Try Lead
        lead = Lead.objects.filter(
            lead_id=reference_id
        ).only("customer_phone").first()

        if lead:
            return Response(
                {
                    "type": "lead",
                    "reference_id": reference_id,
                    "customer_phone": lead.customer_phone
                },
                status=status.HTTP_200_OK
            )

        # ✅ Try Follow Up
        followup = Follow_Up.objects.filter(
            followup_id=reference_id
        ).only("customer_phone").first()

        if followup:
            return Response(
                {
                    "type": "followup",
                    "reference_id": reference_id,
                    "customer_phone": followup.customer_phone
                },
                status=status.HTTP_200_OK
            )

        return Response(
            {"error": "No Lead or Follow-up found for this reference_id"},
            status=status.HTTP_404_NOT_FOUND
        )