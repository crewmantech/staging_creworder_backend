# from django.shortcuts import render
# from rest_framework.views import APIView
# from django.db import transaction
# from rest_framework import viewsets, status
# from services.cloud_telephoney.cloud_telephoney_service import (
#     createCloudTelephoneyChannel,
#     deleteCloudTelephoneyChannel,
#     updateCloudTelephoneyChannel,
#     getCloudTelephoneyChannel,
#     createCloudTelephoneyChannelAssign,
#     updateCloudTelephoneyChannelAssign,
#     deleteCloudTelephoneyChannelAssign
# )
# from rest_framework.permissions import IsAuthenticated
# from .serializers import (
#     CloudTelephonyChannelSerializer,
#     CloudTelephonyChannelAssignSerializer,
#     UserMailSetUpSerializers
# )
# import pdb
# from .models import UserMailSetup

# from rest_framework.response import Response
# from rest_framework import status


# # Create your views here.
# class CreateCloudTelephoneyChannel(APIView):
#     permission_classes = [IsAuthenticated]

#     def post(self, request):
#         try:
#             CloudTelephonyChannel = createCloudTelephoneyChannel(
#                 request.data, request.user.id
#             )
#             return Response(
#                 {
#                     "Success": True,
#                     "data": CloudTelephonyChannelSerializer(CloudTelephonyChannel).data,
#                 },
#                 status=status.HTTP_201_CREATED,
#             )
#         except ValueError as e:
#             return Response(
#                 {"Success": False, "Errors": str(e)},
#                 status=status.HTTP_400_BAD_REQUEST,
#             )


# class CloudTelephoneyChannelDelete(APIView):
#     permission_classes = [IsAuthenticated]

#     def delete(self, request, id):
#         success = deleteCloudTelephoneyChannel(id)
#         if success:
#             return Response(
#                 {"Success": True, "Message": "Deleted successfully."},
#                 status=status.HTTP_200_OK,
#             )
#         else:
#             return Response(
#                 {"Success": False, "Error": "Not found."},
#                 status=status.HTTP_404_NOT_FOUND,
#             )


# class CloudTelephoneyChannelUpdate(APIView):
#     permission_classes = [IsAuthenticated]

#     def put(self, request, id):
#         updatedData = updateCloudTelephoneyChannel(id, request.data)
#         if updatedData:
#             return Response(
#                 {
#                     "Success": True,
#                     "data": CloudTelephonyChannelSerializer(updatedData).data,
#                 },
#                 status=status.HTTP_200_OK,
#             )
#         else:
#             return Response(
#                 {
#                     "Success": False,
#                     "Error": "Not found or invalid data provided.",
#                 },
#                 status=status.HTTP_404_NOT_FOUND,
#             )


# class CloudTelephoneyChannelList(APIView):
#     permission_classes = [IsAuthenticated]
#     def get(self, request):
#         try:
#             data = getCloudTelephoneyChannel(request.user.id)
#             serializer = CloudTelephonyChannelSerializer(data, many=True)
#             return Response(
#                 {"Success": True, "Data": serializer.data},
#                 status=status.HTTP_200_OK,
#             )
#         except Exception as e:
#             return Response(
#                 {"Success": False, "Error": str(e)},
#                 status=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             )

# class CloudtelephoneyChannelAssignForUser(APIView):
#     permission_classes = [IsAuthenticated]
#     def post(self, request):
#         try:
#             cloud_telephony_channel = createCloudTelephoneyChannelAssign(
#                 request.data, request.user.id
#             )
#             if isinstance(cloud_telephony_channel, str):
#                 return Response(
#                     {"Success": False, "Errors": cloud_telephony_channel},
#                     status=status.HTTP_400_BAD_REQUEST,
#                 )
#             return Response(
#                 {
#                     "Success": True,
#                     "data": CloudTelephonyChannelAssignSerializer(cloud_telephony_channel).data,
#                 },
#                 status=status.HTTP_201_CREATED,
#             )
#         except ValueError as e:
#             return Response(
#                 {"Success": False, "Errors": str(e)},
#                 status=status.HTTP_400_BAD_REQUEST,
#             )
#         except Exception as e:
#             return Response(
#                 {"Success": False, "Errors": "An unexpected error occurred: " + str(e)},
#                 status=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             )


# class CloudTelephoneyChannelAssignUpdate(APIView):
#     permission_classes = [IsAuthenticated]
#     def put(self, request, id):
#         updatedData = updateCloudTelephoneyChannelAssign(id, request.data)
#         if updatedData:
#             return Response(
#                 {
#                     "Success": True,
#                     "data": CloudTelephonyChannelAssignSerializer(updatedData).data,
#                 },
#                 status=status.HTTP_200_OK,
#             )
#         else:
#             return Response(
#                 {
#                     "Success": False,
#                     "Error": "Not found or invalid data provided.",
#                 },
#                 status=status.HTTP_404_NOT_FOUND,
#             )
        
# class CloudTelephoneyChannelAssignDelete(APIView):
#     permission_classes = [IsAuthenticated]
#     def delete(self, request, id):
#         success = deleteCloudTelephoneyChannelAssign(id)
#         if success:
#             return Response(
#                 {"Success": True, "Message": "Deleted successfully."},
#                 status=status.HTTP_200_OK,
#             )
#         else:
#             return Response(
#                 {"Success": False, "Error": "Not found."},
#                 status=status.HTTP_404_NOT_FOUND,
#             )
# class UserMailSetupView(viewsets.ModelViewSet):
#     permission_classes = [IsAuthenticated]
#     queryset =UserMailSetup.objects.all()
#     serializer_class= UserMailSetUpSerializers

#     @transaction.atomic
#     def create(self, request, *args, **kwargs):
#         user = request.user
#         request.data['company'] = user.profile.company.id
#         return super().create(request, *args, **kwargs)
    
#     @transaction.atomic
#     def update(self, request, *args, **kwargs):
#         instance = self.get_object()
#         user = request.user

#         if 'company' not in request.data:
#             request.data['company'] = instance.company.id 
#         serializer = self.get_serializer(instance, data=request.data, partial=True)
#         serializer.is_valid(raise_exception=True)
#         serializer.save()
#         return Response(serializer.data)
from django.db.models import Q,OuterRef,Subquery
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from accounts.models import CallQc
from cloud_telephony.utils import get_agent_id_by_user, get_company_from_agent_campaign, has_valid_recording
from follow_up.models import Appointment, Follow_Up
from follow_up.serializers import AppointmentSerializer, FollowUpSerializer
from lead_management.models import Lead
from orders.models import Order_Table
from django.core.files.base import ContentFile
from orders.serializers import OrderTableSerializer
from services.cloud_telephoney.cloud_telephoney_service import CloudConnectService, TataSmartfloService,SansSoftwareService
from superadmin_assets.models import Language
from .models import (
    CallActivity,
    CallLead,
    CallLog,
    CallRecording,
    CloudTelephonyVendor, 
    CloudTelephonyChannel, 
    CloudTelephonyChannelAssign,
    SecretKey, 
    UserMailSetup
)
from .serializers import (
    CallLeadSerializer,
    CallLogSerializer,
    CallRecordingInputSerializer,
    CallRecordingModelSerializer,
    CloudTelephonyChannelAssignBulkSerializer,
    CloudTelephonyChannelAssignCSVSerializer,
    CloudTelephonyVendorSerializer, 
    CloudTelephonyChannelSerializer, 
    CloudTelephonyChannelAssignSerializer,
    SecretKeySerializer, 
    UserMailSetupSerializer
)
from django.shortcuts import get_object_or_404
import requests
import csv
from io import TextIOWrapper
from django.db import transaction
from datetime import datetime, date as dt_date
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers, status, viewsets
from django.utils import timezone

class CloudTelephonyVendorViewSet(viewsets.ModelViewSet):
    queryset = CloudTelephonyVendor.objects.all()
    serializer_class = CloudTelephonyVendorSerializer
    permission_classes = [IsAuthenticated]

class CloudTelephonyChannelViewSet(viewsets.ModelViewSet):
    serializer_class = CloudTelephonyChannelSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return CloudTelephonyChannel.objects.filter(company=user.profile.company)

    def perform_create(self, serializer):
        user = self.request.user
        serializer.save(company=user.profile.company)


class CloudTelephonyChannelAssignViewSet(viewsets.ModelViewSet):
    serializer_class = CloudTelephonyChannelAssignSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        company = user.profile.company

        self_assign = self.request.query_params.get("self_assign")

        qs = CloudTelephonyChannelAssign.objects.filter(company=company)

        # If ?self_assign=true → only my channels
        if self_assign and self_assign.lower() == "true":
            qs = qs.filter(user=user)

        return qs

    def perform_create(self, serializer):
        company = self.request.user.profile.company
        try:
            serializer.save(company=company)
        except DjangoValidationError as e:
            # Extract and format error messages
            error_message = self._format_validation_error(e)
            raise serializers.ValidationError({"error": error_message})

    def perform_update(self, serializer):
        try:
            serializer.save()
        except DjangoValidationError as e:
            # Extract and format error messages
            error_message = self._format_validation_error(e)
            raise serializers.ValidationError({"error": error_message})

    def _format_validation_error(self, exception):
        """
        Convert Django ValidationError to clean error message
        """
        if hasattr(exception, 'message_dict'):
            # Collect all error messages from all fields
            messages = []
            for field, errors in exception.message_dict.items():
                if isinstance(errors, list):
                    messages.extend(errors)
                else:
                    messages.append(str(errors))
            # Join multiple messages with comma
            return ", ".join(messages)
        elif hasattr(exception, 'messages'):
            return ", ".join(exception.messages)
        else:
            return str(exception)

    # ✅ CUSTOM URL: /activate_monitoring/<id>/
    @action(detail=False, methods=["post"], url_path="activate_monitoring/(?P<id>[^/.]+)")
    def activate_monitoring(self, request, id=None):

        try:
            instance = CloudTelephonyChannelAssign.objects.get(id=id)
        except CloudTelephonyChannelAssign.DoesNotExist:
            return Response(
                {"error": "Invalid telephony id"},
                status=status.HTTP_404_NOT_FOUND
            )

        if instance.type != 2:
            return Response(
                {"error": "Only monitoring channels can be activated"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # security: same company only
        if instance.company != request.user.profile.company:
            return Response(
                {"error": "Not allowed"},
                status=status.HTTP_403_FORBIDDEN
            )

        # deactivate others
        CloudTelephonyChannelAssign.objects.filter(
            user=instance.user,
            company=instance.company,
            type=2
        ).update(is_active=False)

        # activate this
        instance.is_active = True
        try:
            instance.save()
        except DjangoValidationError as e:
            error_message = self._format_validation_error(e)
            return Response(
                {"error": error_message},
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response({
            "message": "Monitoring channel activated successfully",
            "active_id": instance.id
        })


class UserMailSetupViewSet(viewsets.ModelViewSet):
    queryset = UserMailSetup.objects.all()
    serializer_class = UserMailSetupSerializer
    
class CallServiceViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['post'], url_path='quick-call')
    def quick_call(self, request):
        # cloud_channel_id = request.data.get('cloud_channel_id')
        lead_id = request.data.get("lead_id")
        order_id = request.data.get("order_id")
        followup_id = request.data.get("followup_id")
        appointment_id = request.data.get("appointment_id")

        user = self.request.user  # Proper user instance
        try:
            channel_assign = CloudTelephonyChannelAssign.objects.get(user_id=user.id,is_active=True)
        except CloudTelephonyChannelAssign.DoesNotExist:
            return Response({"error": "No channel assigned to user for this telephony channel."}, status=status.HTTP_404_NOT_FOUND)

        # Validate cloud channel
        cloud_channel_id = channel_assign.cloud_telephony_channel.id
        try:
            channel = CloudTelephonyChannel.objects.get(id=cloud_channel_id)
        except CloudTelephonyChannel.DoesNotExist:
            return Response({"error": "Invalid CloudTelephonyChannel ID."}, status=status.HTTP_404_NOT_FOUND)
        
        # Get assigned channel config for user
      
        try:
            channel_assign = CloudTelephonyChannelAssign.objects.get(user_id=user.id, cloud_telephony_channel_id=cloud_channel_id,is_active=True)
        except CloudTelephonyChannelAssign.DoesNotExist:
            return Response({"error": "No channel assigned to user for this telephony channel."}, status=status.HTTP_404_NOT_FOUND)
  
        # Get phone number from source
        phone_number = None

        if lead_id:
            try:
                lead = (Lead.objects.filter(Q(lead_id=lead_id) | Q(id=lead_id)).only("customer_phone").first())
                if not lead:
                    return Response({"error": "lead_id parameter is required"}, status=status.HTTP_400_BAD_REQUEST) 
                phone_number = lead.customer_phone
            except Lead.DoesNotExist:
                return Response({"error": "Lead not found."}, status=status.HTTP_404_NOT_FOUND)
        elif order_id:
            try:
                phone_number = Order_Table.objects.get(order_id=order_id).customer_phone
            except Order_Table.DoesNotExist:
                return Response({"error": "Order not found."}, status=status.HTTP_404_NOT_FOUND)
        elif followup_id:
            try:
                phone_number = Follow_Up.objects.get(followup_id=followup_id).customer_phone
            except Follow_Up.DoesNotExist:
                return Response({"error": "Follow-up not found."}, status=status.HTTP_404_NOT_FOUND)
        elif appointment_id:
            try:
                from follow_up.models import Appointment
                phone_number = Appointment.objects.get(id=appointment_id).patient_phone
            except Appointment.DoesNotExist:
                return Response({"error": "Appointment not found."}, status=status.HTTP_404_NOT_FOUND)
        else:
            return Response({"error": "Provide either lead_id, order_id,appointment_id, or followup_id."}, status=status.HTTP_400_BAD_REQUEST)

        if not phone_number:
            return Response({"error": "Phone number is missing."}, status=status.HTTP_400_BAD_REQUEST)

        # Channel details
        cloud_vendor = channel.cloudtelephony_vendor.name.lower()
        response_data = {}

        if cloud_vendor == 'cloud connect':
            token = channel.token
            tenant_id = channel.tenent_id
            if not token or not tenant_id:
                return Response({"error": "token and tenant_id required for CloudConnect."}, status=status.HTTP_400_BAD_REQUEST)
            
            cloud_connect_service = CloudConnectService(token, tenant_id)
            session_response = cloud_connect_service.get_session_id(channel_assign.agent_id)
       
            if session_response.get("code") != 200 or "session_id" not in session_response:
                return Response({"error": "Failed to get session ID from CloudConnect."}, status=status.HTTP_400_BAD_REQUEST)
            session_id = session_response["session_id"]
            print(session_id,"--------------340")
            response_data = cloud_connect_service.manual_call_originate(
                channel_assign.agent_id,
                session_id,
                phone_number,
                channel_assign.camp_id
            )
            print(response_data,"--------------356")
        elif cloud_vendor == 'tatasmartflo':
            api_key = request.data.get('api_key')
            if not api_key:
                return Response({"error": "api_key required for TataSmartflo."}, status=status.HTTP_400_BAD_REQUEST)

            tata_smartflo_service = TataSmartfloService(api_key)
            response_data = tata_smartflo_service.initiate_click_to_call(
                request.data.get('agent_number', ''),
                phone_number,
                request.data.get('caller_id', '')
            )
        
    # ============ SANSOFTWARES ============
        elif cloud_vendor == 'sansoftwares':
            # Assuming you store Sanssoftwares process_id in channel.tenent_id
            process_id = channel.tenent_id
            if not process_id:
                return Response(
                    {"error": "process_id (stored in tenant_id) is required for Sanssoftwares."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            sans_service = SansSoftwareService(process_id=process_id)

            # Use assigned agent username as Sanssoft 'agent_name'
            agent_name = channel_assign.agent_username or user.username
            if not agent_name:
                return Response(
                    {"error": "agent_username is required for Sanssoftwares click-to-call."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            response_data = sans_service.click_to_call(
                agent_name=agent_name,
                dialed_number=str(phone_number)[-10:]
            )
            print(response_data,"--------------379")
        else:
            return Response(
                {"error": f"{cloud_vendor} is not supported."},
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response({"success": True, "response": response_data}, status=status.HTTP_200_OK)


    # @action(detail=False, methods=['get'], url_path='get-number')
    # def get_number(self, request):
    #     call_id = request.query_params.get("call_id")
    #     if not call_id:
    #         return Response({"error": "call_id is required."}, status=status.HTTP_400_BAD_REQUEST)

    #     user = request.user
    #     try:
    #         channel_assign = CloudTelephonyChannelAssign.objects.get(user_id=user.id)
    #         channel = channel_assign.cloud_telephony_channel
    #     except CloudTelephonyChannelAssign.DoesNotExist:
    #         return Response({"error": "No channel assigned to this user."}, status=status.HTTP_404_NOT_FOUND)

    #     cloud_vendor = channel.cloudtelephony_vendor.name.lower()

    #     if cloud_vendor == 'cloudconnect':
    #         if not channel.token or not channel.tenent_id:
    #             return Response({"error": "token and tenant_id required for CloudConnect."}, status=status.HTTP_400_BAD_REQUEST)

    #         cloud_connect_service = CloudConnectService(channel.token, channel.tenent_id)
    #         details_response = cloud_connect_service.call_details(call_id)

    #         if details_response.get("code") != 200:
    #             return Response({"error": "Failed to retrieve call details."}, status=status.HTTP_400_BAD_REQUEST)

    #         result = details_response.get("result", {})
    #         return Response({
    #             "success": True,
    #             "phone_number": result.get("phone_number"),
    #             "message": details_response.get("status_message")
    #         }, status=status.HTTP_200_OK)

    #     return Response({"error": f"{cloud_vendor} is not supported."}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'], url_path='get-call-recording')
    def get_call_recording(self, request):
        call_id = request.query_params.get("call_id")
        phone_number = request.query_params.get("phone_number")
        agent_id = request.query_params.get("agent_id")
        date = request.query_params.get("date")

        if not call_id and not phone_number and not agent_id and not date:
            return Response({"error": "call_id or phone_number date is required."}, status=status.HTTP_400_BAD_REQUEST)

        user = request.user
        try:
            channel_assign = CloudTelephonyChannelAssign.objects.get(user_id=user.id,is_active=True)
            channel = channel_assign.cloud_telephony_channel
        except CloudTelephonyChannelAssign.DoesNotExist:
            return Response({"error": "No channel assigned to this user."}, status=status.HTTP_404_NOT_FOUND)
        cloud_vendor = channel.cloudtelephony_vendor.name.lower()
        if cloud_vendor == 'cloud connect':
            if not channel.token or not channel.tenent_id:
                return Response({"error": "token and tenant_id required for CloudConnect."}, status=status.HTTP_400_BAD_REQUEST)

            cloud_connect_service = CloudConnectService(channel.token, channel.tenent_id)
            if call_id:
                details_response = cloud_connect_service.get_recording_details(call_id)
                if details_response.get("code") != 200:
                    return Response({"error": "Failed to retrieve call recording."}, status=status.HTTP_400_BAD_REQUEST)
            
                result = details_response if details_response else {}
                return Response({
                    "success": True,
                    # "phone_number": result.get("phone_number"),
                    "data":[{"file_path":result.get('file_path'),"call_id":call_id}],
                    # "file_path":result.get('file_path'),
                    "message": details_response.get("status_message")
                }, status=status.HTTP_200_OK)
            elif date:
                details_response = cloud_connect_service.get_call_details(date, phone_number)
                if details_response.get("code") != 200:
                    return Response({"error": "Failed to retrieve call recording."}, status=status.HTTP_400_BAD_REQUEST)
               
                data = details_response.get("result", {})
                
                calls = []

                # Loop over all keys that are digits (i.e., actual call entries)
                for key, value in data.items():
                    if key.isdigit():
                        value['file_path'] = value.get("recording_path")
                        calls.append(value)

                return Response({
                    "success": True,
                    "data": calls,
                    "message": details_response.get("message", "Call details retrieved successfully.")
                }, status=status.HTTP_200_OK)
        # ============ SANSOFTWARES ============
        elif cloud_vendor == 'sansoftwares':
            # Sanssoft docs only show phone_number + process_id (no date),
            # so we will primarily use phone_number here.
            process_id = channel.tenent_id
            if not process_id:
                return Response(
                    {"error": "process_id (stored in tenant_id) is required for Sanssoftwares."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # if not phone_number:
            #     return Response(
            #         {"error": "phone_number is required for Sanssoftwares call details."},
            #         status=status.HTTP_400_BAD_REQUEST
            #     )

            sans_service = SansSoftwareService(process_id=process_id)
            if call_id:
                details_response = sans_service.get_number(call_id)
                print(details_response,"-------------------509")
                
                if not details_response.get("success"):
                    return Response(
                        {"error": "Failed to retrieve call details."},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                result = details_response.get("result", [])

                # ✅ Safely extract phone number
                phone_number = None
                if result and isinstance(result, list):
                    phone_number = result[0].get("Phone_number")

            if date:
                start_date = end_date = datetime.strptime(date, "%Y-%m-%d").date()
            else:
                today = dt_date.today()
                start_date = today.replace(day=1)
                end_date = today

            response_data = sans_service.get_all_call_log_detail(
                phone_number,
                start_date,
                end_date
            )  
            # response_data = sans_service.get_all_call_log_detail(phone_number,date,date)
            print(response_data,"--------------511")
            if not response_data:
                return Response(
                    {"error": "Failed to retrieve call details from Sanssoftwares."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            # if response_data.get("code") != 200:
            #         return Response({"error": "Failed to retrieve call recording."}, status=status.HTTP_400_BAD_REQUEST)
               
            data = response_data.get("result", {})
            print(data,"--------------------------521")
            calls = []

            # Loop over all keys that are digits (i.e., actual call entries)
            for value in data:
                # if key.isdigit():
                value['file_path'] = value.get("reco_file")
                value['call_start_time'] = value.get('start_time')
                value['agent_username'] = value.get('agent_name')
                value['campaign_name'] = value.get('campaign')
                value['phone_number'] = value.get('log_phone_no')
                calls.append(value)
            # print(calles)
            return Response({
                "success": True,
                "data": calls,
                "message": response_data.get("message", "Call details retrieved successfully.")
            }, status=status.HTTP_200_OK)
            return Response({
                "success": True,
                "data": response_data,
                "message": response_data.get("message", "Call details retrieved successfully.")
            }, status=status.HTTP_200_OK)
   

        return Response({"error": f"{cloud_vendor} is not supported."}, status=status.HTTP_400_BAD_REQUEST)
    

    @action(detail=False, methods=['get'], url_path='get-call-details')
    def get_call_details(self, request):
        phone_number = request.query_params.get("phone_number")
        agent_id = request.query_params.get("agent_id")
        date = request.query_params.get("date")

        if not date:
            return Response({
                "error": "Missing required parameters: 'date' is required."
            }, status=status.HTTP_400_BAD_REQUEST)

        user = request.user
        company = user.profile.company 
        try:
            channel_assign = CloudTelephonyChannelAssign.objects.get(user_id=user.id,is_active=True)
            channel = channel_assign.cloud_telephony_channel
        except CloudTelephonyChannelAssign.DoesNotExist:
            return Response(
                {"error": "No channel assigned to this user."},
                status=status.HTTP_404_NOT_FOUND
            )

        cloud_vendor = channel.cloudtelephony_vendor.name.lower()

        # ============ CLOUD CONNECT ============
        if cloud_vendor == 'cloud connect':
            if not channel.token or not channel.tenent_id:
                return Response(
                    {"error": "token and tenant_id required for CloudConnect."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            cloud_connect_service = CloudConnectService(channel.token, channel.tenent_id)
            response_data = cloud_connect_service.get_call_details(date, phone_number)
            qc_call_ids = set(
                CallQc.objects.filter(company=company)
                .values_list("call_id", flat=True)
            )
            print(qc_call_ids,"---------------------710")
            data = response_data.get("result", {})
            print(data,"---------------------705")
            qc_call_ids = set(
            CallQc.objects.filter(company=company)
            .values_list("call_id", flat=True)
                    )

            calls = []

            for key, value in data.items():
                if key.isdigit():
                    call_id = value.get("call_id")
                    recording_path = value.get("recording_path")
                    if has_valid_recording(recording_path):
                        print("-----732---has recording---")
                        value["recording_path"] = recording_path

                        # Recording exists?
                        value["has_recording"] = has_valid_recording(recording_path)

                        # QC done?
                        value["call_qc"] = call_id in qc_call_ids

                        calls.append(value)
            print(calls,"---------------------725")
            return Response({
                "success": True,
                "data": calls,
                "message": response_data.get("status_message", "Call details retrieved successfully.")
            }, status=status.HTTP_200_OK)
            if response_data.get("code") != 200:
                return Response(
                    {"error": "Failed to retrieve call details."},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
            return Response({
                "success": True,
                "data": response_data.get("result", {}),
                "message": response_data.get("status_message")
            }, status=status.HTTP_200_OK)

        # ============ SANSOFTWARES ============
        elif cloud_vendor == 'sansoftwares':
            # Sanssoft docs only show phone_number + process_id (no date),
            # so we will primarily use phone_number here.
            process_id = channel.tenent_id
            if not process_id:
                return Response(
                    {"error": "process_id (stored in tenant_id) is required for Sanssoftwares."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if not phone_number:
                return Response(
                    {"error": "phone_number is required for Sanssoftwares call details."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            sans_service = SansSoftwareService(process_id=process_id)
            response_data = sans_service.get_all_call_log_detail(phone_number,date,date)

            if not response_data:
                return Response(
                    {"error": "Failed to retrieve call details from Sanssoftwares."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            if response_data.get("code") != 200:
                    return Response({"error": "Failed to retrieve call recording."}, status=status.HTTP_400_BAD_REQUEST)
               
            data = response_data.get("result", {})
            
            calls = []

            # Loop over all keys that are digits (i.e., actual call entries)
            for key, value in data.items():
                if key.isdigit():
                    value['file_path'] = value.get("reco_file")
                    calls.append(value)

            return Response({
                "success": True,
                "data": calls,
                "message": response_data.get("message", "Call details retrieved successfully.")
            }, status=status.HTTP_200_OK)
            # return Response({
            #     "success": True,
            #     "data": response_data,
            #     "message": response_data.get("message", "Call details retrieved successfully.")
            # }, status=status.HTTP_200_OK)

        return Response(
            {"error": f"{cloud_vendor} is not supported."},
            status=status.HTTP_400_BAD_REQUEST
        )
    @action(detail=False, methods=['post'], url_path='create-session')
    def create_session(self, request):
        

        agent_id = request.data.get("agent_id")
      

        user = request.user
        

        # ================== CHANNEL ASSIGNMENT ==================
        try:
           
            channel_assign = CloudTelephonyChannelAssign.objects.get(user_id=user.id,is_active=True)
            channel = channel_assign.cloud_telephony_channel

            

        except CloudTelephonyChannelAssign.DoesNotExist:
          
            return Response(
                {"error": "No channel assigned to this user."},
                status=status.HTTP_404_NOT_FOUND
            )

        # ================== CHANNEL DETAILS ==================
       
        # ================== VENDOR ==================
        cloud_vendor = channel.cloudtelephony_vendor.name.strip().lower()
       
        # ================== CLOUD CONNECT ==================
        if cloud_vendor == 'cloud connect':
            if not channel.token or not channel.tenent_id:  
                return Response(
                    {"error": "token and tenant_id required for CloudConnect."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            # Prefer agent_id from assignment
            agent_id = agent_id or channel_assign.agent_id
            if not agent_id:
                return Response(
                    {"error": "agent_id is required."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            agent_username = channel_assign.agent_username
            camp_id = channel_assign.camp_id
            agent_password = channel_assign.agent_password
            other = channel_assign.other
            campangin_name = channel_assign.campangin_name
            

            cloud_connect_service = CloudConnectService(
                channel.token,
                channel.tenent_id
            )

            # ================== CLOUD API CALL ==================
            try:
                

                response_data = cloud_connect_service.create_session(agent_id,agent_username,agent_password,camp_id,other,campangin_name)

                
            except Exception as e:
                
                return Response(
                    {"error": str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # ================== SUCCESS RESPONSE ==================
           
            return Response(
                {
                    "success": True,
                    "session_id": response_data.get("session_id"),
                    "message": response_data.get("status_message"),
                },
                status=status.HTTP_200_OK
            )

        # ================== UNSUPPORTED VENDOR ==================
        
        return Response(
            {
                "error": f"Cloud vendor '{cloud_vendor}' is not supported yet."
            },
            status=status.HTTP_400_BAD_REQUEST
        )
    

    @action(detail=False, methods=['post'], url_path='get-session-id')
    def get_session_id(self, request):
        """
        Legacy session API (optional)
        """

        agent_id = request.data.get("agent_id")

        user = request.user

        # ================== CHANNEL ASSIGNMENT ==================
        try:
            channel_assign = CloudTelephonyChannelAssign.objects.get(user_id=user.id,is_active=True)
            channel = channel_assign.cloud_telephony_channel
        except CloudTelephonyChannelAssign.DoesNotExist:
            return Response(
                {"error": "No channel assigned to this user."},
                status=status.HTTP_404_NOT_FOUND
            )

        # ================== VENDOR ==================
        cloud_vendor = channel.cloudtelephony_vendor.name.strip().lower()

        # ================== CLOUD CONNECT ==================
        if cloud_vendor == 'cloud connect':

            agent_id = agent_id or channel_assign.agent_id

            if not agent_id:
                return Response(
                    {"error": "agent_id is required."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            cloud_connect_service = CloudConnectService(
                channel.token,
                channel.tenent_id
            )

            try:
                response_data = cloud_connect_service.get_session_id(agent_id)
            except Exception as e:
                return Response(
                    {"error": str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )

            return Response(
                {
                    "success": True,
                    "session_id": response_data.get("session_id"),
                    "message": response_data.get("status_message"),
                },
                status=status.HTTP_200_OK
            )

        # ================== UNSUPPORTED VENDOR ==================
        return Response(
            {
                "error": f"Cloud vendor '{cloud_vendor}' is not supported yet."
            },
            status=status.HTTP_400_BAD_REQUEST
        )
    @action(detail=False, methods=['get'], url_path='agent-current-status')
    def agent_current_status(self, request):

        # ================== QUERY PARAMS ==================
        agent_id = request.query_params.get("agent_id")
        agent_uname = request.query_params.get("agent_uname")
        queue_id = request.query_params.get("queue_id")
        status_param = request.query_params.get("status")

        user = request.user

        # ================== CHANNEL ASSIGNMENT ==================
        try:
            channel_assign = CloudTelephonyChannelAssign.objects.get(user_id=user.id,is_active=True)
            channel = channel_assign.cloud_telephony_channel
        except CloudTelephonyChannelAssign.DoesNotExist:
            return Response(
                {"error": "No channel assigned to this user."},
                status=status.HTTP_404_NOT_FOUND
            )

        # ================== VENDOR ==================
        cloud_vendor = channel.cloudtelephony_vendor.name.strip().lower()

        # ================== CLOUD CONNECT ==================
        if cloud_vendor == 'cloud connect':

            if not channel.token or not channel.tenent_id:
                return Response(
                    {"error": "token and tenant_id required for CloudConnect."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Prefer assignment values if not provided in query
            agent_id = agent_id 
            agent_uname = agent_uname 
            queue_id = queue_id 
            if not agent_id:
                return Response(
                    {"error": "agent_id is required."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            cloud_connect_service = CloudConnectService(
                channel.token,
                channel.tenent_id
            )

            # ================== CLOUD API CALL ==================
            try:
                response_data = cloud_connect_service.agent_current_status(
                    agent_id=agent_id,
                    agent_uname=agent_uname,
                    queue_id=queue_id,
                    status=status_param
                )
            except Exception as e:
                return Response(
                    {"error": str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # ================== SUCCESS RESPONSE ==================
            return Response(
                {
                    "success": True,
                    "data": response_data
                },
                status=status.HTTP_200_OK
            )

        # ================== UNSUPPORTED VENDOR ==================
        return Response(
            {
                "error": f"Cloud vendor '{cloud_vendor}' is not supported yet."
            },
            status=status.HTTP_400_BAD_REQUEST
        )
    
    @action(detail=False, methods=['get'], url_path='active-call')
    def active_call(self, request):

        user = request.user

        # ================== CHANNEL ASSIGNMENT ==================
        try:
            channel_assign = CloudTelephonyChannelAssign.objects.get(user_id=user.id,is_active=True)
            channel = channel_assign.cloud_telephony_channel
        except CloudTelephonyChannelAssign.DoesNotExist:
            return Response(
                {"error": "No channel assigned to this user."},
                status=status.HTTP_404_NOT_FOUND
            )

        # ================== VENDOR ==================
        cloud_vendor = channel.cloudtelephony_vendor.name.strip().lower()

        # ================== CLOUD CONNECT ==================
        if cloud_vendor == 'cloud connect':

            if not channel.token or not channel.tenent_id:
                return Response(
                    {"error": "token and tenant_id required for CloudConnect."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            cloud_connect_service = CloudConnectService(
                channel.token,
                channel.tenent_id
            )

            # ================== CLOUD API CALL ==================
            try:
                response_data = cloud_connect_service.get_active_Call()
            except Exception as e:
                return Response(
                    {"error": str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # ================== SUCCESS RESPONSE ==================
            return Response(
                {
                    "success": True,
                    "data": response_data
                },
                status=status.HTTP_200_OK
            )

        # ================== UNSUPPORTED VENDOR ==================
        return Response(
            {
                "error": f"Cloud vendor '{cloud_vendor}' is not supported yet."
            },
            status=status.HTTP_400_BAD_REQUEST
        )
from rest_framework.views import APIView
class GetNumberAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        call_id = request.query_params.get("call_id")
        if not call_id:
            return Response({"error": "call_id is required."}, status=status.HTTP_400_BAD_REQUEST)

        user = request.user
        try:
            channel_assign = CloudTelephonyChannelAssign.objects.get(user_id=user.id,is_active=True)
            channel = channel_assign.cloud_telephony_channel
        except CloudTelephonyChannelAssign.DoesNotExist:
            return Response({"error": "No channel assigned to this user."}, status=status.HTTP_404_NOT_FOUND)

        cloud_vendor = channel.cloudtelephony_vendor.name.lower()

        if cloud_vendor == 'cloud connect':
            if not channel.token or not channel.tenent_id:
                return Response({"error": "token and tenant_id required for CloudConnect."}, status=status.HTTP_400_BAD_REQUEST)

            cloud_connect_service = CloudConnectService(channel.token, channel.tenent_id)
            details_response = cloud_connect_service.call_details(call_id)

            if details_response.get("code") != 200:
                return Response({"error": "Failed to retrieve call details."}, status=status.HTTP_400_BAD_REQUEST)

            result = details_response.get("result", {})
            return Response({
                "success": True,
                "phone_number": result.get("phone_number")[-10:],
                "message": details_response.get("status_message")
            }, status=status.HTTP_200_OK)
        elif cloud_vendor == 'sansoftwares':
            process_id = channel.tenent_id

            if not process_id:
                return Response(
                    {"error": "process_id (stored in tenant_id) is required for Sanssoftwares."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if not call_id:
                return Response(
                    {"error": "call_id is required for Sanssoftware."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            sans_service = SansSoftwareService(process_id=process_id)
            details_response = sans_service.get_number(call_id)

            if not details_response.get("success"):
                return Response(
                    {
                        "error": "Failed to retrieve call details.",
                        "vendor_response": details_response
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            result = details_response.get("result", [])

            phone_number = None
            if isinstance(result, list) and len(result) > 0:
                phone_number = result[0].get("Phone_number")

            if not phone_number:
                return Response(
                    {
                        "error": "Phone number not found",
                        "vendor_response": details_response
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            return Response(
                {
                    "success": True,
                    "phone_number": phone_number[-10:],
                    "message": details_response.get("message")
                },
                status=status.HTTP_200_OK
            )

        return Response(
            {"error": f"{cloud_vendor} is not supported."},
            status=status.HTTP_400_BAD_REQUEST
        )
    

class SaveCallRecordingAPIView(APIView):
    def post(self, request):
        # Validate Request Body
        serializer = CallRecordingInputSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        secret_key = serializer.validated_data["secret_key"]
        recording_url = serializer.validated_data["recording_url"]
        agent_username = serializer.validated_data["agent_username"]
        call_datetime = serializer.validated_data["datetime"]
        duration = serializer.validated_data["duration"]
        number = serializer.validated_data["number"]

        # 1️⃣ VALIDATE SECRET KEY
        try:
            key_obj = SecretKey.objects.select_related("cloudtelephony_vendor").get(
                secret_key=secret_key,
                is_active=True
            )
            vendor = key_obj.cloudtelephony_vendor
        except SecretKey.DoesNotExist:
            return Response({"error": "Invalid or inactive secret key"}, status=401)

        # 2️⃣ Find agent → user → company → branch for this vendor
        try:
            assign = CloudTelephonyChannelAssign.objects.select_related(
                "user", "company", "branch"
            ).get(agent_username=agent_username, vendor=vendor)
        except CloudTelephonyChannelAssign.DoesNotExist:
            return Response({"error": "Agent not found for this vendor"}, status=404)

        user = assign.user
        company = assign.company
        branch = assign.branch

        # 3️⃣ Download recording file
        try:
            file_response = requests.get(recording_url)
            if file_response.status_code != 200:
                return Response({"error": "Failed to download recording"}, status=400)
        except Exception as e:
            return Response({"error": str(e)}, status=400)

        # 4️⃣ Prepare filename
        filename = f"{agent_username}_{number}_{int(call_datetime.timestamp())}.mp3"

        # 5️⃣ Save Recording Model
        recording_obj = CallRecording(
            user=user,
            company=company,
            branch=branch,
            agent_username=agent_username,
            number=number,
            duration=duration,
            call_datetime=call_datetime,
            recording_original_url=recording_url
        )

        recording_obj.recording_file.save(
            filename,
            ContentFile(file_response.content)
        )
        recording_obj.save()

        # 6️⃣ Return response
        output = CallRecordingModelSerializer(recording_obj).data

        return Response({
            "message": "Recording saved successfully",
            "data": output
        }, status=status.HTTP_201_CREATED)




class SecretKeyViewSet(viewsets.ModelViewSet):
    queryset = SecretKey.objects.select_related("cloudtelephony_vendor").all()
    serializer_class = SecretKeySerializer
    permission_classes = [IsAuthenticated]
    # Auto-generate secret key in serializer.save()
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        vendor_id = serializer.validated_data["cloudtelephony_vendor"].id

        # Create a new record → secret key auto-generates in model.save()
        secret_key_obj = SecretKey.objects.create(
            cloudtelephony_vendor_id=vendor_id
        )

        return Response(
            SecretKeySerializer(secret_key_obj).data,
            status=status.HTTP_201_CREATED
        )

    # Custom action to activate key
    @action(detail=True, methods=["post"])
    def activate(self, request, pk=None):
        key_obj = self.get_object()
        key_obj.is_active = True
        key_obj.deactivated_at = None
        key_obj.save()

        return Response({"message": "Key activated successfully"})

    # Custom action to deactivate key
    @action(detail=True, methods=["post"])
    def deactivate(self, request, pk=None):
        key_obj = self.get_object()
        key_obj.is_active = False
        key_obj.deactivated_at = timezone.now()
        key_obj.save()

        return Response({"message": "Key deactivated successfully"})
    

class CloudTelephonyChannelAssignCSVUploadAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        company = request.user.profile.company

        serializer = CloudTelephonyChannelAssignBulkSerializer(
            data={"items": request.data},
            context={"request": request}
        )
        serializer.is_valid(raise_exception=True)

        success = []
        failed = []

        for index, item in enumerate(serializer.validated_data["items"], start=1):
            try:
                user = item.get("user")

                instance = CloudTelephonyChannelAssign.objects.filter(
                    user=user,
                    company=company
                ).first()

                if instance:
                    # 🔁 update only provided fields
                    for field, value in item.items():
                        if value is not None:
                            setattr(instance, field, value)
                    instance.save()
                    success.append(
                        {"row": index, "status": "updated", "id": instance.id}
                    )
                else:
                    obj = CloudTelephonyChannelAssign.objects.create(
                        company=company,
                        **item
                    )
                    success.append(
                        {"row": index, "status": "created", "id": obj.id}
                    )

            except Exception as e:
                failed.append(
                    {
                        "row": index,
                        "error": str(e),
                        "data": item
                    }
                )

        return Response(
            {
                "success": True,
                "summary": {
                    "total": len(request.data),
                    "created_or_updated": len(success),
                    "failed": len(failed),
                },
                "success_rows": success,
                "failed_rows": failed
            },
            status=status.HTTP_200_OK
        )



from rest_framework import status as drf_status
from django.utils.timezone import now
from rest_framework.permissions import AllowAny
class CloudConnectWebhookAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        data = request.data

        call_id = data.get("callid")
        status_value = data.get("status")
        phone = data.get("callernumber")

        agent_id = data.get("agent_id")
        campaign_id = data.get("campaignId")

        if not call_id or not status_value or not phone:
            return Response(
                {"error": "Missing required fields"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 🔥 Resolve company
        company = get_company_from_agent_campaign(agent_id)
        print(company,"-------------------company")
        call_log, created = CallLog.objects.update_or_create(
            call_id=call_id,
            defaults={
                "call_uuid": data.get("call_uuid"),
                "phone": phone,
                "agent_id": agent_id,
                "status": status_value,
                "direction": data.get("call_direction"),
                "campaign_id": campaign_id,
                "company": company,   # ✅ auto mapped
                "session_id": data.get("sessionId"),
                "transfer_id": data.get("transfer_id"),
                "job_id": data.get("job_id"),
                "hangup_reason": data.get("reason"),
                "raw_payload": data,
                "updated_at": now(),
            }
        )

        return Response(
            {
                "received": True,
                "call_id": call_id,
                "status": status_value,
                "company_id": company.id if company else None,
                "created": created
            },
            status=status.HTTP_200_OK
        )


class CustomerDataByMobileAPI(APIView):
    """
    Get all related data by mobile number
    """ 
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        company = user.profile.company
        mobile = request.query_params.get("mobile")

        if not mobile:
            return Response(
                {"error": "mobile number is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        last10 = mobile[-10:]

        orders = Order_Table.objects.filter(
            customer_phone__endswith=last10,
            company=company,
            is_deleted=False
        )

        calls = CallLog.objects.filter(
            phone__endswith=last10,
            company=company
        )

        # Appointments
        appointments = Appointment.objects.filter(
            company=company,
            patient_phone__endswith=last10
        )

        # Follow Ups
        followups = Follow_Up.objects.filter(
            company=company,
            customer_phone__endswith=last10
        )

        response_data = {
            "mobile": mobile,
            "orders": OrderTableSerializer(orders, many=True).data,
            "calls": CallLogSerializer(calls, many=True).data,
            "appointments": AppointmentSerializer(appointments, many=True).data,
            "followups": FollowUpSerializer(followups, many=True).data,
        }

        return Response(response_data, status=status.HTTP_200_OK)
    
class CallActivityCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        company = request.user.profile.company

        phone = request.data["phone"]
        call_log_id = request.data["call_log_id"]

        name = request.data.get("name")
        address = request.data.get("address")  # ✅ NEW
        language_id = request.data.get("language")  # ✅ NEW (id)

        call_log = get_object_or_404(CallLog, call_id=call_log_id)

        language = None
        if language_id:
            language = Language.objects.filter(id=language_id).first()

        lead, created = CallLead.objects.get_or_create(
            phone=phone,
            company=company,
            defaults={
                "created_by": request.user,
                "name": name,
                "address": address,
                "language": language
            }
        )

        # 🔁 Update fields if lead already exists
        update_fields = []

        if name:
            lead.name = name
            update_fields.append("name")

        if address:
            lead.address = address
            update_fields.append("address")

        if language:
            lead.language = language
            update_fields.append("language")

        if update_fields:
            lead.save(update_fields=update_fields)

        activity = CallActivity.objects.create(
            lead=lead,
            call_log=call_log,
            company=company,
            activity_type=request.data.get("activity_type"),
            status=request.data["status"],
            remark=request.data["remark"],
            next_followup=request.data.get("next_followup"),
            updated_by=request.user
        )

        # snapshot
        lead.last_call = call_log
        lead.last_status = activity.status
        lead.last_remark = activity.remark
        lead.save(update_fields=["last_call", "last_status", "last_remark"])

        return Response({
            "success": True,
            "created": created,
            "lead_id": lead.id,
            "activity_id": activity.id
        })

class CallLeadDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, phone):
        company = request.user.profile.company

        lead = CallLead.objects.filter(
            phone=phone,
            company=company
        ).first()

        if not lead:
            return Response({"new_number": True})

        serializer = CallLeadSerializer(lead)
        return Response(serializer.data)

class TodayFollowupAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        today = timezone.now().date()
        company = request.user.profile.company

        qs = CallActivity.objects.filter(
            company=company,
            next_followup__date=today
        ).select_related("lead", "updated_by")

        data = [
            {
                "phone": a.lead.phone,
                "status": a.status,
                "remark": a.remark,
                "time": a.next_followup,
                "agent": a.updated_by.username if a.updated_by else None
            }
            for a in qs
        ]

        return Response(data)
from rest_framework.generics import ListAPIView
class CallLogListAPIView(ListAPIView):
    serializer_class = CallLogSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        company = user.profile.company

        agent_param = self.request.query_params.get("agent_id")
        status_param = self.request.query_params.get("status")
        session_id = self.request.query_params.get("session_id")
        campaign_id = self.request.query_params.get("campaign_id")

        # 🔹 Base queryset → company level security
        queryset = CallLog.objects.filter(company=company)

        # 🔹 Agent filter (only if provided)
        if agent_param:
            agent_id = get_agent_id_by_user(agent_param)
            if not agent_id:
                return CallLog.objects.none()
            queryset = queryset.filter(agent_id=agent_id)

        # 🔹 Other filters (optional)
        if campaign_id:
            queryset = queryset.filter(campaign_id=campaign_id)

        if status_param:
            queryset = queryset.filter(status__icontains=status_param)

        if session_id:
            queryset = queryset.filter(session_id__icontains=session_id)

        return queryset.order_by("-created_at")
