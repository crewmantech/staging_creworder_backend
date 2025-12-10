from django.shortcuts import render
from rest_framework.views import APIView
from accounts.models import Branch, Company
from orders.models import Order_Table, OrderStatus
from orders.perrmissions import ShipmentPermissions
from services.orders.order_service import getOrderDetails
from .serializers import ShipmentSerializer,CourierServiceSerializer, ShipmentVendorSerializer
from .models import CourierServiceModel, ShipmentVendor
from rest_framework import viewsets, status
from rest_framework import status
from rest_framework.response import Response
from services.shipment.shipment_service import *
from services.shipment.schedule_orders import NimbuspostAPI, ShiprocketScheduleOrder,TekipostService, ZoopshipService
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
from rest_framework.decorators import action
from django.shortcuts import get_object_or_404


class ShipmentView(APIView):
    permission_classes = [IsAuthenticated,ShipmentPermissions]
    def post(self, request):
        try:
            createCategoryResponse = createShipment(request.data, request.user.id)
            return Response(
                {
                    "Success": True,
                    "data": ShipmentSerializer(createCategoryResponse).data,
                },
                status=status.HTTP_201_CREATED,
            )
        except ValueError as e:
            return Response(
                {"Success": False, "Errors": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

    def get(self, request, pk=None):
        try:
            data = getShipment(request.user.id,pk)
            serializer = ShipmentSerializer(data, many=True)
            return Response(
                {"Success": True, "Data": serializer.data},
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return Response(
                {"Success": False, "Error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        
    def delete(self, request, pk):
        success = deleteShipment(pk)
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
            updatedData = updateShipment(pk, request.data)
            if updatedData:
                return Response(
                    {
                        "Success": True,
                        "data": ShipmentSerializer(updatedData).data,
                    },
                    status=status.HTTP_200_OK,
                )
            else:
                return Response(
                    {
                        "Success": False,
                        "Error": "Shipment not found or invalid data provided.",
                    },
                    status=status.HTTP_404_NOT_FOUND,
                )
        except ShipmentModel.DoesNotExist:
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

# class CheckServiceability(APIView):
#     def get(self, request, pk=None):
#         data = checkServiceability(request.user.profile.branch_id,request.user.profile.company_id, request.data['pincode'])
#         if data:
#             return Response(
#                 {
#                     "success": True,
#                     "data": data,
#                 },
#                 status=status.HTTP_200_OK,
#             )
#         else:
#             return Response(
#                 {
#                     "success": False,
#                     "data": {"massage":f"Non serviceable {request.data['pincode']}"},
#                 },
#                 status=status.HTTP_404_NOT_FOUND,
#             )

class CourierServiceView(viewsets.ModelViewSet):
    queryset = CourierServiceModel.objects.all()
    serializer_class = CourierServiceSerializer
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        user = request.user
        if 'branch' not in request.data:
            request.data['branch'] = user.profile.branch.id 
        request.data['company'] = user.profile.company.id
        return super().create(request, *args, **kwargs)
    
    @transaction.atomic
    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        user = request.user

        if 'company' not in request.data:
            request.data['company'] = instance.company.id 
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data)
    
class ScheduleOrders(viewsets.ModelViewSet):
    queryset = ShipmentModel.objects.all()
    serializer_class = ShipmentSerializer
    permission_classes = [IsAuthenticated,ShipmentPermissions]
    
    @transaction.atomic
    def create(self, request, *args, **kwargs):
        order_ids = request.data.get("order_ids", [])
        channel_id = request.data.get("shipment_channel_id","")
        ship_by = request.data.get("ship_by","")
        pickup_id = request.data.get("pickup_id")
        if not order_ids:
            return Response(
                {"error": "Order IDs are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not pickup_id:
            return Response(
                {"error": "pickup code is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        trackdata = ShipmentModel.objects.get(
                id=ship_by
            )
        print(trackdata,"-------------------164")
        serializer = ShipmentSerializer(trackdata)
        serialized_data = serializer.data
        if not serialized_data:
            return Response({"error": "Vendor not found", "data": {}}, status=status.HTTP_400_BAD_REQUEST)
        print(serialized_data,"-------------------164")
        _response = {}
        print(serialized_data['shipment_vendor']['name'],"----------------------12")
        if serialized_data['shipment_vendor']['name'].lower()  =='shiprocket':
            if serialized_data['credential_username']!='' or serialized_data['credential_username']!=None:
                shiprocket_service = ShiprocketScheduleOrder(serialized_data['credential_username'],serialized_data['credential_password'])
                # _response=shiprocket_service.schedule_order(order_ids, request.user.profile.branch.id, request.user.profile.company.id,serialized_data['shipment_channel_id'],request.user.id)
                shipment_vendor = serialized_data['shipment_vendor'].get('id')
                _response=shiprocket_service.schedule_order(order_ids, request.user.profile.branch.id, request.user.profile.company.id,channel_id,request.user.id,pickup_id,shipment_vendor)
        elif serialized_data['shipment_vendor']['name'].lower() == 'tekipost':
                if serialized_data['credential_username']:
                    takipost_service = TekipostService(
                        serialized_data['credential_username'], serialized_data['credential_password']
                    )
                    shipment_vendor = serialized_data['shipment_vendor'].get('id')
                    _response=takipost_service.schedule_order(order_ids, request.user.profile.branch.id, request.user.profile.company.id,channel_id,request.user.id,pickup_id,shipment_vendor)
        elif serialized_data['shipment_vendor']['name'].lower() == 'nimbuspost':
                if serialized_data['credential_username']:
                    shipment_vendor = serialized_data['shipment_vendor'].get('id')
                    nimbuspost_service = NimbuspostAPI(
                        serialized_data['credential_username'], serialized_data['credential_password']
                    )
                    _response=nimbuspost_service.schedule_order(order_ids, request.user.profile.branch.id, request.user.profile.company.id,channel_id,request.user.id,pickup_id,shipment_vendor)
        elif serialized_data['shipment_vendor']['name'].lower()=='zoopship':
                if serialized_data['credential_username']:
                    shipment_vendor = serialized_data['shipment_vendor'].get('id')
                    nimbuspost_service = ZoopshipService(
                        serialized_data['credential_username'], serialized_data['credential_password']
                    )
                    _response=nimbuspost_service.schedule_order_zoopshipservice(order_ids, request.user.profile.branch.id, request.user.profile.company.id,channel_id,request.user.id,pickup_id,shipment_vendor)
        if _response:
            return Response(
                {
                    "data":_response
                },
                status=status.HTTP_200_OK,
            )
        else:
            return Response(
                {
                    "data":_response,
                    "message":"please select a valid vendor name"
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
class ShiprocketChannelViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    @transaction.atomic
    def list(self, request, *args, **kwargs):
        trackdata = ShipmentModel.objects.filter(
            branch=request.user.profile.branch.id, 
            company=request.user.profile.company.id,
            status=1
        )
        # Serialize the data
        serializer = ShipmentSerializer(trackdata, many=True)
        serialized_data = serializer
        _response = []
        shiprocket_service = None
        # Loop through each shipment data to get channels
        for shipmentData in serialized_data.data:
            if shipmentData['shipment_vendor']['name'].lower()  == 'shiprocket':
                # Check if the credentials are valid
                if shipmentData['credential_username'] and shipmentData['credential_username'] != '':
                    shiprocket_service = ShiprocketScheduleOrder(
                        shipmentData['credential_username'], shipmentData['credential_password']
                    )
                    
                    channels_response = shiprocket_service.Ship_channels()
                    print(channels_response)
                    if 'data' in channels_response:
                        _response.append(channels_response['data'])
                    else:
                        _response.append(channels_response)

        if _response:
            return Response(
                {
                    "data": _response
                },
                status=status.HTTP_200_OK
            )
        else:
            return Response(
                {
                    "error": "No valid Shiprocket credentials found or failed to fetch channels."
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        

class GeneratePickupAPI(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        """
        API endpoint to generate a pickup for orders.
        """
        order_ids = request.data.get("order_ids", [])
        if not order_ids:
            return Response(
                {"error": "Order IDs are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        
        branch_id = request.user.profile.branch.id
        company_id = request.user.profile.company.id
        
        # Create an instance of your service class
        trackdata = ShipmentModel.objects.filter(
            branch=request.user.profile.branch.id, 
            company=request.user.profile.company.id,
            status=1
        )
        # Serialize the data
        serializer = ShipmentSerializer(trackdata, many=True)
        serialized_data = serializer
        shiprocket_service = None
        _response = []
        # Loop through each shipment data to get channels
        for shipmentData in serialized_data.data:
            if shipmentData['shipment_vendor']['name'].lower() == 'shiprocket':
                # Check if the credentials are valid
                if shipmentData['credential_username'] and shipmentData['credential_username'] != '':
                    shiprocket_service = ShiprocketScheduleOrder(
                        shipmentData['credential_username'], shipmentData['credential_password']
                    )
        
        # Call the generate_pickup method
                _response = shiprocket_service.generate_pickup(order_ids, branch_id, company_id)
        
        # Check and return the response
        if _response.get("errors"):
            return Response(
                {
                    "message": "Some pickups failed to generate.",
                    "success_logs": _response.get("success_logs", []),
                    "errors": _response.get("errors", []),
                },
                status=status.HTTP_207_MULTI_STATUS,
            )
        
        return Response(
            {
                "message": "All pickups generated successfully.",
                "success_logs": _response.get("success_logs", []),
            },
            status=status.HTTP_200_OK,
        )


class TrackOrderAPI(viewsets.ViewSet):
    """
    API to track an order using shipment ID.
    """
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def retrieve(self, request, pk=None, *args, **kwargs):
        """
        Retrieve the tracking details for an order.
        :param pk: Shipment ID of the order to be tracked.
        """
        if not pk:
            return Response(
                {"error": "Order ID is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            order_data = Order_Table.objects.get(id=pk)
        except Order_Table.DoesNotExist:
            return Response({"error": "Order not found for the given order ID."}, status=status.HTTP_400_BAD_REQUEST)
        shipment_id = order_data.shipment_id
        if not shipment_id:
            return Response({"error": "Unable to fetch the shipment ID from the order."}, status=status.HTTP_400_BAD_REQUEST)
        # Fetch the Shiprocket credentials from the user's profile
        try:
            trackdata = ShipmentModel.objects.filter(
            branch=request.user.profile.branch.id, 
            company=request.user.profile.company.id,
            status=1
            )
            # Serialize the data
            serializer = ShipmentSerializer(trackdata, many=True)
            serialized_data = serializer
            _response = []
            shiprocket_service = None
            # Loop through each shipment data to get channels
            for shipmentData in serialized_data.data:
                if shipmentData['shipment_vendor']['name'].lower()  == 'shiprocket':
                    # Check if the credentials are valid
                    if shipmentData['credential_username'] and shipmentData['credential_username'] != '':
                        shiprocket_service = ShiprocketScheduleOrder(
                            shipmentData['credential_username'], shipmentData['credential_password']
                        )
        except Exception as e:
            return Response(
                {"error": f"Error initializing Shiprocket service: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # Use the service to track the order
        try:
            tracking_response = shiprocket_service.track_order(shipment_id)
        except Exception as e:
            return Response(
                {"error": f"Error while tracking the order: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # Return the tracking data
        if tracking_response and tracking_response["status"] == "success":
            return Response(
                tracking_response,
                status=status.HTTP_200_OK,
            )
        else:
            return Response(
                tracking_response,
                status=status.HTTP_400_BAD_REQUEST,
            )

class WalletBalanceAPI(viewsets.ViewSet):
    """
    API to fetch the wallet balance from Shiprocket.
    """
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def list(self, request, *args, **kwargs):
        """
        Fetch wallet balance details for the authenticated Shiprocket account.
        """
        try:
            trackdata = ShipmentModel.objects.filter(
            branch=request.user.profile.branch.id, 
            company=request.user.profile.company.id,
            status=1
        )
            # Serialize the data
            serializer = ShipmentSerializer(trackdata, many=True)
            serialized_data = serializer
            _response = []
            shiprocket_service = None
            # Loop through each shipment data to get channels
            for shipmentData in serialized_data.data:
                if shipmentData['shipment_vendor']['name'].lower()  == 'shiprocket':
                    # Check if the credentials are valid
                    if shipmentData['credential_username'] and shipmentData['credential_username'] != '':
                        shiprocket_service = ShiprocketScheduleOrder(
                            shipmentData['credential_username'], shipmentData['credential_password']
                        )
        except Exception as e:
            return Response(
                {"error": f"Error initializing Shiprocket service: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        wallet_response = shiprocket_service.get_wallet_balance()

        if "status" in wallet_response and wallet_response["status"] == "error":
            return Response(wallet_response, status=status.HTTP_400_BAD_REQUEST)

        return Response(wallet_response, status=status.HTTP_200_OK)
    


class NDRViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated,ShipmentPermissions]

    @transaction.atomic
    def list(self, request):
        """
        Fetch all NDR shipments.
        """
        company_id = request.user.profile.company.id
        branch_id = request.user.profile.branch.id
        trackdata = ShipmentModel.objects.filter(
            branch=request.user.profile.branch.id, 
            company=request.user.profile.company.id,
            status=1
        )
        # Serialize the data
        serializer = ShipmentSerializer(trackdata, many=True)
        serialized_data = serializer
        _response = []
        shiprocket_service = None
        # Loop through each shipment data to get channels
        for shipmentData in serialized_data.data:
            if shipmentData['shipment_vendor']['name'].lower()  == 'shiprocket':
                # Check if the credentials are valid
                if shipmentData['credential_username'] and shipmentData['credential_username'] != '':
                    shiprocket_service = ShiprocketScheduleOrder(
                        shipmentData['credential_username'], shipmentData['credential_password']
                    )
        response = shiprocket_service.get_all_ndr_shipments()
        order_list = []
        if response.get("status") == "error":
            return Response(response, status=status.HTTP_400_BAD_REQUEST)
        if response.get('data'):
            for data in response['data']:
                id = data.get('id')
                order = Order_Table.objects.get(vendor_order_id=id)
                if order:
                    res= getOrderDetails(request.user,id=order.id,company_id=company_id,branch_id=branch_id)
                    order_list.append(res)
                ofd_count = len(data.get('history')) if data.get('history') else 0
                
                res= getOrderDetails(request.user,id=order.id,company_id=company_id,branch_id=branch_id) 
        data = {"Success": True,
                "data":order_list} 
        return Response(data, status=status.HTTP_200_OK)

    @transaction.atomic
    def retrieve(self, request, pk=None):
        """
        Fetch details of a specific NDR shipment.
        """
        try:
            order_data = Order_Table.objects.get(id=pk)
        except Order_Table.DoesNotExist:
            return Response({"error": "Order not found for the given order ID."}, status=status.HTTP_400_BAD_REQUEST)
        shipment_id = order_data.shipment_id
        if not shipment_id:
            return Response({"error": "Unable to fetch the shipment ID from the order."}, status=status.HTTP_400_BAD_REQUEST)
        trackdata = ShipmentModel.objects.filter(
            branch=request.user.profile.branch.id, 
            company=request.user.profile.company.id,
            status=1
        )
        # Serialize the data
        serializer = ShipmentSerializer(trackdata, many=True)
        serialized_data = serializer
        _response = []
        shiprocket_service = None
        
        # Loop through each shipment data to get channels
        for shipmentData in serialized_data.data:
            if shipmentData['shipment_vendor']['name'].lower()  == 'shiprocket':
                # Check if the credentials are valid
                if shipmentData['credential_username'] and shipmentData['credential_username'] != '':
                    shiprocket_service = ShiprocketScheduleOrder(
                        shipmentData['credential_username'], shipmentData['credential_password']
                    )
        response = shiprocket_service.get_ndr_shipment_details(shipment_id)
        if response.get("status") == "error":
            return Response(response, status=status.HTTP_400_BAD_REQUEST)
        return Response(response, status=status.HTTP_200_OK)

    @transaction.atomic
    def create(self, request):
        """
        Perform an action on an NDR shipment.
        """
        order_id = request.data.get("order_id")
        action = request.data.get("action")
        date = request.data.get("date")

        if not order_id or not action:
            return Response(
                {"error": "Order ID and action are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            order_data = Order_Table.objects.get(id=order_id)
            if order_data.ofd_counter == 0 or not order_data.ofd_counter:
                counter = 0
            else:
                counter = order_data.ofd_counter+1
        except Order_Table.DoesNotExist:
            return Response({"error": "Order not found for the given order ID."}, status=status.HTTP_400_BAD_REQUEST)
        shipment_id = order_data.order_wayBill
        if not shipment_id:
            return Response({"error": "Unable to fetch the way Bill Number from the order."}, status=status.HTTP_400_BAD_REQUEST)
        trackdata = ShipmentModel.objects.filter(
            branch=request.user.profile.branch.id, 
            company=request.user.profile.company.id,
            status=1
        )
        # Serialize the data
        serializer = ShipmentSerializer(trackdata, many=True)
        serialized_data = serializer
        _response = []
        shiprocket_service = None
        # Loop through each shipment data to get channels
        for shipmentData in serialized_data.data:
            if shipmentData['shipment_vendor']['name'].lower()  == 'shiprocket':
                # Check if the credentials are valid
                if shipmentData['credential_username'] and shipmentData['credential_username'] != '':
                    shiprocket_service = ShiprocketScheduleOrder(
                        shipmentData['credential_username'], shipmentData['credential_password']
                    )
        response = shiprocket_service.action_ndr(shipment_id, action)
        if response.get("status") == "error":
            return Response(response, status=status.HTTP_400_BAD_REQUEST)
        
        order_data.ofd_counter = counter
        order_data.save()
        return Response(response, status=status.HTTP_200_OK)
    



class PickupLocationViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def list(self, request):
        """
        Fetch all pickup locations.
        """
        trackdata = ShipmentModel.objects.filter(
            branch=request.user.profile.branch.id, 
            company=request.user.profile.company.id,
            status=1
        )
        # Serialize the data
        serializer = ShipmentSerializer(trackdata, many=True)
        serialized_data = serializer
        _response = []
        shiprocket_service = None
        # Loop through each shipment data to get channels
        for shipmentData in serialized_data.data:
            if shipmentData['shipment_vendor']['name'].lower()  == 'shiprocket':
                # Check if the credentials are valid
                if shipmentData['credential_username'] and shipmentData['credential_username'] != '':
                    shiprocket_service = ShiprocketScheduleOrder(
                        shipmentData['credential_username'], shipmentData['credential_password']
                    )
        response = shiprocket_service.get_all_pickup_locations()
        if response.get("status") == "error":
            return Response(response, status=status.HTTP_400_BAD_REQUEST)
        return Response(response, status=status.HTTP_200_OK)

    @transaction.atomic
    def create(self, request):
        """
        Add a new pickup location.
        """
        location_data = request.data.get("location_data", None)

        if not location_data:
            return Response(
                {"error": "Pickup location data is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        trackdata = ShipmentModel.objects.filter(
            branch=request.user.profile.branch.id, 
            company=request.user.profile.company.id,
            status=1
        )
        # Serialize the data
        serializer = ShipmentSerializer(trackdata, many=True)
        serialized_data = serializer
        _response = []
        shiprocket_service = None
        # Loop through each shipment data to get channels
        for shipmentData in serialized_data.data:
            if shipmentData['shipment_vendor']['name'].lower()  == 'shiprocket':
                # Check if the credentials are valid
                if shipmentData['credential_username'] and shipmentData['credential_username'] != '':
                    shiprocket_service = ShiprocketScheduleOrder(
                        shipmentData['credential_username'], shipmentData['credential_password']
                    )
        print("-------------536")
        response = shiprocket_service.add_pickup_location(location_data)
        if response.get("status") == "error":
            return Response(response, status=status.HTTP_400_BAD_REQUEST)
        return Response(response, status=status.HTTP_200_OK)
    

def fetch_all_pickup_locations(user):
    """
    Fetch all pickup locations for the logged-in user.
    """
    trackdata = ShipmentModel.objects.filter(
            branch = user.profile.branch.id, 
            company = user.profile.company.id,
            status=1
        )
        # Serialize the data
    serializer = ShipmentSerializer(trackdata, many=True)
    serialized_data = serializer
    _response = []
    shiprocket_service = None
    # Loop through each shipment data to get channels
    for shipmentData in serialized_data.data:
        if shipmentData['shipment_vendor']['name'].lower()  == 'shiprocket':
            # Check if the credentials are valid
            if shipmentData['credential_username'] and shipmentData['credential_username'] != '':
                shiprocket_service = ShiprocketScheduleOrder(
                    shipmentData['credential_username'], shipmentData['credential_password']
                )
    response = shiprocket_service.get_all_pickup_locations()
    return response


def add_new_pickup_location(user, location_data):
    """
    Add a new pickup location for the logged-in user.
    """
    trackdata = ShipmentModel.objects.filter(
            branch = user.profile.branch.id, 
            company = user.profile.company.id,
            status=1
        )
        # Serialize the data
    serializer = ShipmentSerializer(trackdata, many=True)
    serialized_data = serializer
    _response = []
    shiprocket_service = None
    # Loop through each shipment data to get channels
    for shipmentData in serialized_data.data:
        if shipmentData['shipment_vendor']['name'].lower()  == 'shiprocket':
            # Check if the credentials are valid
            if shipmentData['credential_username'] and shipmentData['credential_username'] != '':
                shiprocket_service = ShiprocketScheduleOrder(
                    shipmentData['credential_username'], shipmentData['credential_password']
                )
    response = shiprocket_service.add_pickup_location(location_data)
    return response

class OrderCancellationViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        try:
            order_id = request.data.get('order_id')
            reason = request.data.get('reason')

            if not order_id:
                return Response({"error": "Order ID is required."}, status=status.HTTP_400_BAD_REQUEST)
            if not reason:
                return Response({"error": "Reason is required."}, status=status.HTTP_400_BAD_REQUEST)

            # Fetch the order
            try:
                order_data = Order_Table.objects.get(id=order_id)
            except Order_Table.DoesNotExist:
                return Response({"error": "Order not found for the given order ID."}, status=status.HTTP_400_BAD_REQUEST)

            # Fetch the branch and company instances
            try:
                branch = Branch.objects.get(id=request.user.profile.branch.id)
                company = Company.objects.get(id=request.user.profile.company.id)
            except Branch.DoesNotExist:
                return Response({"error": "Branch does not exist."}, status=status.HTTP_400_BAD_REQUEST)
            except Company.DoesNotExist:
                return Response({"error": "Company does not exist."}, status=status.HTTP_400_BAD_REQUEST)

            # Fetch shipment data
            trackdata = ShipmentModel.objects.filter(
                branch=branch,
                company=company,
                status=1
            )

            # Serialize the data
            serializer = ShipmentSerializer(trackdata, many=True)
            serialized_data = serializer

            # Initialize Shiprocket service
            shiprocket_service = None
            for shipmentData in serialized_data.data:
                if shipmentData['shipment_vendor']['name'].lower()  == 'shiprocket':
                    if shipmentData['credential_username']:
                        shiprocket_service = ShiprocketScheduleOrder(
                            shipmentData['credential_username'], shipmentData['credential_password']
                        )

            vendor_order_id = order_data.vendor_order_id
            if vendor_order_id is None:
                # Update the order status to "Canceled"
                order_status, created = OrderStatus.objects.get_or_create(
                    name='Canceled'
                    # branch=branch,
                    # company=company
                )
                order_data.order_status = order_status
                order_data.order_remark = reason
                order_data.save()
            else:
                # Use Shiprocket API to cancel the order
                cancellation_response = shiprocket_service.cancel_order(vendor_order_id, reason)
                print(cancellation_response,"---------------759")
                if "error" in cancellation_response:
                    return Response(cancellation_response, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
                # Update the order status after successful cancellation
                if cancellation_response.get("status_code") == 200:
                    order_status, created = OrderStatus.objects.get_or_create(
                        name='CANCELED'
                        # branch=branch,
                        # company=company
                    )
                    order_data.order_status = order_status
                    order_data.order_remark = reason
                    order_data.save()

            return Response({"message": "Order canceled successfully."}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class TrackOrderViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]  # Only authenticated users can access this API
    
    @action(detail=False, methods=['get'], url_path='track/(?P<shipment_id>[^/.]+)', url_name='track_order')
    def track_order(self, request, shipment_id=None):
        
        try:
            if not shipment_id:
                return Response(
                    {"error": "Order ID is required."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            try:
                order_data = Order_Table.objects.get(id=shipment_id)
            except Order_Table.DoesNotExist:
                return Response({"error": "Order not found for the given order ID."}, status=status.HTTP_400_BAD_REQUEST)
            shipment_id = order_data.shipment_id
            if not shipment_id:
                return Response({"error": "Unable to fetch the shipment ID from the order."}, status=status.HTTP_400_BAD_REQUEST)
            trackdata = ShipmentModel.objects.filter(
                branch=request.user.profile.branch.id, 
                company=request.user.profile.company.id,
                status=1
            )

            # Serialize the data
            serializer = ShipmentSerializer(trackdata, many=True)
            serialized_data = serializer

            # Initialize Shiprocket service
            shiprocket_service = None
            for shipmentData in serialized_data.data:
                if shipmentData['shipment_vendor']['name'].lower()  == 'shiprocket':
                    if shipmentData['credential_username']:
                        shiprocket_service = ShiprocketScheduleOrder(
                            shipmentData['credential_username'], shipmentData['credential_password']
                        )
            # Create instance of ShiprocketAPI
          
            tracking_response = shiprocket_service.track_order(shipment_id)

            # Return success or failure response based on tracking data
            if tracking_response["status"] == "success":
                return Response(tracking_response, status=status.HTTP_200_OK)
            else:
                return Response(tracking_response, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            # Handle any unexpected exceptions
            return Response(
                {"status": "error", "message": f"An error occurred: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        

class OrderOperationsViewSet(viewsets.ModelViewSet):
    """
    ViewSet to handle Shiprocket order operations such as generating manifests, printing labels, and invoices.
    """
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['post'], url_path='generate-manifest', url_name='generate_manifest')
    def generate_manifest(self, request):
        shipment_ids = request.data.get('shipment_ids', [])
        if not shipment_ids:
            return Response({"error": "Shipment IDs are required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            trackdata = ShipmentModel.objects.filter(
                branch=request.user.profile.branch.id, 
                company=request.user.profile.company.id,
                status=1
            )

            # Serialize the data
            serializer = ShipmentSerializer(trackdata, many=True)
            serialized_data = serializer

            # Initialize Shiprocket service
            shiprocket_service = None
            for shipmentData in serialized_data.data:
                if shipmentData['shipment_vendor']['name'].lower()  == 'shiprocket':
                    if shipmentData['credential_username']:
                        shiprocket_service = ShiprocketScheduleOrder(
                            shipmentData['credential_username'], shipmentData['credential_password']
                        )
            manifest_response = shiprocket_service.generate_manifest(shipment_ids)

            if manifest_response.get("status") == "success":
                return Response(manifest_response, status=status.HTTP_200_OK)
            else:
                return Response({
                    "status": "failed",
                    "message": manifest_response.get("message", "Manifest generation failed."),
                    "error_details": manifest_response.get("error", [])
                }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'], url_path='print-manifest', url_name='print_manifest')
    def print_manifest(self, request):
        manifest_id = request.data.get('manifest_id')
        if not manifest_id:
            return Response(
                {"error": "Manifest ID is required."}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Fetch shipment data for the user's branch and company
            trackdata = ShipmentModel.objects.filter(
                branch=request.user.profile.branch.id, 
                company=request.user.profile.company.id,
                status=1
            )

            # Serialize the shipment data
            serializer = ShipmentSerializer(trackdata, many=True)
            serialized_data = serializer.data

            # Initialize Shiprocket service
            shiprocket_service = None
            for shipmentData in serialized_data:
                if shipmentData['shipment_vendor']['name'].lower()  == 'shiprocket' and shipmentData['credential_username']:
                    shiprocket_service = ShiprocketScheduleOrder(
                        shipmentData['credential_username'], 
                        shipmentData['credential_password']
                    )
                    break  # Use the first matching service

            # Ensure Shiprocket service is initialized
            if not shiprocket_service:
                return Response(
                    {"error": "No valid Shiprocket credentials found."}, 
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Call the Shiprocket API to print the manifest
            print_response = shiprocket_service.print_manifest(manifest_id)
            if print_response.get("status") == "success":
                return Response(print_response, status=status.HTTP_200_OK)
            else:
                return Response(
                    {
                        "status": "failed",
                        "message": print_response.get("message", "Manifest printing failed."),
                        "error_details": print_response.get("error_details", [])
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
        except Exception as e:
            return Response(
                {"error": "An unexpected error occurred.", "details": str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post'], url_path='generate-label', url_name='generate_label')
    def generate_label(self, request):
        shipment_ids = request.data.get('shipment_ids', [])
        if not shipment_ids:
            return Response({"error": "Shipment IDs are required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            trackdata = ShipmentModel.objects.filter(
                branch=request.user.profile.branch.id, 
                company=request.user.profile.company.id,
                status=1
            )

            # Serialize the data
            serializer = ShipmentSerializer(trackdata, many=True)
            serialized_data = serializer

            # Initialize Shiprocket service
            shiprocket_service = None
            for shipmentData in serialized_data.data:
                if shipmentData['shipment_vendor']['name'].lower()  == 'shiprocket':
                    if shipmentData['credential_username']:
                        shiprocket_service = ShiprocketScheduleOrder(
                            shipmentData['credential_username'], shipmentData['credential_password']
                        )
            label_response = shiprocket_service.generate_label(shipment_ids)

            if label_response.get("status") == "success":
                return Response(label_response, status=status.HTTP_200_OK)
            else:
                return Response({
                    "status": "failed",
                    "message": label_response.get("message", "Label generation failed."),
                    "error_details": label_response.get("error", [])
                }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'], url_path='generate-invoice', url_name='generate_invoice')
    def generate_invoice(self, request):
        shipment_ids = request.data.get('shipment_ids', [])
        if not shipment_ids:
            return Response({"error": "Shipment IDs are required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            trackdata = ShipmentModel.objects.filter(
                branch=request.user.profile.branch.id, 
                company=request.user.profile.company.id,
                status=1
            )

            # Serialize the data
            serializer = ShipmentSerializer(trackdata, many=True)
            serialized_data = serializer

            # Initialize Shiprocket service
            shiprocket_service = None
            for shipmentData in serialized_data.data:
                if shipmentData['shipment_vendor']['name'].lower()  == 'shiprocket':
                    if shipmentData['credential_username']:
                        shiprocket_service = ShiprocketScheduleOrder(
                            shipmentData['credential_username'], shipmentData['credential_password']
                        )
            invoice_response = shiprocket_service.generate_invoice(shipment_ids)

            if invoice_response.get("status") == "success":
                return Response(invoice_response, status=status.HTTP_200_OK)
            else:
                return Response({
                    "status": "failed",
                    "message": invoice_response.get("message", "Invoice generation failed."),
                    "error_details": invoice_response.get("error", [])
                }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        

class ShipmentViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def list(self, request):
        """
        Fetch details of all shipments for the authenticated user's branch/company.
        """
        try:
            # Fetch shipment data for the user's branch/company
            trackdata = ShipmentModel.objects.filter(
                branch=request.user.profile.branch.id,
                company=request.user.profile.company.id,
                status=1
            )
            
            # Serialize the data
            serializer = ShipmentSerializer(trackdata, many=True)
            serialized_data = serializer.data
            shiprocket_service = None
            for shipmentData in serialized_data:
                if shipmentData['shipment_vendor']['name'].lower()  == 'shiprocket' and shipmentData['credential_username']:
                    shiprocket_service = ShiprocketScheduleOrder(
                        shipmentData['credential_username'],
                        shipmentData['credential_password']
                    )
                    break  # Use the first matching service

            # Ensure Shiprocket service is initialized
            if not shiprocket_service:
                return Response(
                    {"error": "No valid Shiprocket credentials found."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Fetch shipment details for the provided shipment ID (pk)
            shipment_response = shiprocket_service.shipment_details()
            if shipment_response.get("status") == "success":
                return Response(shipment_response.get("shipment_details"), status=status.HTTP_200_OK)
            else:
                return Response(
                    {
                        "status": "failed",
                        "message": shipment_response.get("message", "Unable to fetch shipment details."),
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            
        except Exception as e:
            return Response(
                {"error": "An unexpected error occurred.", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def retrieve(self, request, pk=None):
        """
        Fetch details of a specific shipment using the shipment ID.
        """
        try:
            # Fetch shipment credentials for the user's branch/company
            trackdata = ShipmentModel.objects.filter(
                branch=request.user.profile.branch.id,
                company=request.user.profile.company.id,
                status=1
            )

            # Serialize the data
            serializer = ShipmentSerializer(trackdata, many=True)
            serialized_data = serializer.data

            # Initialize Shiprocket service
            shiprocket_service = None
            for shipmentData in serialized_data:
                if shipmentData['shipment_vendor']['name'].lower()  == 'shiprocket' and shipmentData['credential_username']:
                    shiprocket_service = ShiprocketScheduleOrder(
                        shipmentData['credential_username'],
                        shipmentData['credential_password']
                    )
                    break  # Use the first matching service

            # Ensure Shiprocket service is initialized
            if not shiprocket_service:
                return Response(
                    {"error": "No valid Shiprocket credentials found."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Fetch shipment details for the provided shipment ID (pk)
            shipment_response = shiprocket_service.shipment_details(pk)

            if shipment_response.get("status") == "success":
                return Response(shipment_response, status=status.HTTP_200_OK)
            else:
                return Response(
                    {
                        "status": "failed",
                        "message": shipment_response.get("message", "Unable to fetch shipment details."),
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
        except Exception as e:
            return Response(
                {"error": "An unexpected error occurred.", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )



class ShipmentVendorViewSet(viewsets.ModelViewSet):
    """
    CRUD API for Shipment Vendors.
    """
    queryset = ShipmentVendor.objects.all()
    serializer_class = ShipmentVendorSerializer
    permission_classes = [IsAuthenticated]
    
def get_vendor_service(shipment: ShipmentModel):
    """
    Return the correct service instance (Shiprocket / Nimbuspost)
    using the SAME credential pattern as ScheduleOrders.create.
    """
    serializer = ShipmentSerializer(shipment)
    data = serializer.data

    vendor_name = (data["shipment_vendor"]["name"] or "").strip().lower()
    username = data.get("credential_username")
    password = data.get("credential_password")

    if not username:
        raise ValueError("Credential username not configured for this shipment")

    if vendor_name == "shiprocket":
        return ShiprocketScheduleOrder(username, password)

    if vendor_name == "nimbuspost":
        return NimbuspostAPI(username, password)

    raise ValueError(f"Unsupported shipment vendor: {data['shipment_vendor']['name']}")

class NDRActionAPIView(APIView):
    """
    POST: Perform NDR action based on shipment_vendor_id and awb.

    Common request body (example):

    {
        "shipment_vendor_id": 1,
        "awb": "NMBC0002111111",
        "action": "re-attempt",
        "comments": "Customer wants re-delivery",  # mainly for Shiprocket
        "action_data": {                          # mainly for Nimbuspost
            "re_attempt_date": "2021-06-03"
        }
    }

    - For Nimbuspost:
        -> calls NimbuspostAPI.submit_ndr_action([...])
    - For Shiprocket:
        -> calls ShiprocketScheduleOrder.action_ndr(awb, action, comments)
    """

    def post(self, request, *args, **kwargs):
        shipment_vendor_id = request.data.get("shipment_vendor_id")
        awb = request.data.get("awb")
        action = request.data.get("action")
        comments = request.data.get("comments", "")
        action_data = request.data.get("action_data", {})

        if not shipment_vendor_id or not awb or not action:
            return Response(
                {
                    "detail": "shipment_vendor_id, awb, and action are required.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Get vendor
        vendor = get_object_or_404(ShipmentVendor, id=shipment_vendor_id)

        try:
            service = get_vendor_service(vendor)
        except ValueError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            return Response(
                {"detail": "Error initializing vendor service", "error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        vendor_name = vendor.name.strip().lower()

        try:
            if vendor_name == "nimbuspost":
                # Nimbuspost expects a list of actions
                payload = [
                    {
                        "awb": awb,
                        "action": action,
                        "action_data": action_data or {},
                    }
                ]
                result = service.submit_ndr_action(payload)

            elif vendor_name == "shiprocket":
                # Shiprocket expects awb in URL and body with action & comments
                result = service.action_ndr(
                    awb=awb,
                    action=action,
                    comments=comments,
                )

            else:
                return Response(
                    {"detail": f"Unsupported vendor: {vendor.name}"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            return Response(result, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {
                    "detail": "Error while performing NDR action",
                    "error": str(e),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class NDRListAPIView(APIView):
    """
    GET: List NDR shipments based on vendor.

    Query params:
      - shipment_vendor_id (required)
      - awb_number (optional, used for Nimbuspost)
      - page_no, per_page (optional for Nimbuspost)

    Examples:

    Nimbuspost:
      GET /api/ndr/?shipment_vendor_id=1&awb_number=1122335577&page_no=1&per_page=50

    Shiprocket:
      GET /api/ndr/?shipment_vendor_id=2
      -> calls ShiprocketScheduleOrder.get_all_ndr_shipments()
    """

    def get(self, request, *args, **kwargs):
        shipment_vendor_id = request.query_params.get("shipment_vendor_id")
        if not shipment_vendor_id:
            return Response(
                {"detail": "shipment_vendor_id is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        vendor = get_object_or_404(ShipmentVendor, id=shipment_vendor_id)

        try:
            service = get_vendor_service(vendor)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.exception("Error initializing vendor service")
            return Response(
                {"detail": "Error initializing vendor service", "error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        vendor_name = vendor.name.strip().lower()

        try:
            if vendor_name == "nimbuspost":
                awb_number = request.query_params.get("awb_number", "")
                page_no = int(request.query_params.get("page_no", 1))
                per_page = int(request.query_params.get("per_page", 50))

                result = service.get_ndr_list(
                    awb_number=awb_number,
                    page_no=page_no,
                    per_page=per_page,
                )

            elif vendor_name == "shiprocket":
                # Your ShiprocketScheduleOrder.get_all_ndr_shipments()
                result = service.get_all_ndr_shipments()

            else:
                return Response(
                    {"detail": f"Unsupported vendor: {vendor.name}"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            return Response(result, status=status.HTTP_200_OK)

        except Exception as e:
            logger.exception("Error while fetching NDR list")
            return Response(
                {"detail": "Error while fetching NDR list", "error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class NDRDetailAPIView(APIView):
    """
    GET: Get NDR details for a specific AWB based on vendor.

    Path param:
      - awb (required)

    Query params:
      - shipment_vendor_id (required)

    Examples:

    Nimbuspost:
      GET /api/ndr/NMBC0002111111/?shipment_vendor_id=1
      -> calls NimbuspostAPI.get_ndr_list(awb_number=awb, page_no=1, per_page=1)

    Shiprocket:
      GET /api/ndr/NMBC0002111111/?shipment_vendor_id=2
      -> calls ShiprocketScheduleOrder.get_ndr_shipment_details(awb)
    """

    def get(self, request, awb, *args, **kwargs):
        shipment_vendor_id = request.query_params.get("shipment_vendor_id")
        if not shipment_vendor_id:
            return Response(
                {"detail": "shipment_vendor_id is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        vendor = get_object_or_404(ShipmentVendor, id=shipment_vendor_id)

        try:
            service = get_vendor_service(vendor)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.exception("Error initializing vendor service")
            return Response(
                {"detail": "Error initializing vendor service", "error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        vendor_name = vendor.name.strip().lower()

        try:
            if vendor_name == "nimbuspost":
                # For a single AWB, we can just reuse get_ndr_list with page 1, per_page 1
                result = service.get_ndr_list(
                    awb_number=awb,
                    page_no=1,
                    per_page=1,
                )

            elif vendor_name == "shiprocket":
                result = service.get_ndr_shipment_details(shipment_id=awb)

            else:
                return Response(
                    {"detail": f"Unsupported vendor: {vendor.name}"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            return Response(result, status=status.HTTP_200_OK)

        except Exception as e:
            logger.exception("Error while fetching NDR detail")
            return Response(
                {"detail": "Error while fetching NDR detail", "error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )