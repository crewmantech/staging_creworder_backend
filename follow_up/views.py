import csv
from django.http import HttpResponse
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import viewsets,status
from rest_framework.decorators import action
from accounts.models import Employees
from accounts.permissions import HasPermission

from cloud_telephony.models import CloudTelephonyChannelAssign
from follow_up.permissions import AppointmentStatusPermission
from follow_up.utils import get_phone_by_reference_id
from lead_management.models import Lead
from orders.views import FilterOrdersPagination
from services.cloud_telephoney.cloud_telephoney_service import CloudConnectService, SansSoftwareService
from .models import Appointment, Appointment_layout, AppointmentStatus, Follow_Up
from .serializers import AppointmentLayoutSerializer, AppointmentSerializer, AppointmentStatusSerializer, BulkFollowupAssignSerializer, FollowUpSerializer,NotepadSerializer
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
from django.shortcuts import get_object_or_404
from .models import User
class FollowUpView(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = Follow_Up.objects.all()
    serializer_class = FollowUpSerializer

    # =====================================================
    # 🔐 PHONE MASKING (RESPONSE ONLY)
    # =====================================================
    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get("request")

        if (
            request
            and request.user.has_perm("accounts.view_number_masking_others")
            and data.get("customer_phone")
        ):
            phone = data["customer_phone"]
            if len(phone) >= 10:
                data["customer_phone"] = phone[:2] + "******" + phone[-2:]

        return data

    # =====================================================
    # 📞 PHONE RESOLUTION (SAFE)
    # =====================================================
    def resolve_phone_number(self, call_id, phone_number, user):
        """
        Priority:
        1. Direct unmasked phone
        2. Lead table
        3. Cloud Telephony API
        """

        # ✅ 1. Direct clean phone
        if phone_number and "*" not in phone_number:
            return phone_number

        # ✅ 2. Lead lookup (SAFE .first())
        lead = (
            Lead.objects
            .filter(Q(lead_id=call_id) | Q(id=call_id))
            .only("customer_phone")
            .first()
        )

        if lead and lead.customer_phone:
            return lead.customer_phone

        # ✅ 3. Cloud telephony lookup
        try:
            channel_assign = CloudTelephonyChannelAssign.objects.get(user_id=user.id)
            channel = channel_assign.cloud_telephony_channel
        except CloudTelephonyChannelAssign.DoesNotExist:
            return None

        vendor = channel.cloudtelephony_vendor.name.lower()
        tenant = channel.tenent_id
        token = channel.token

        # 🔹 Cloud Connect
        if vendor == "cloud connect":
            service = CloudConnectService(token, tenant)
            resp = service.call_details(call_id)
            return resp.get("result", {}).get("phone_number")

        # 🔹 SansSoftwares
        if vendor == "sansoftwares":
            service = SansSoftwareService(process_id=tenant)
            resp = service.get_number(call_id)
            result = resp.get("result", [])

            if isinstance(result, list) and result:
                return result[0].get("Phone_number")

        return None

    # =====================================================
    # 🔐 PERMISSIONS
    # =====================================================
    def get_permissions(self):
        permission_map = {
            'create': ['superadmin_assets.show_submenusmodel_follow_up', 'superadmin_assets.add_submenusmodel'],
            'update': ['superadmin_assets.show_submenusmodel_follow_up', 'superadmin_assets.change_submenusmodel'],
            'destroy': ['superadmin_assets.show_submenusmodel_follow_up', 'superadmin_assets.delete_submenusmodel'],
            'retrieve': ['superadmin_assets.show_submenusmodel_follow_up', 'superadmin_assets.view_submenusmodel'],
            'list': ['superadmin_assets.show_submenusmodel_follow_up', 'superadmin_assets.view_submenusmodel'],
        }

        if self.action in permission_map:
            return [HasPermission(p) for p in permission_map[self.action]]

        return super().get_permissions()

    # =====================================================
    # 📂 QUERYSET RULES
    # =====================================================
    def get_queryset(self):
        user = self.request.user
        queryset = Follow_Up.objects.all()

        # Company isolation
        if hasattr(user, "profile") and user.profile.company:
            queryset = queryset.filter(company=user.profile.company)

        # Admin filters
        if hasattr(user, "profile") and user.profile.user_type == "admin":
            params = self.request.query_params

            if params.get("status"):
                queryset = queryset.filter(follow_status_id=params["status"])

            if params.get("branch"):
                queryset = queryset.filter(branch_id=params["branch"])

            if params.get("follow_add_by"):
                queryset = queryset.filter(
                    Q(follow_add_by_id=params["follow_add_by"]) |
                    Q(assign_user_id=params["follow_add_by"])
                )

            if params.get("search"):
                search = params["search"]
                queryset = queryset.filter(
                    Q(follow_status__name__icontains=search) |
                    Q(follow_add_by__first_name__icontains=search) |
                    Q(follow_add_by__last_name__icontains=search) |
                    Q(follow_add_by__username__icontains=search) |
                    Q(assign_user__username__icontains=search) |
                    Q(customer_phone__icontains=search)
                )

            return queryset.order_by("-created_at")

        # Branch restriction
        if hasattr(user, "profile") and user.profile.branch:
            queryset = queryset.filter(branch=user.profile.branch)

        # Agent visibility
        if hasattr(user, "profile") and user.profile.user_type == "agent":

            if user.has_perm("accounts.view_own_followup_others"):
                queryset = queryset.filter(
                    Q(follow_add_by=user) | Q(assign_user=user)
                )

            elif user.has_perm("accounts.view_teamlead_followup_others"):
                team_users = Employees.objects.filter(
                    teamlead=user
                ).values_list("user", flat=True)

                queryset = queryset.filter(
                    Q(follow_add_by__in=team_users) |
                    Q(assign_user__in=team_users)
                )

            elif user.has_perm("accounts.view_manager_followup_others"):
                team_leads = Employees.objects.filter(
                    manager=user
                ).values_list("user", flat=True)

                team_users = Employees.objects.filter(
                    teamlead__in=team_leads
                ).values_list("user", flat=True)

                queryset = queryset.filter(
                    Q(follow_add_by__in=team_leads) |
                    Q(follow_add_by__in=team_users)
                )

            elif user.has_perm("accounts.view_all_followup_others"):
                pass
            else:
                queryset = Follow_Up.objects.none()

        return queryset.order_by("-created_at")

    # =====================================================
    # ➕ CREATE
    # =====================================================
    @transaction.atomic
    def create(self, request, *args, **kwargs):
        user = request.user
        data = request.data.copy()

        data.setdefault("branch", user.profile.branch.id)
        data.setdefault("company", user.profile.company.id)

        call_id = data.get("call_id")
        incoming_phone = data.get("customer_phone")

        # ❌ ignore masked phone
        if incoming_phone and "*" in incoming_phone:
            incoming_phone = None
            data.pop("customer_phone", None)

        resolved_phone = self.resolve_phone_number(
            call_id=call_id,
            phone_number=incoming_phone,
            user=user
        )

        if not resolved_phone:
            return Response(
                {"customer_phone": ["Unable to resolve phone number"]},
                status=status.HTTP_400_BAD_REQUEST
            )

        data["customer_phone"] = resolved_phone

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save(follow_add_by=user)

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    # =====================================================
    # ✏️ UPDATE
    # =====================================================
    @transaction.atomic
    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        user = request.user
        data = request.data.copy()

        incoming_phone = data.get("customer_phone")

        if incoming_phone and "*" in incoming_phone:
            data.pop("customer_phone", None)

        call_id = data.get("call_id") or instance.call_id

        if "customer_phone" not in data:
            resolved = self.resolve_phone_number(
                call_id=call_id,
                phone_number=instance.customer_phone,
                user=user
            )
            if resolved:
                data["customer_phone"] = resolved

        serializer = self.get_serializer(instance, data=data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data)

    # =====================================================
    # 🔄 BULK ASSIGN
    # =====================================================
    @action(detail=False, methods=["post"], url_path="bulk-assign")
    @transaction.atomic
    def bulk_assign(self, request):
        serializer = BulkFollowupAssignSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user_ids = serializer.validated_data["user_ids"]
        followup_ids = serializer.validated_data["followup_ids"]

        users = list(User.objects.filter(id__in=user_ids))
        followups = list(Follow_Up.objects.filter(followup_id__in=followup_ids))

        if not users or not followups:
            return Response(
                {"error": "Invalid users or followups"},
                status=status.HTTP_400_BAD_REQUEST
            )

        assigned = []
        for i, followup in enumerate(followups):
            user = users[i % len(users)]
            followup.assign_user = user
            followup.save(update_fields=["assign_user"])
            assigned.append({
                "followup_id": followup.followup_id,
                "assigned_to": user.id
            })

        return Response(
            {
                "message": "Followups assigned successfully",
                "total_assigned": len(assigned),
                "assignments": assigned
            },
            status=status.HTTP_200_OK
        )
    
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
    serializer_class = FollowUpSerializer
    queryset = Follow_Up.objects.all()
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
        lead = (Lead.objects.filter(Q(lead_id=reference_id) | Q(id=reference_id)).only("customer_phone").first()         )

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
    




class AppointmentViewSet(viewsets.ModelViewSet):
    serializer_class = AppointmentSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = FilterOrdersPagination 
    queryset = Appointment.objects.select_related(
        "doctor", "branch", "company", "created_by"
    )
    def apply_appointment_filters(self, queryset):
        params = self.request.query_params

        # 🔍 Global search
        search = params.get("search")

        doctor = params.get("doctor")
        branch = params.get("branch")
        status = params.get("status")
        appointment_type = params.get("appointment_type")
        uhid = params.get("uhid")
        phone = params.get("phone")
        patient_name = params.get("patient_name")
        appointment_date = params.get("appointment_date")
        date_from = params.get("start_date")
        date_to = params.get("end_date")
        created_by = params.get("created_by")
        reference_id = params.get("reference_id")
        appointment_status = params.get("appointment_status")  # ✅ NEW
        # =====================================================
        # 🔍 Global Search (single keyword)
        # =====================================================
        if search:
            queryset = queryset.filter(
                Q(id=search) |
                Q(uhid=search) |
                Q(reference_id=search) |
                Q(patient_name__icontains=search) |
                Q(patient_phone=search) |
                Q(doctor__user__first_name__icontains=search) |
                Q(doctor__user__last_name__icontains=search) |
                Q(doctor__registration_number__icontains=search)|
                Q(appointment_status__name__icontains=search)
            )

        # =====================================================
        # 🎯 Specific Filters
        # =====================================================
        if appointment_status:
            queryset = queryset.filter(
                Q(appointment_status_id=appointment_status) |
                Q(appointment_status__name__iexact=appointment_status)
            )   
        if doctor:
            queryset = queryset.filter(doctor_id=doctor)

        if branch:
            queryset = queryset.filter(branch_id=branch)

        if status:
            queryset = queryset.filter(status=status)

        if appointment_type:
            queryset = queryset.filter(appointment_type=appointment_type)

        if uhid:
            queryset = queryset.filter(uhid__icontains=uhid)

        if phone:
            queryset = queryset.filter(patient_phone__icontains=phone)

        if patient_name:
            queryset = queryset.filter(patient_name__icontains=patient_name)

        if appointment_date:
            queryset = queryset.filter(appointment_date=appointment_date)

        if date_from and date_to:
            queryset = queryset.filter(
                appointment_date__range=[date_from, date_to]
            )

        if created_by:
            queryset = queryset.filter(created_by_id=created_by)

        if reference_id:
            queryset = queryset.filter(reference_id__icontains=reference_id)

        return queryset


    @action(detail=True, methods=["get"], url_path="customer-phone")
    def customer_phone(self, request, pk=None):
        """
        Fetch patient phone number using appointment ID
        """
        try:
            appointment = Appointment.objects.get(pk=pk)
        except Appointment.DoesNotExist:
            return Response(
                {"error": "Appointment not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        return Response(
            {
                "appointment_id": appointment.id,
                "patient_phone": str(appointment.patient_phone) if appointment.patient_phone else None
            },
            status=status.HTTP_200_OK
        )

    def get_queryset(self):
        user = self.request.user
        queryset = super().get_queryset()

        # 🔐 Company Isolation
        if hasattr(user, "profile") and user.profile.user_type != "superadmin":
            queryset = queryset.filter(company=user.profile.company)

        # 👤 Admin
        if hasattr(user, "profile") and user.profile.user_type == "admin":
            # queryset = apply_common_filters(queryset)
            # queryset = self.apply_date_filter(queryset)
            queryset = queryset.filter(company=user.profile.company)
            queryset = self.apply_appointment_filters(queryset)
            return queryset.order_by("-created_at")
        # 👥 Agent / Staff
        # 🔑 Permission-based access
        params = self.request.query_params
        search = params.get("search")
        if search:
            pass
        elif user.has_perm("accounts.view_own_appointment_others"):
            queryset = queryset.filter(created_by=user)

        elif user.has_perm("accounts.view_teamlead_appointment_others"):
            team_users = Employees.objects.filter(
                teamlead=user
            ).values_list("user", flat=True)
            queryset = queryset.filter(created_by__in=team_users)

        elif user.has_perm("accounts.view_manager_appointment_others"):
            team_leads = Employees.objects.filter(
                manager=user
            ).values_list("user", flat=True)

            team_users = Employees.objects.filter(
                teamlead__in=team_leads
            ).values_list("user", flat=True)

            queryset = queryset.filter(
                created_by__in=list(team_leads) + list(team_users)
            )

        elif  user.has_perm("accounts.view_all_appointment_others"):
            queryset = queryset.filter(company=user.profile.company)

        else:
            print("-----------int his")
            queryset = queryset.none()
        queryset = self.apply_appointment_filters(queryset)
        return queryset.order_by("-created_at")


    def perform_create(self, serializer):
        user = self.request.user

        serializer.save(
            company=user.profile.company,
            branch=user.profile.branch,
            created_by=user
        )
    @transaction.atomic
    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        data = request.data.copy()

        incoming_phone = data.get("patient_phone")

        # ❌ Ignore masked phone coming from frontend
        if incoming_phone and "*" in incoming_phone:
            data.pop("patient_phone", None)

        serializer = self.get_serializer(
            instance,
            data=data,
            partial=True
        )
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        return Response(serializer.data)
    @action(detail=False,methods=["post"],url_path="bulk-status-update" )
    @transaction.atomic
    def bulk_status_update(self, request):
        """
        Bulk update appointment status
        """

        appointment_ids = request.data.get("appointment_ids", [])
        appointment_status_id = request.data.get("appointment_status")
        # sync_legacy = request.data.get("sync_legacy_status", False)

        # --------------------
        # Validations
        # --------------------
        if not appointment_ids or not isinstance(appointment_ids, list):
            return Response(
                {"error": "appointment_ids must be a non-empty list"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not appointment_status_id:
            return Response(
                {"error": "appointment_status is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            status_obj = AppointmentStatus.objects.get(
                id=appointment_status_id
            )
        except AppointmentStatus.DoesNotExist:
            return Response(
                {"error": "Invalid appointment_status"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # --------------------
        # Permission check (optional but recommended)
        # --------------------
        # if not request.user.has_perm(
        #     f"follow_up.appointmentstatus_can_work_on_{status_obj.name.lower().replace(' ', '_')}"
        # ):
        #     return Response(
        #         {"error": "You do not have permission to update to this status"},
        #         status=status.HTTP_403_FORBIDDEN
        #     )

        # --------------------
        # Filter appointments (company safe)
        # --------------------
        queryset = Appointment.objects.filter(
            id__in=appointment_ids
        )

        if hasattr(request.user, "profile") and request.user.profile.user_type != "superadmin":
            queryset = queryset.filter(
                company=request.user.profile.company
            )

        updated_count = queryset.update(
            appointment_status=status_obj
        )

        # --------------------
        # Optional legacy sync
        # --------------------
        # if sync_legacy:
        #     queryset.update(
        #         status=status_obj.name.lower()
        #     )

        return Response(
            {
                "message": "Appointment status updated successfully",
                "updated_count": updated_count,
                "appointment_status": {
                    "id": status_obj.id,
                    "name": status_obj.name
                }
            },
            status=status.HTTP_200_OK
        )


class GetPhoneByReferenceAllAPIView(APIView):
    """
    GET phone number using a single reference_id
    reference_id can be:
    - Lead.lead_id
    - Follow_Up.followup_id
    - call_id (cloud vendor)
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        reference_id = request.query_params.get("reference_id")

        try:
            data = get_phone_by_reference_id(
                user=request.user,
                reference_id=reference_id
            )
            return Response(
                {"success": True, "data": data},
                status=status.HTTP_200_OK
            )

        except ValidationError as e:
            return Response(
                {"success": False, "error": e.detail},
                status=status.HTTP_404_NOT_FOUND
            )



class AppointmentLayoutViewSet(viewsets.ModelViewSet):
    serializer_class = AppointmentLayoutSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # 🔐 Only current user's company data
        return Appointment_layout.objects.filter(
            company=self.request.user.profile.company
        )

    def perform_create(self, serializer):
        # 🚫 NOT USED (handled in create())
        pass

    def create(self, request, *args, **kwargs):
        company = request.user.profile.company

        instance = Appointment_layout.objects.filter(
            company=company
        ).first()

        if instance:
            # 🔁 UPDATE existing record
            serializer = self.get_serializer(
                instance,
                data=request.data,
                partial=True
            )
            message = "Appointment layout updated successfully"
        else:
            # ➕ CREATE new record
            serializer = self.get_serializer(
                data=request.data
            )
            message = "Appointment layout created successfully"

        serializer.is_valid(raise_exception=True)
        serializer.save(company=company)

        return Response(
            {
                "success": True,
                "message": message,
                "data": serializer.data
            },
            status=status.HTTP_200_OK
        )


class AppointmentStatusViewSet(viewsets.ModelViewSet):
    queryset = AppointmentStatus.objects.all().order_by('-created_at')
    serializer_class = AppointmentStatusSerializer
    permission_classes = [IsAuthenticated]