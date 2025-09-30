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

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from follow_up.models import Follow_Up
from lead_management.models import Lead
from orders.models import Order_Table
from services.cloud_telephoney.cloud_telephoney_service import CloudConnectService, TataSmartfloService
from .models import (
    CloudTelephonyVendor, 
    CloudTelephonyChannel, 
    CloudTelephonyChannelAssign, 
    UserMailSetup
)
from .serializers import (
    CloudTelephonyVendorSerializer, 
    CloudTelephonyChannelSerializer, 
    CloudTelephonyChannelAssignSerializer, 
    UserMailSetupSerializer
)

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
        return CloudTelephonyChannelAssign.objects.filter(company=user.profile.company)

    def perform_create(self, serializer):
        user = self.request.user
        company = user.profile.company
        target_user = serializer.validated_data.get('user')
        channel = serializer.validated_data.get('cloud_telephony_channel')

        # Check if a record exists for this user
        try:
            existing_assignment = CloudTelephonyChannelAssign.objects.get(
                user=target_user, company=company
            )
            # Update existing record
            serializer.instance = existing_assignment
            serializer.save()
        except CloudTelephonyChannelAssign.DoesNotExist:
            # Create new assignment
            serializer.save(company=company)


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

        user = self.request.user  # Proper user instance
        try:
            channel_assign = CloudTelephonyChannelAssign.objects.get(user_id=user.id)
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
            channel_assign = CloudTelephonyChannelAssign.objects.get(user_id=user.id, cloud_telephony_channel_id=cloud_channel_id)
        except CloudTelephonyChannelAssign.DoesNotExist:
            return Response({"error": "No channel assigned to user for this telephony channel."}, status=status.HTTP_404_NOT_FOUND)
  
        # Get phone number from source
        phone_number = None

        if lead_id:
            try:
                phone_number = Lead.objects.get(id=lead_id).customer_phone
            except Lead.DoesNotExist:
                return Response({"error": "Lead not found."}, status=status.HTTP_404_NOT_FOUND)
        elif order_id:
            try:
                phone_number = Order_Table.objects.get(id=order_id).customer_phone
            except Order_Table.DoesNotExist:
                return Response({"error": "Order not found."}, status=status.HTTP_404_NOT_FOUND)
        elif followup_id:
            try:
                phone_number = Follow_Up.objects.get(id=followup_id).customer_phone
            except Follow_Up.DoesNotExist:
                return Response({"error": "Follow-up not found."}, status=status.HTTP_404_NOT_FOUND)
        else:
            return Response({"error": "Provide either lead_id, order_id, or followup_id."}, status=status.HTTP_400_BAD_REQUEST)

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

            response_data = cloud_connect_service.manual_call_originate(
                channel_assign.agent_id,
                session_id,
                phone_number,
                channel_assign.camp_id
            )

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
        else:
            return Response({"error": f"{cloud_vendor} is not supported."}, status=status.HTTP_400_BAD_REQUEST)

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
            channel_assign = CloudTelephonyChannelAssign.objects.get(user_id=user.id)
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
            

        return Response({"error": f"{cloud_vendor} is not supported."}, status=status.HTTP_400_BAD_REQUEST)
    

    @action(detail=False, methods=['get'], url_path='get-call-details')
    def get_call_details(self, request):
        phone_number = request.query_params.get("phone_number")
        agent_id = request.query_params.get("agent_id")
        date = request.query_params.get("date")

        if  not date:
            return Response({
                "error": "Missing required parameters:  'agent_id', and 'date' are required."
            }, status=status.HTTP_400_BAD_REQUEST)

        user = request.user
        try:
            channel_assign = CloudTelephonyChannelAssign.objects.get(user_id=user.id)
            channel = channel_assign.cloud_telephony_channel
        except CloudTelephonyChannelAssign.DoesNotExist:
            return Response({"error": "No channel assigned to this user."}, status=status.HTTP_404_NOT_FOUND)

        cloud_vendor = channel.cloudtelephony_vendor.name.lower()

        if cloud_vendor == 'cloud connect':
            if not channel.token or not channel.tenent_id:
                return Response({"error": "token and tenant_id required for CloudConnect."}, status=status.HTTP_400_BAD_REQUEST)

            cloud_connect_service = CloudConnectService(channel.token, channel.tenent_id)
            session_response = cloud_connect_service.get_session_id(channel_assign.agent_id)
    
            # if session_response.get("code") != 200 or "session_id" not in session_response:
            #     return Response({"error": "Failed to get session ID from CloudConnect."}, status=status.HTTP_400_BAD_REQUEST)
            # session_id = session_response["session_id"]
            response_data = cloud_connect_service.get_call_details(date, phone_number)
            if response_data.get("code") != 200:
                return Response({"error": "Failed to retrieve call details."}, status=status.HTTP_400_BAD_REQUEST)

            return Response({
                "success": True,
                "data": response_data.get("result", {}),
                "message": response_data.get("status_message")
            }, status=status.HTTP_200_OK)

        return Response({"error": f"{cloud_vendor} is not supported."}, status=status.HTTP_400_BAD_REQUEST)
    
from rest_framework.views import APIView
class GetNumberAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        call_id = request.query_params.get("call_id")
        if not call_id:
            return Response({"error": "call_id is required."}, status=status.HTTP_400_BAD_REQUEST)

        user = request.user
        try:
            channel_assign = CloudTelephonyChannelAssign.objects.get(user_id=user.id)
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
                "phone_number": result.get("phone_number"),
                "message": details_response.get("status_message")
            }, status=status.HTTP_200_OK)

        return Response({"error": f"{cloud_vendor} is not supported."}, status=status.HTTP_400_BAD_REQUEST)