import csv
from django.http import HttpResponse
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import viewsets,status

from accounts.models import Employees
from accounts.permissions import HasPermission
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

class FollowUpView(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = Follow_Up.objects.all()
    serializer_class = FollowUpSerializer
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
        mutable_data = request.data.copy()
        if 'branch' not in mutable_data:
            mutable_data['branch'] = request.user.profile.branch.id
        mutable_data['company'] = user.profile.company.id
        request._full_data = mutable_data

        return super().create(request, *args, **kwargs)
    
    @transaction.atomic
    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        user = request.user

        mutable_data = request.data.copy()

        if 'branch' not in mutable_data:
            mutable_data['branch'] = request.user.profile.branch.id
        if 'company' not in mutable_data:
            mutable_data['company'] = request.user.profile.company.id
        
        serializer = self.get_serializer(instance, data=mutable_data, partial=True)
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