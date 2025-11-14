import io
from django.shortcuts import render
import csv
from rest_framework import generics, permissions , viewsets, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import PermissionDenied 
from accounts.models import Branch, Employees
from accounts.permissions import HasPermission
from lead_management.permissions import CanUpdateStatusRemarkOrFullUpdate
from rest_framework.parsers import MultiPartParser
import csv, io

from orders.views import FilterOrdersPagination
from .models import DealCategoryModel, lead_form, Lead, LeadModel, LeadSourceModel, LeadStatusModel, Pipeline, UserCategoryAssignment ,User,Company
from .serializers import DealCategoryModelSerializer, DynamicRequestSerializer, LeadNewSerializer, LeadSerializer, LeadSourceModelSerializer, LeadStatusModelSerializer, PipelineSerializer, UserCategoryAssignmentSerializer
from services.lead_management.lead_management_service import createLead,updateLead,deleteLead,getLead
from rest_framework.permissions import IsAuthenticated, AllowAny, DjangoObjectPermissions
from django.http import JsonResponse
from orders.models import Products
from io import TextIOWrapper
from rest_framework.decorators import action
from django.db import transaction
from random import choice
from datetime import datetime, time
from django.utils.dateparse import parse_date
from rest_framework.pagination import PageNumberPagination
class LeadPagination(PageNumberPagination):
    page_size = 100  # default records per page
    page_size_query_param = 'page_size'
    max_page_size = 1000000

class LeadCreateAPIView(APIView):
    def post(self, request, *args, **kwargs):
        data = request.data
        createRes=createLead(request.data,request.user.id)
        if createRes.errors:
            return Response(createRes.errors, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response(createRes.data, status=status.HTTP_201_CREATED)


    def get(self, request, pk=None, *args, **kwargs):
        try:
            leads = getLead(request.user.id, pk)

            # Handle single vs multiple
            many = False if pk else True
            serializerData = LeadSerializer(leads, many=many)

            # Apply pagination only for multiple results
            if many:
                paginator = FilterOrdersPagination()
                result_page = paginator.paginate_queryset(leads, request)
                serializerData = LeadSerializer(result_page, many=True)
                return paginator.get_paginated_response(serializerData.data)

            return Response(
                {"Success": True, "Data": serializerData.data},
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return Response(
                {"Success": False, "Error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


    def delete(self, request, pk, *args, **kwargs):
        success = deleteLead(pk)
        if success:
            return Response(
                {"Success": True, "Message": "Deleted successfully."},
                status=status.HTTP_200_OK,
            )
        else:
            return Response(
                {"Success": False, "Error": "Not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        
    def put(self, request, pk):
        try:
            updatedData = updateLead(pk, request.data)
            if updatedData:
                return Response(
                    {
                        "Success": True,
                        "data": LeadSerializer(updatedData).data,
                    },
                    status=status.HTTP_200_OK,
                )
            else:
                return Response(
                    {
                        "Success": False,
                        "Error": "Lead not found or invalid data provided.",
                    },
                    status=status.HTTP_404_NOT_FOUND,
                )
        except LeadModel.DoesNotExist:
            return Response(
                {
                    "Success": False,
                    "Error": "Category not found.",
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        except ValueError as e:
            return Response(
                {"Success": False, "Errors": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        
class LeadSourceModelViewSet(viewsets.ModelViewSet):
    queryset = LeadSourceModel.objects.all()
    serializer_class = LeadSourceModelSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        """
        Create a new LeadSource entry with the user's branch and company.
        """
        # Get the authenticated user
        user = request.user
        branch = user.profile.branch
        company = user.profile.company
        # Add the branch and company to the data before creating
        request_data = request.data.copy()  # Make a mutable copy of the request data
        request_data['branch'] = branch.id if branch else None
        request_data['company'] = company.id if company else None

        # Use the modified data to create a new LeadSource entry
        serializer = self.get_serializer(data=request_data)
        if serializer.is_valid():
            # Save the new LeadSource entry
            lead_source = serializer.save()

            # Return a custom response
            return Response({
                "Success": True,
                "Message": "Lead Source created successfully",
                "Data": serializer.data
            }, status=status.HTTP_201_CREATED)
        
        # If validation fails, return an error response
        return Response({
            "Success": False,
            "Message": "Failed to create Lead Source",
            "Errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, *args, **kwargs):
        """
        Retrieve a single LeadSource entry.
        """
        # Get the lead source object based on the primary key
        lead_source = self.get_object()
        # Serialize the lead source data
        serializer = self.get_serializer(lead_source)
        
        return Response({
            "Success": True,
            "Data": serializer.data
        }, status=status.HTTP_200_OK)

    def update(self, request, *args, **kwargs):
        """
        Update a LeadSource entry with the provided data.
        """
        # Get the authenticated user
        user = request.user
        branch = user.profile.branch
        company = user.profile.company
        # Add the branch and company to the request data
        request_data = request.data.copy()  # Make a mutable copy of the request data
        request_data['branch'] = branch.id if branch else None
        request_data['company'] = company.id if company else None

        # Get the lead source instance to update
        lead_source = self.get_object()

        # Serialize the data and update the lead source instance
        serializer = self.get_serializer(lead_source, data=request_data, partial=False)  # partial=False means full update
        if serializer.is_valid():
            updated_lead_source = serializer.save()

            return Response({
                "Success": True,
                "Message": "Lead Source updated successfully",
                "Data": serializer.data
            }, status=status.HTTP_200_OK)

        # If validation fails, return an error response
        return Response({
            "Success": False,
            "Message": "Failed to update Lead Source",
            "Errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

    def partial_update(self, request, *args, **kwargs):
        """
        Partially update a LeadSource entry.
        """
        # Get the authenticated user
        user = request.user
        branch = user.profile.branch
        company = user.profile.company

        # Add the branch and company to the request data
        request_data = request.data.copy()  # Make a mutable copy of the request data
        request_data['branch'] = branch.id if branch else None
        request_data['company'] = company.id if company else None

        # Get the lead source instance to update
        lead_source = self.get_object()

        # Serialize the data and update the lead source instance
        serializer = self.get_serializer(lead_source, data=request_data, partial=True)  # partial=True allows partial update
        if serializer.is_valid():
            updated_lead_source = serializer.save()

            return Response({
                "Success": True,
                "Message": "Lead Source partially updated successfully",
                "Data": serializer.data
            }, status=status.HTTP_200_OK)

        # If validation fails, return an error response
        return Response({
            "Success": False,
            "Message": "Failed to partially update Lead Source",
            "Errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs):
        # Get the lead source instance to delete
        lead_source = self.get_object()

        # Delete the lead source instance
        lead_source.delete()

        return Response({
            "Success": True,
            "Message": "Lead Source deleted successfully"
        }, status=status.HTTP_204_NO_CONTENT)

    def get_queryset(self):
        """
        Optionally filter the queryset based on the authenticated user's branch and company.
        """
        user = self.request.user
        return LeadSourceModel.objects.filter(company=user.profile.company, branch=user.profile.branch)
    

class LeadViewSet(viewsets.ModelViewSet):
    queryset = Lead.objects.all()
    serializer_class = LeadNewSerializer
    permission_classes = [IsAuthenticated, CanUpdateStatusRemarkOrFullUpdate]
    # parser_classes = [MultiPartParser] 
    pagination_class = FilterOrdersPagination
    def get_permissions(self):
        permission_map = {
            'create': ['superadmin_assets.show_submenusmodel_add_leads', 'superadmin_assets.add_submenusmodel'],
            'update': ['superadmin_assets.show_submenusmodel_all_leads', 'superadmin_assets.change_submenusmodel'],
            'destroy': ['superadmin_assets.show_submenusmodel_all_leads', 'superadmin_assets.delete_submenusmodel'],
            'retrieve': ['superadmin_assets.show_submenusmodel_all_leads', 'superadmin_assets.view_submenusmodel'],
            'list': ['superadmin_assets.show_submenusmodel_all_leads', 'superadmin_assets.view_submenusmodel']
        }
        action = self.action
        if action in permission_map:
            permissions = permission_map[action]
            return [HasPermission(perm) for perm in permissions]
        return super().get_permissions()

    def get_queryset(self):
        user = self.request.user
        queryset = Lead.objects.all()

        # 🔹 Filter by company
        if hasattr(user, 'profile') and user.profile.company:
            queryset = queryset.filter(company=user.profile.company)

        # 🔹 Admins can view all under their company
        if hasattr(user, 'profile') and user.profile.user_type == 'admin':
            queryset = self.apply_common_filters(queryset)
            return self.apply_date_filter(queryset)

        # 🔹 Permission-based visibility
        if user.has_perm("accounts.view_own_lead_others"):
            queryset = queryset.filter(assign_user=user)
        elif user.has_perm("accounts.view_teamlead_lead_others"):
            team_lead_users = Employees.objects.filter(teamlead=user).values_list('user', flat=True)
            queryset = queryset.filter(assign_user__in=team_lead_users)
        elif user.has_perm("accounts.view_manager_lead_others"):
            team_leads = Employees.objects.filter(manager=user).values_list('user', flat=True)
            team_lead_users = Employees.objects.filter(teamlead__in=team_leads).values_list('user', flat=True)
            all_users = list(team_leads) + list(team_lead_users)
            queryset = queryset.filter(assign_user__in=all_users)
        elif user.has_perm("accounts.view_all_lead_others"):
            pass
        else:
            queryset = Lead.objects.none()

        # 🔹 Apply additional filters
        queryset = self.apply_common_filters(queryset)
        queryset = self.apply_date_filter(queryset)
        return queryset


    def apply_common_filters(self, queryset):
        """Apply filters for phone, email, city, status, and lead_id."""
        customer_phone = self.request.query_params.get('mobile')
        customer_email = self.request.query_params.get('email')
        customer_city = self.request.query_params.get('city')
        status = self.request.query_params.get('status')
        lead_id = self.request.query_params.get('lead_id')

        if customer_phone:
            queryset = queryset.filter(customer_phone__icontains=customer_phone)
        if customer_email:
            queryset = queryset.filter(customer_email__icontains=customer_email)
        if customer_city:
            queryset = queryset.filter(customer_city__icontains=customer_city)
        if status:
            queryset = queryset.filter(status__id=status)  # assuming status is a FK
        if lead_id:
            queryset = queryset.filter(lead_id__icontains=lead_id)  # allows partial matches like LEAD123

        return queryset


    def apply_date_filter(self, queryset):
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')

        # both start and end date
        if start_date and end_date:
            start = parse_date(start_date)
            end = parse_date(end_date)
            if start and end:
                start = datetime.combine(start, time.min)
                end = datetime.combine(end, time.max)
                queryset = queryset.filter(created_at__range=[start, end])

        # only start_date
        elif start_date:
            start = parse_date(start_date)
            if start:
                start = datetime.combine(start, time.min)
                queryset = queryset.filter(created_at__gte=start)

        # ✅ only end_date (your case)
        elif end_date:
            end = parse_date(end_date)
            if end:
                # include full end date till 23:59:59
                end = datetime.combine(end, time.max)
                queryset = queryset.filter(created_at__lte=end)

        return queryset

    def perform_create(self, serializer):
        user = self.request.user
        if hasattr(user, 'profile') and user.profile.company and user.profile.branch:
            company = user.profile.company
            branch = user.profile.branch
            serializer.save(
                created_by=user,
                updated_by=user,
                company=company,
                branch=branch
            )
        else:
            raise PermissionDenied("User profile must have a company and branch.")

    def perform_update(self, serializer):
        user = self.request.user
        if user.has_perm('superadmin_assets.change_submenusmodel'):
            serializer.save(updated_by=user)
        elif user.has_perm('superadmin_assets.change_submenusmodel'):
            restricted_fields = {'status', 'remark'}
            if set(self.request.data.keys()).issubset(restricted_fields):
                serializer.save(updated_by=user)
            else:
                raise PermissionDenied("You can only update 'status' and 'remark'.")
        else:
            raise PermissionDenied("You do not have permission to update this lead.")
    
    @transaction.atomic
    def create(self, request, *args, **kwargs):
        user = request.user
        if not user.is_authenticated:
            return Response({"Success": False, "Message": "Authentication is required."}, status=status.HTTP_401_UNAUTHORIZED)

        request_data = request.data.copy()
        profile = getattr(user, "profile", None)
        if profile:
            request_data["company"] = profile.company.id if profile.company else None
            request_data["branch"] = profile.branch.id if profile.branch else None

        pipeline_id = request_data.get("pipeline")
        if pipeline_id:
            try:
                pipeline = Pipeline.objects.select_for_update().get(id=pipeline_id)
                request_data["lead_source"] = pipeline.lead_source.id
                request_data["deal_category"] = pipeline.deal_category.id

                if pipeline.round_robin:
                    # assigned_users = list(pipeline.assigned_users.all().order_by("id"))
                    assigned_users = list(pipeline.assigned_users.filter(profile__status=1).order_by("id"))
                    if assigned_users:
                        next_index = (pipeline.last_assigned_index + 1) % len(assigned_users)
                        next_user = assigned_users[next_index]

                        request_data["assign_user"] = next_user.id
                        pipeline.last_assigned_index = next_index
                        pipeline.save()
                    else:
                        request_data["assign_user"] = user.id
                else:
                    request_data["assign_user"] = user.id

            except Pipeline.DoesNotExist:
                return Response({
                    "Success": False,
                    "Message": f"Pipeline with ID {pipeline_id} does not exist."
                }, status=status.HTTP_400_BAD_REQUEST)
        serializer = self.get_serializer(data=request_data)
        
        if serializer.is_valid():
            # print(serializer.data,"----------------358")
            lead = serializer.save()
            return Response({
                "Success": True,
                "Message": "Lead created successfully",
                "Data": serializer.data
            }, status=status.HTTP_201_CREATED)

        return Response({
            "Success": False,
            "Message": "Failed to create lead.",
            "Errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs):
        lead = self.get_object()
        user = request.user
        if user == lead.created_by or user.is_staff:
            lead.delete()
            return Response({"Success": True, "Message": "Lead deleted successfully."}, status=status.HTTP_204_NO_CONTENT)
        else:
            return Response({"Success": False, "Message": "You do not have permission to delete this lead."}, status=status.HTTP_403_FORBIDDEN)

    @action(detail=False, methods=['post'], url_path='bulk-upload', permission_classes=[IsAuthenticated])
    @transaction.atomic
    def bulk_upload(self, request):
        file = request.FILES.get('file')
        user = request.user

        if not file:
            return Response({"Success": False, "Message": "CSV file is required."}, status=400)
        if not file.name.endswith('.csv'):
            return Response({"Success": False, "Message": "Only CSV files are allowed."}, status=400)

        decoded_file = file.read().decode('utf-8')
        csv_data = csv.DictReader(io.StringIO(decoded_file))
        created_leads = []
        errors = []

        for i, row in enumerate(csv_data, start=1):
            try:
                pipeline_id = row.get('pipeline')
                if not pipeline_id:
                    raise Exception("Missing pipeline ID in row.")

                try:
                    pipeline = Pipeline.objects.select_for_update().get(id=pipeline_id)
                except Pipeline.DoesNotExist:
                    raise Exception(f"Pipeline ID {pipeline_id} not found.")

                if pipeline.round_robin:
                    # assigned_users = list(pipeline.assigned_users.all().order_by("id"))
                    assigned_users = list(pipeline.assigned_users.filter(profile__status=1).order_by("id"))
                    if assigned_users:
                        next_index = (pipeline.last_assigned_index + 1) % len(assigned_users)
                        next_user = assigned_users[next_index]
                        row['assign_user'] = next_user.id
                        pipeline.last_assigned_index = next_index
                        pipeline.save()
                    else:
                        row['assign_user'] = user.id
                else:
                    row['assign_user'] = user.id

                # Add company and branch from profile
                profile = getattr(user, 'profile', None)
                if profile:
                    row['company'] = profile.company.id if profile.company else None
                    row['branch'] = profile.branch.id if profile.branch else None

                serializer = self.get_serializer(data=row)
                serializer.is_valid(raise_exception=True)
                serializer.save(created_by=user, updated_by=user)
                created_leads.append(serializer.data)

            except Exception as e:
                errors.append({"row": i, "error": str(e)})

        if errors:
            return Response({
                "Success": False,
                "Message": "Some rows failed to import.",
                "Errors": errors,
                "Imported": len(created_leads)
            }, status=207)  # Multi-status

        return Response({
            "Success": True,
            "Message": f"{len(created_leads)} leads uploaded successfully.",
            "Data": created_leads
        }, status=201)

class LeadBulkUploadView(APIView):
    """
    API endpoint for uploading leads in bulk using a CSV file.
    """
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        permission_map = {
            'create': ['superadmin_assets.show_submenusmodel_add_leads', 'superadmin_assets.add_submenusmodel'],
            'update': ['superadmin_assets.show_submenusmodel_all_leads', 'superadmin_assets.change_submenusmodel'],
            'destroy': ['superadmin_assets.show_submenusmodel_all_leads', 'superadmin_assets.delete_submenusmodel'],
            'retrieve': ['superadmin_assets.show_submenusmodel_all_leads', 'superadmin_assets.view_submenusmodel'],
            'list': ['superadmin_assets.show_submenusmodel_all_leads', 'superadmin_assets.view_submenusmodel']
        }

        action = getattr(self, 'action', None)
        if action in permission_map:
            permissions = permission_map[action]
            return [HasPermission(perm) for perm in permissions]

        return super().get_permissions()

    def is_valid_phone_number(self, number):
        """
        Validate phone number using defined rules.
        """
        if not number:
            return False

        str_number = str(number).strip()

        # Rule 1: Reject scientific notation (e.g. 1.23E+10)
        if "e" in str_number.lower():
            return False

        # Rule 2: Must be numeric only
        if not str_number.isdigit():
            return False

        # Rule 3: Must be exactly 10 digits
        if len(str_number) != 10:
            return False

        return True

    def process_phone_number(self, number):
        """Add +91 prefix to valid 10-digit numbers"""
        return f"+91{number}"

    def post(self, request, *args, **kwargs):
        user = request.user
        if 'file' not in request.FILES:
            return Response({"Error": "No file provided"}, status=status.HTTP_400_BAD_REQUEST)

        csv_file = request.FILES['file']
        if not csv_file.name.endswith('.csv'):
            return Response({"Error": "File is not a CSV"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            decoded_file = csv_file.read().decode('utf-8')
            io_string = io.StringIO(decoded_file)
            reader = csv.DictReader(io_string)

            leads_data = []
            errors = []

            for index, row in enumerate(reader, start=1):
                try:
                    phone_value = str(row.get('customer_phone', '')).strip()

                    # Validation check
                    if not self.is_valid_phone_number(phone_value):
                        errors.append({
                            "row": index,
                            "error": f"Invalid phone number: {phone_value}",
                            "data": row
                        })
                        continue

                    processed_phone = self.process_phone_number(phone_value)

                    # Foreign key resolution
                    product = Products.objects.get(id=row['product'])
                    pipeline = Pipeline.objects.get(id=row['pipeline'])
                    status_obj = LeadStatusModel.objects.get(id=row['status']) if row.get('status') else None
                    branch = Branch.objects.get(id=row['branch']) if row.get('branch') else None

                    if pipeline.round_robin:
                        assigned_users = list(pipeline.assigned_users.all().order_by("id"))
                        if assigned_users:
                            next_index = (pipeline.last_assigned_index + 1) % len(assigned_users)
                            next_user = assigned_users[next_index]
                            row['assign_user'] = next_user.id
                            pipeline.last_assigned_index = next_index
                            pipeline.save()
                        else:
                            row['assign_user'] = user.id
                    else:
                        row['assign_user'] = user.id

                    profile = request.user.profile
                    company = profile.company if profile else None

                    lead_data = {
                        'customer_name': row.get('customer_name', 'Null'),
                        'customer_email': row.get('customer_email', 'null@test.com'),
                        'customer_phone': processed_phone,
                        'customer_postalcode': row.get('customer_postalcode', 'Null'),
                        'customer_city': row.get('customer_city', 'Null'),
                        'customer_state': row.get('customer_state', 'Null'),
                        'customer_address': row.get('customer_address', 'Null'),
                        'customer_message': row.get('customer_message', 'Null'),
                        'remark': row.get('remark', 'Null'),
                        'product': product.id,
                        'lead_source': pipeline.lead_source.id,
                        'pipeline': pipeline.id,
                        'branch': branch.id if branch else None,
                        'company': company.id if company else None,
                        'assign_user': assign_user,
                    }

                    # Save each valid record independently
                    with transaction.atomic():
                        serializer = LeadNewSerializer(data=lead_data)
                        if serializer.is_valid(raise_exception=False):
                            serializer.save(created_by=request.user, updated_by=request.user)
                            leads_data.append(serializer.data)
                        else:
                            errors.append({
                                "row": index,
                                "error": serializer.errors,
                                "data": row
                            })

                except Exception as e:
                    errors.append({
                        "row": index,
                        "error": str(e),
                        "data": row
                    })

            # Build partial success response
            response_data = {
                "Success": True if leads_data else False,
                "Message": f"{len(leads_data)} leads uploaded successfully. {len(errors)} failed.",
                "Saved_Count": len(leads_data),
                "Failed_Count": len(errors),
                "Errors": errors
            }

            return Response(response_data, status=status.HTTP_207_MULTI_STATUS if errors else status.HTTP_201_CREATED)

        except Exception as e:
            print(str(e))
            return Response({"Error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class LeadStatusModelViewSet(viewsets.ModelViewSet):
    queryset = LeadStatusModel.objects.all()
    serializer_class = LeadStatusModelSerializer
    permission_classes = [IsAuthenticated]
    # def get_permissions(self):
    #     permission_map = {
    #         'create': ['superadmin_assets.show_settingsmenu_lead_setting', 'superadmin_assets.add_settingsmenu'],
    #         'update': ['superadmin_assets.show_settingsmenu_lead_setting', 'superadmin_assets.change_settingsmenu'],
    #         'destroy': ['superadmin_assets.show_settingsmenu_lead_setting', 'superadmin_assets.delete_settingsmenu'],
    #         'retrieve': ['superadmin_assets.show_settingsmenu_lead_setting', 'superadmin_assets.view_settingsmenu'],
    #         'list': ['superadmin_assets.show_settingsmenu_lead_setting', 'superadmin_assets.view_settingsmenu']
    #     }
        
    #     action = self.action
    #     if action in permission_map:
    #         permissions = permission_map[action]
    #         return [HasPermission(perm) for perm in permissions]  # Return a list of permission checks
    
        # return super().get_permissions()
    def create(self, request, *args, **kwargs):
        """
        Create a new LeadStatus entry with the user's branch and company.
        """
        # Get the authenticated user
        user = request.user
        branch = user.profile.branch
        company = user.profile.company
        # Add the branch and company to the data before creating
        request_data = request.data.copy()  # Make a mutable copy of the request data
        request_data['branch'] = branch.id if branch else None
        request_data['company'] = company.id if company else None

        # Use the modified data to create a new LeadStatus entry
        serializer = self.get_serializer(data=request_data)
        if serializer.is_valid():
            # Save the new LeadSource entry
            lead_status = serializer.save()

            # Return a custom response
            return Response({
                "Success": True,
                "Message": "Lead Status created successfully",
                "Data": serializer.data
            }, status=status.HTTP_201_CREATED)
        
        # If validation fails, return an error response
        return Response({
            "Success": False,
            "Message": "Failed to create Lead Status",
            "Errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, *args, **kwargs):
        """
        Retrieve a single LeadStatus entry.
        """
        # Get the lead Status object based on the primary key
        lead_status = self.get_object()
        # Serialize the lead Status data
        serializer = self.get_serializer(lead_status)
        
        return Response({
            "Success": True,
            "Data": serializer.data
        }, status=status.HTTP_200_OK)

    def update(self, request, *args, **kwargs):
        """
        Update a LeadStatus entry with the provided data.
        """
        # Get the authenticated user
        user = request.user
        branch = user.profile.branch
        company = user.profile.company
        # Add the branch and company to the request data
        request_data = request.data.copy()  # Make a mutable copy of the request data
        request_data['branch'] = branch.id if branch else None
        request_data['company'] = company.id if company else None

        # Get the lead Status instance to update
        lead_status = self.get_object()

        # Serialize the data and update the lead Status instance
        serializer = self.get_serializer(lead_status, data=request_data, partial=False)  # partial=False means full update
        if serializer.is_valid():
            updated_lead_status = serializer.save()

            return Response({
                "Success": True,
                "Message": "Lead Status updated successfully",
                "Data": serializer.data
            }, status=status.HTTP_200_OK)

        # If validation fails, return an error response
        return Response({
            "Success": False,
            "Message": "Failed to update Lead Status",
            "Errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

    def partial_update(self, request, *args, **kwargs):
        """
        Partially update a LeadStatus entry.
        """
        # Get the authenticated user
        user = request.user
        branch = user.profile.branch
        company = user.profile.company

        # Add the branch and company to the request data
        request_data = request.data.copy()  # Make a mutable copy of the request data
        request_data['branch'] = branch.id if branch else None
        request_data['company'] = company.id if company else None

        # Get the lead Status instance to update
        lead_status = self.get_object()

        # Serialize the data and update the lead source instance
        serializer = self.get_serializer(lead_status, data=request_data, partial=True)  # partial=True allows partial update
        if serializer.is_valid():
            updated_lead_status = serializer.save()

            return Response({
                "Success": True,
                "Message": "Lead Status partially updated successfully",
                "Data": serializer.data
            }, status=status.HTTP_200_OK)

        # If validation fails, return an error response
        return Response({
            "Success": False,
            "Message": "Failed to partially update Lead Status",
            "Errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs):
        # Get the lead status instance to delete
        lead_status = self.get_object()

        # Delete the lead status instance
        lead_status.delete()

        return Response({
            "Success": True,
            "Message": "Lead Status deleted successfully"
        }, status=status.HTTP_204_NO_CONTENT)

    def get_queryset(self):
        """
        Optionally filter the queryset based on the authenticated user's branch and company.
        """
        user = self.request.user
        return LeadStatusModel.objects.filter(company=user.profile.company, branch=user.profile.branch)
    

class DealCategoryModelViewSet(viewsets.ModelViewSet):
    queryset = DealCategoryModel.objects.all()
    serializer_class = DealCategoryModelSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        """
        Create a new Deal Category entry with the user's branch and company.
        """
        # Get the authenticated user
        user = request.user
        branch = user.profile.branch
        company = user.profile.company
        # Add the branch and company to the data before creating
        request_data = request.data.copy()  # Make a mutable copy of the request data
        request_data['branch'] = branch.id if branch else None
        request_data['company'] = company.id if company else None

        # Use the modified data to create a new DealCategory entry
        serializer = self.get_serializer(data=request_data)
        if serializer.is_valid():
            # Save the new LeadSource entry
            deal_category = serializer.save()

            # Return a custom response
            return Response({
                "Success": True,
                "Message": "Deal Category created successfully",
                "Data": serializer.data
            }, status=status.HTTP_201_CREATED)
        
        # If validation fails, return an error response
        return Response({
            "Success": False,
            "Message": "Failed to create Lead Status",
            "Errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, *args, **kwargs):
        """
        Retrieve a single DealCategory entry.
        """
        # Get the Deal Category object based on the primary key
        deal_category = self.get_object()
        # Serialize the Deal Category data
        serializer = self.get_serializer(deal_category)
        
        return Response({
            "Success": True,
            "Data": serializer.data
        }, status=status.HTTP_200_OK)

    def update(self, request, *args, **kwargs):
        """
        Update a DealCategory entry with the provided data.
        """
        # Get the authenticated user
        user = request.user
        branch = user.profile.branch
        company = user.profile.company
        # Add the branch and company to the request data
        request_data = request.data.copy()  # Make a mutable copy of the request data
        request_data['branch'] = branch.id if branch else None
        request_data['company'] = company.id if company else None

        # Get the Deal Category instance to update
        deal_category = self.get_object()

        # Serialize the data and update the Deal Category instance
        serializer = self.get_serializer(deal_category, data=request_data, partial=False)  # partial=False means full update
        if serializer.is_valid():
            updated_deal_category = serializer.save()

            return Response({
                "Success": True,
                "Message": "Deal Category updated successfully",
                "Data": serializer.data
            }, status=status.HTTP_200_OK)

        # If validation fails, return an error response
        return Response({
            "Success": False,
            "Message": "Failed to update Lead category",
            "Errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

    def partial_update(self, request, *args, **kwargs):
        """
        Partially update a DealCategory entry.
        """
        # Get the authenticated user
        user = request.user
        branch = user.profile.branch
        company = user.profile.company

        # Add the branch and company to the request data
        request_data = request.data.copy()  # Make a mutable copy of the request data
        request_data['branch'] = branch.id if branch else None
        request_data['company'] = company.id if company else None

        # Get the Deal Category instance to update
        deal_category = self.get_object()

        # Serialize the data and update the lead source instance
        serializer = self.get_serializer(deal_category, data=request_data, partial=True)  # partial=True allows partial update
        if serializer.is_valid():
            updated_deal_category = serializer.save()

            return Response({
                "Success": True,
                "Message": "Deal Category partially updated successfully",
                "Data": serializer.data
            }, status=status.HTTP_200_OK)

        # If validation fails, return an error response
        return Response({
            "Success": False,
            "Message": "Failed to partially update Lead category",
            "Errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs):
        # Get the Deal Category instance to delete
        deal_category = self.get_object()

        # Delete the Deal Category instance
        deal_category.delete()

        return Response({
            "Success": True,
            "Message": "Deal Category deleted successfully"
        }, status=status.HTTP_204_NO_CONTENT)

    def get_queryset(self):
        """
        Optionally filter the queryset based on the authenticated user's branch and company.
        """
        user = self.request.user
        return DealCategoryModel.objects.filter(company=user.profile.company, branch=user.profile.branch)
    

class UserCategoryAssignmentViewSet(viewsets.ModelViewSet):
    queryset = UserCategoryAssignment.objects.all()
    serializer_class = UserCategoryAssignmentSerializer
    permission_classes = [IsAuthenticated]  # Only allow authenticated users

    def perform_create(self, serializer):
        """
        Override the default create method to assign a category to a user.
        """
        user_id = self.request.data.get('user_profile')
        deal_category_id = self.request.data.get('deal_category')

        try:
            user_profile = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)

        try:
            deal_category = DealCategoryModel.objects.get(id=deal_category_id)
        except DealCategoryModel.DoesNotExist:
            return Response({"detail": "Deal Category not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer.save(user_profile=user_profile, deal_category=deal_category)

    def get(self, request, pk=None, *args, **kwargs):
        """
        Get all users with their assigned categories based on the company.
        """
        company_id = request.user.profile.company.id

        if not company_id:
            return Response({"detail": "Company ID is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            company = Company.objects.get(id=company_id)
        except Company.DoesNotExist:
            return Response({"detail": "Company not found."}, status=status.HTTP_404_NOT_FOUND)

        assignments = (
        UserCategoryAssignment.objects.filter(
            user_profile__profile__company=company_id,
            user_profile__profile__status=1
        )
        .select_related('user_profile', 'deal_category')
    )

        print(assignments,"--------------------1019")
        if not assignments.exists():
            return Response({"detail": "No users or categories found for this company."}, status=status.HTTP_404_NOT_FOUND)

        users_with_categories = [
            {
                "id":assignment.id,
                "user_name": assignment.user_profile.username,
                "user_id": assignment.user_profile.id,
                "deal_category": assignment.deal_category.name,
                "deal_category_id": assignment.deal_category.id
            }
            for assignment in assignments
        ]

        return Response(users_with_categories, status=status.HTTP_200_OK)

    def delete(self, request, pk, *args, **kwargs):
        """
        Delete a category assignment for a user.
        """
        try:
            user_category_assignment = UserCategoryAssignment.objects.get(id=pk)
        except UserCategoryAssignment.DoesNotExist:
            return Response({"detail": "UserCategoryAssignment not found."}, status=status.HTTP_404_NOT_FOUND)

        user_category_assignment.delete()
        return Response({"detail": "Category unassigned successfully."}, status=status.HTTP_200_OK)

    def update(self, request, pk=None, *args, **kwargs):
        """
        Update an existing category assignment for a user.
        """
        try:
            user_category_assignment = UserCategoryAssignment.objects.get(id=pk)
        except UserCategoryAssignment.DoesNotExist:
            return Response({"detail": "UserCategoryAssignment not found."}, status=status.HTTP_404_NOT_FOUND)

        user_id = request.data.get('user_profile')
        deal_category_id = request.data.get('deal_category')

        try:
            user_profile = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)

        try:
            deal_category = DealCategoryModel.objects.get(id=deal_category_id)
        except DealCategoryModel.DoesNotExist:
            return Response({"detail": "Deal Category not found."}, status=status.HTTP_404_NOT_FOUND)

        user_category_assignment.user_profile = user_profile
        user_category_assignment.deal_category = deal_category
        user_category_assignment.save()

        return Response({"detail": "UserCategoryAssignment updated successfully."}, status=status.HTTP_200_OK)
    
    def list(self, request, *args, **kwargs):
        """
        Get all users with their assigned categories based on the company.
        """
        company_id = request.user.profile.company.id

        if not company_id:
            return Response({"detail": "Company ID is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            company = Company.objects.get(id=company_id)
        except Company.DoesNotExist:
            return Response({"detail": "Company not found."}, status=status.HTTP_404_NOT_FOUND)

        assignments = UserCategoryAssignment.objects.filter(
            user_profile__profile__company=company_id, user_profile__profile__status=1
        ).select_related('user_profile', 'deal_category')

        if not assignments.exists():
            data = {"results":[],"count":0}
            return Response(data, status=status.HTTP_200_OK)
            return Response({"detail": "No users or categories found for this company."}, status=status.HTTP_404_NOT_FOUND)

        users_with_categories = [
            {   "id":assignment.id,
                "user_name": assignment.user_profile.username,
                "user_id": assignment.user_profile.id,
                "deal_category": assignment.deal_category.name,
                "deal_category_id": assignment.deal_category.id
            }
            for assignment in assignments
        ]
        data = {"results":users_with_categories,"count":len(users_with_categories)}
        return Response(data, status=status.HTTP_200_OK)



class PipelineViewSet(viewsets.ModelViewSet):
    queryset = Pipeline.objects.all()
    serializer_class = PipelineSerializer

    def check_user_assigned_to_deal_category(self, user, deal_category):
        """
        Check if the user is assigned to the given deal category.
        """
        if not UserCategoryAssignment.objects.filter(user_profile=user.profile, deal_category=deal_category).exists():
            return False
        return True

    def assign_users_to_pipeline(self, pipeline, assigned_users, deal_category):
        """
        Helper method to assign users to the pipeline if they are valid for the deal category.
        """
        valid_users = UserCategoryAssignment.objects.filter(deal_category=deal_category).values_list('user_profile__profile__user', flat=True)

        
        for user_id in assigned_users:
            if user_id not in valid_users:
                raise ValueError(f"User with ID {user_id} is not assigned to this deal category.")
            
            try:
                user = User.objects.get(id=user_id)
                pipeline.assigned_users.add(user)  # Add user to ManyToMany field
            except User.DoesNotExist:
                raise ValueError(f"User with ID {user_id} not found.")

    @transaction.atomic
    def perform_create(self, serializer):
        """
        Handle the creation of the pipeline along with the user assignment validation.
        Only assign users who are already assigned to a deal category.
        """
        user = self.request.user  # Get the authenticated user
        company = user.profile.company
        branch = user.profile.branch

        if not company or not branch:
            return Response({"detail": "User profile must have a company and branch."}, status=status.HTTP_400_BAD_REQUEST)

        # Automatically set the company and branch
        pipeline = serializer.save(company=company, branch=branch)

        # Get the deal category and assigned users from the request data
        assigned_users = self.request.data.get("assigned_users", [])
        deal_category_id = self.request.data.get("deal_category")

        try:
            # Fetch the deal category
            deal_category = DealCategoryModel.objects.get(id=deal_category_id)
        except DealCategoryModel.DoesNotExist:
            return Response({"detail": f"Deal Category with ID {deal_category_id} not found."}, status=status.HTTP_404_NOT_FOUND)

        try:
            # Assign users to the pipeline
            self.assign_users_to_pipeline(pipeline, assigned_users, deal_category)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        pipeline.save()  # Save the pipeline after assigning users

    @transaction.atomic
    def perform_update(self, serializer):
        """
        Handle updating the pipeline along with the user assignment validation.
        Only assign users who are already assigned to a deal category.
        """
        user = self.request.user
        company = user.profile.company
        branch = user.profile.branch

        if not company or not branch:
            return Response({"detail": "User profile must have a company and branch."}, status=status.HTTP_400_BAD_REQUEST)

        # Automatically set the company and branch
        pipeline = serializer.save(company=company, branch=branch)

        # Get the deal category and assigned users from the request data
        assigned_users = self.request.data.get("assigned_users", [])
        deal_category_id = self.request.data.get("deal_category")

        try:
            # Fetch the deal category
            deal_category = DealCategoryModel.objects.get(id=deal_category_id)
        except DealCategoryModel.DoesNotExist:
            return Response({"detail": f"Deal Category with ID {deal_category_id} not found."}, status=status.HTTP_404_NOT_FOUND)

        try:
            # Assign users to the pipeline
            self.assign_users_to_pipeline(pipeline, assigned_users, deal_category)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        pipeline.save()  # Save the pipeline after assigning users

    @action(detail=True, methods=['get'], url_path='assigned-users')
    def get_assigned_users(self, request, pk=None):
        """
        Get all users assigned to a specific pipeline.
        """
        try:
            pipeline = Pipeline.objects.get(id=pk)
        except Pipeline.DoesNotExist:
            return Response({"detail": "Pipeline not found."}, status=status.HTTP_404_NOT_FOUND)

        # Get all users assigned to this pipeline
        # assigned_users = pipeline.assigned_users.all()
        assigned_users = pipeline.assigned_users.filter(profile__status=1)
        if not assigned_users:
            return Response({"detail": "No users assigned to this pipeline."}, status=status.HTTP_404_NOT_FOUND)

        # Serialize the assigned users data
        user_data = [{"id": user.id, "username": user.username} for user in assigned_users]
        return Response(user_data, status=status.HTTP_200_OK)
    def get_queryset(self):
        """
        Filter pipelines by the authenticated user's company and branch.
        """
        user = self.request.user
        company = user.profile.company
        branch = user.profile.branch

        return Pipeline.objects.filter(company=company, branch=branch)
    
class LeadformViewSet(viewsets.ModelViewSet):
    queryset = lead_form.objects.all().order_by('-created_at')
    serializer_class = DynamicRequestSerializer


class LeadsViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Public API to list all leads with pagination (no authentication required).
    """
    queryset = Lead.objects.all().order_by('-created_at')
    serializer_class = LeadNewSerializer
    pagination_class = LeadPagination

class LeadDetailByLeadIDView(APIView):
    """
    Get Lead details by lead_id
    Example: /api/leads/by-lead-id/?lead_id=LEAD12345
    """
    def get(self, request):
        lead_id = request.query_params.get('lead_id', None)
        if not lead_id:
            return Response({"error": "lead_id parameter is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            lead = Lead.objects.get(lead_id=lead_id)
        except Lead.DoesNotExist:
            return Response({"error": "Lead not found"}, status=status.HTTP_404_NOT_FOUND)

        serializer = LeadNewSerializer(lead)
        return Response(serializer.data, status=status.HTTP_200_OK)
