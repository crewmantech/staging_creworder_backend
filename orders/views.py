
import calendar
import csv
import io
import pdb
from datetime import time,date, timedelta
from django.shortcuts import get_object_or_404
from rest_framework import status,pagination
from rest_framework.response import Response
from rest_framework import viewsets, status
from django.db.models import Q,OuterRef,Subquery
from django.db.models import Sum, Count
from accounts.models import Attendance, Branch, CompanyUserAPIKey, Employees, UserTargetsDelails
from accounts.permissions import CanCreateAndDeleteCustomerState, CanCreateOrDeletePaymentStatus, IsSuperAdmin
from cloud_telephony.models import CloudTelephonyChannel, CloudTelephonyChannelAssign
from lead_management.models import Lead
from orders.perrmissions import CategoryPermissions, OrderPermissions
from services.cloud_telephoney.cloud_telephoney_service import CloudConnectService
from shipment.models import ShipmentVendor
from .models import (
    AllowStatus,
    Order_Table,
    OrderDetail,
    Category,
    OrderLogModel,
    OrderStatusWorkflow,
    OrderValueSetting,
    Payment_Status,
    Payment_Type,
    Payment_method,
    PincodeLocality,
    Products,
    Customer_State,
    OrderStatus,
    AllowStatus,
    ReturnType,
    LableLayout,
    SmsConfig,
    invoice_layout
)
from .serializers import (
    AllowStatusSerializer,
    CustomerStateSerializer,
    NotificationsConfigSerializer,
    OrderLogSerializer,
    OrderStatusUpdateSerializer,
    OrderStatusWorkflowSerializer,
    OrderSummarySerializer,
    OrderTableSerializer,
    OrderDetailSerializer,
    CategorySerializer,
    OrderValueSettingSerializer,
    PaymentStatusSerializer,
    PaymentTypeSerializer,
    PincodeLocalitySerializer,
    ProductSerializer,
    OrderStatusSerializer,
    FilterOrdersSerializer,
    ReturnTypeSerializer,
    ScanOrderSerializer,
    LableLayoutSerializer,
    LableinvoiceSerializer,
    PaymentMethodSerializer

)
from rest_framework.views import APIView
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from dashboard.views import ScheduleOrderForDashboard
from django.utils import timezone
import traceback
from django.utils.timezone import now
from django.db import transaction,IntegrityError
# from rest_framework.authtoken.models import Token
from accounts.models import ExpiringToken as Token
from services.category.category_service import (
    createCategory,
    updateCategory,
    deleteCategory,
    getCategory,
)
from services.products.products_service import (
    createProduct,
    updateProduct,
    deleteProduct,
    getProduct,
)
from services.orders.order_service import (
    attach_product_details,
    createOrders,
    get_single_order,
    orderLogInsert,
    soft_delete_order,
    updateOrders,
    deleteOrder,
    getOrderDetails,
    exportOrders,
    ivoiceDeatail,
    checkServiceability,
)
from datetime import datetime
from rest_framework.decorators import action
from django.db.models import Sum, F


class FilterOrdersPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 10000 

class OrderAPIView(APIView):
    permission_classes = [IsAuthenticated,OrderPermissions]
    
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        try:
            state = Customer_State.objects.get(name=request.data['customer_state'])
            lead_id = request.data.get('lead_id')
            if lead_id:
                try:
                    lead = Lead.objects.get(lead_id=lead_id)
                    request.data['customer_phone'] =  lead.customer_phone
                except Lead.DoesNotExist:
                    return f"No number found for lead ID: {lead_id}"
            else:
                request.data['lead_id'] = None
            repeat_order = request.data.get("repeat_order")
            if repeat_order and str(repeat_order)=='1':
                if request.user.has_perm('accounts.view_number_masking_others') and request.user.profile.user_type != 'admin':
                    reference_order = request.data.get('reference_order')
                    if reference_order:
                        try:
                            order = Order_Table.objects.get(id=reference_order)
                            print(order.customer_phone)
                            request.data['customer_phone'] =  order.customer_phone
                        except Order_Table.DoesNotExist:
                            print("No mobile number found using this order ID.")
                            return f"No reference_order found for : {reference_order}"
                    else:
                        return f"No reference_order found for : {reference_order}"
            print(request.data,"---------------------120")
            state_id = state.id
            # for payment purposes
            payment_type = request.data['payment_type']
            total_amount = float(request.data['total_amount'])
            user = self.request.user
            branch_id = user.profile.branch  # Assuming the user has a related `profile` model with `branch`
            company_id = user.profile.company 
            # Filter OrderValueSetting
            payment_type_id = request.data["payment_type"]
            prepaid_amount = request.data["prepaid_amount"]
            payment_type = Payment_Type.objects.filter(id=payment_type_id).first()
            # call_id = request.data['call_id']
            # if call_id:
            #     # Get the assigned channel
            #     try:
            #         channel_assign = CloudTelephonyChannelAssign.objects.get(user_id=user.id)
            #         channel = channel_assign.cloud_telephony_channel
            #         if not channel.token or not channel.tenent_id:
            #             return Response({"error": "CloudConnect token or tenant ID missing."}, status=status.HTTP_400_BAD_REQUEST)

            #         cloud_service = CloudConnectService(channel.token, channel.tenent_id)
            #         response = cloud_service.call_details(call_id)
            #         if response.get("code") == 200:
            #             phone_number = response.get("result", {}).get("phone_number")
            #             request.data['customer_phone'] = phone_number
            #         else:
            #             return Response({"error": "Call details fetch failed."}, status=status.HTTP_400_BAD_REQUEST)
            #     except CloudTelephonyChannelAssign.DoesNotExist:
            #         return Response({"error": "Channel not assigned to user."}, status=status.HTTP_400_BAD_REQUEST)
            
                
            if not payment_type:
                return Response({"error": "Invalid payment type"}, status=status.HTTP_400_BAD_REQUEST)

            payment_type_name = payment_type.name.lower()  # Convert to lowercase for consistency

            # Fetch OrderStatus where name = "Pending"
            order_status = OrderStatus.objects.filter(name="Pending").first()
            if order_status:
                request.data["order_status"] = order_status.id

            # If Payment Type is COD, update Payment Status to "Payment Pending"
            if payment_type_name == "partial payment":
                payment_status = Payment_Status.objects.filter(name="Partial Payment Received").first()
                if payment_status:
                    request.data["payment_status"] = payment_status.id
            if payment_type_name == "prepaid payment":
                payment_status = Payment_Status.objects.filter(name="Payment Received").first()
                if payment_status:
                    request.data["payment_status"] = payment_status.id
            else:
                payment_status = Payment_Status.objects.filter(name="Payment Pending").first()
                if payment_status:
                    request.data["payment_status"] = payment_status.id
            
            payment_setting = OrderValueSetting.objects.filter(
                payment_type_id=payment_type,
                company_id=company_id,
                branch_id=branch_id
            ).first()
            amount_to_check = prepaid_amount if payment_type_name.lower() == "partial payment" else total_amount
            if payment_setting and float(payment_setting.amount) > amount_to_check:
                return Response(
                    {"Success": False, "Error": "We can't proceed with your order. Please ensure the order value is Greater than " + str(payment_setting.amount) + ".","message": "We can't proceed with your order. Please ensure the order value is Greater than " + str(payment_setting.amount) + "."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            # for pincode and locality purposes
            request.data["order_created_by"] = request.data.get('order_created_by') or request.user.id
            request.data["customer_state"] = state_id
            orderSerializer = OrderTableSerializer(data=request.data)
            if orderSerializer.is_valid():
                createOrdersResponse = createOrders(request.data, request.user.id)
                return Response(
                    {
                        "Success": True,
                        "data": OrderTableSerializer(createOrdersResponse).data,
                    },
                    status=status.HTTP_201_CREATED,
                )
            return Response(orderSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        except Customer_State.DoesNotExist:
            return Response(
                {"Success": False, "Error": "Customer state not found."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        
        except Exception as e:
            return Response(
                {"Success": False, "Error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

    def get(self, request, pk=None):
        try:
            branch_id = request.user.profile.branch  # Assuming the user has a related `profile` model with `branch`
            company_id = request.user.profile.company 
            new = []
            if pk:
                data =  get_single_order(request.user.id, pk)
                if request.user.profile.user_type not in  ["admin","superadmin"]:
                    if request.user.has_perm('accounts.view_Product_Information_others') or request.user.has_perm('accounts.view_order_payment_status_others') or request.user.has_perm('accounts.view_order_status_tracking_others') or request.user.has_perm('accounts.view_customer_information_others'):
                        for i in data:
                            if request.user.has_perm('accounts.view_Product_Information_others'):
                                i['product_permission'] = True
                            if request.user.has_perm('accounts.view_order_payment_status_others'):
                                i['payment_permission'] = True
                            if request.user.has_perm('accounts.view_order_status_tracking_others'):
                                i['status_permission'] = True
                            if request.user.has_perm('accounts.view_customer_information_others'):
                                i['customer_permission'] = True
                            new.append(i)
                    else:
                        for i in data:
                            if request.user.has_perm('accounts.view_Product_Information_others'):
                                i['product_permission'] = False
                            if request.user.has_perm('accounts.view_order_payment_status_others'):
                                i['payment_permission'] = False
                            if request.user.has_perm('accounts.view_order_status_tracking_others'):
                                i['status_permission'] = False
                            if request.user.has_perm('accounts.view_customer_information_others'):
                                i['customer_permission'] = False
                            new.append(i)
                else:
                   
                        for i in data:
                            i['product_permission'] = True
                            i['payment_permission'] = True
                            i['status_permission'] = True
                            i['customer_permission'] = True
                            new.append(i)
                   
                    # pass
                # for i in data:
                #     # i['product_details'] = None
                #     new.append(i)
            else:
                data = getOrderDetails(request.user.id, pk,company_id,branch_id)
                return Response(
                    {"Success": True, "Data": data},
                    status=status.HTTP_200_OK,
                )
            return Response(
                {"Success": True, "Data": new},
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return Response(
                {"Success": False, "Error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def delete(self, request, pk):
        # success = deleteOrder(pk)
        success = soft_delete_order(pk)
        if success:
            return Response(
                {"Success": True, "Message": "Deleted successfully."},
                status=status.HTTP_204_NO_CONTENT,
            )
        else:
            return Response(
                {"Success": False, "Error": "Not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

    def put(self, request, pk):
        try:
            if not request.user.has_perm('accounts.edit_order_others') and request.user.profile.user_type != 'admin':
                return Response(
                    {"error": "You do not have permission to edit order status."},
                    status=status.HTTP_403_FORBIDDEN
                )
            updatedData = updateOrders(pk, request.data, request.user.id)
            if updatedData:
                return Response(
                    {
                        "Success": True,
                        "data": OrderTableSerializer(updatedData).data,
                    },
                    status=status.HTTP_200_OK,
                )
            else:
                return Response(
                    {
                        "Success": False,
                        "Error": "Order not found or invalid data provided.",
                    },
                    status=status.HTTP_404_NOT_FOUND,
                )
        except Category.DoesNotExist:
            return Response(
                {
                    "Success": False,
                    "Error": "Order not found.",
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        except ValueError as e:
            return Response(
                {"Success": False, "Errors": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

    def patch(self, request, pk):
        try:
            if (not request.user.has_perm('accounts.edit_order_others') and not request.user.has_perm('accounts.edit_order_status_others')) and request.user.profile.user_type != 'admin':
                return Response(
                    {"error": "You do not have permission to edit order status."},
                    status=status.HTTP_403_FORBIDDEN
                )
            data = request.data
            if 'customer_state_name' in data:
                state_name = data['customer_state_name'].upper()
                CustomerState = Customer_State.objects.filter(name=state_name).first()
                data.pop('customer_state_name')
                if CustomerState:
                    data['customer_state'] =  CustomerState.id
                else:
                    return Response({"Success": False, "message":"State Not Found"})
            updatedData = updateOrders(pk, data, request.user.id)
            if updatedData:
                return Response(
                    {
                        "Success": True,
                        "data": OrderTableSerializer(updatedData).data,
                    },
                    status=status.HTTP_200_OK,
                )
            else:
                return Response(
                    {
                        "Success": False,
                        "Error": "Order not found or invalid data provided.",
                    },
                    status=status.HTTP_404_NOT_FOUND,
                )
        except Category.DoesNotExist:
            return Response(
                {
                    "Success": False,
                    "Error": "Order not found.",
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        except ValueError as e:
            return Response(
                {"Success": False, "Errors": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )


class OrderDetailView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated,CategoryPermissions]
    queryset = Order_Table.objects.all()
    serializer_class = OrderTableSerializer


class CategoryView(APIView):
    permission_classes = [IsAuthenticated,CategoryPermissions]

    def post(self, request):
        try:
            createCategoryResponse = createCategory(request.data, request.user.id)
            return Response(
                {
                    "Success": True,
                    "data": CategorySerializer(createCategoryResponse).data,
                },
                status=status.HTTP_201_CREATED,
            )
        except ValueError as e:
            return Response(
                {"Success": False, "Errors": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

    def put(self, request, pk):  # Changed from 'id' to 'pk'
        try:
            updatedData = updateCategory(pk, request.data)
            if updatedData:
                return Response(
                    {
                        "Success": True,
                        "data": CategorySerializer(updatedData).data,
                    },
                    status=status.HTTP_200_OK,
                )
            else:
                return Response(
                    {
                        "Success": False,
                        "Error": "Category not found or invalid data provided.",
                    },
                    status=status.HTTP_404_NOT_FOUND,
                )
        except Category.DoesNotExist:
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

    def delete(self, request, pk):
        success = deleteCategory(pk)
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

    def get(self, request, pk=None):
        try:
            data = getCategory(request.user.id, pk)
            serializer = CategorySerializer(data, many=True)
            return Response(
                {"Success": True, "Data": serializer.data},
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return Response(
                {"Success": False, "Error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class ProductView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            createCategoryResponse = createProduct(request.data, request.user.id)
            return Response(
                {
                    "Success": True,
                    "data": ProductSerializer(createCategoryResponse).data,
                },
                status=status.HTTP_201_CREATED,
            )
        except ValueError as e:
            return Response(
                {"Success": False, "Errors": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

    def put(self, request, pk):
        try:
            updatedData = updateProduct(pk, request.data)
            if updatedData:
                return Response(
                    {
                        "Success": True,
                        "data": ProductSerializer(updatedData).data,
                    },
                    status=status.HTTP_200_OK,
                )
            else:
                return Response(
                    {
                        "Success": False,
                        "Error": "Product not found or invalid data provided.",
                    },
                    status=status.HTTP_404_NOT_FOUND,
                )
        except Products.DoesNotExist:
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

    def delete(self, request, pk):
        success = deleteProduct(pk)
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

    def get(self, request, pk=None):
        try:
            data = getProduct(request.user.id, pk)
            serializer = ProductSerializer(data, many=True)
            return Response(
                {"Success": True, "Data": serializer.data},
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return Response(
                {"Success": False, "Error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class ProductListCreateAPIView(generics.ListCreateAPIView):

    serializer_class = ProductSerializer

    permission_classes = [IsAuthenticated]

    pagination_class = None  # Disable pagination



    def get_queryset(self):

        user = self.request.user

        branch = user.profile.branch

        company = user.profile.company

        # Get all products for the user's branch and company

        queryset = Products.objects.filter(company=company)

        # Check if the user is an agent

        if user.profile.user_type == "agent":

            user_permissions = set(user.get_all_permissions())

            allowed_product_ids = []

            for product in queryset:

                # Generate permission code name

                product_name_slug = product.product_name.lower().replace(' ', '_')

                permission_codename = f"products_can_work_on_this_{product_name_slug}"

                full_permission = f"orders.{permission_codename}"  

                # Check if user has this permission

                if full_permission in user_permissions:

                    allowed_product_ids.append(product.id)

            queryset = queryset.filter(id__in=allowed_product_ids)



        return queryset
           


class ProductDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return Products.objects.filter(branch=user.profile.branch, company=user.profile.company)


class CategoryListCreateAPIView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated,CategoryPermissions]
    queryset = Category.objects.all()
    serializer_class = CategorySerializer


class CategorytDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated,CategoryPermissions]
    queryset = Category.objects.all()
    serializer_class = CategorySerializer


class OrderStatusAPIView(viewsets.ModelViewSet):
    queryset = OrderStatus.objects.all()
    serializer_class = OrderStatusSerializer
    permission_classes = [IsAuthenticated] 
    pagination_class = None

    # def get_queryset(self):
    #     """
    #     Retrieve OrderStatus based on the user's branch and company.
    #     """
    #     # user = self.request.user
    #     queryset = OrderStatus.objects.all()
    #     # queryset = OrderStatus.objects.filter(
    #     #     branch=user.profile.branch,
    #     #     company=user.profile.company
    #     # )
    #     return queryset
    def get_queryset(self):
        """
        Retrieve OrderStatus based on:
        - 'newstatus' query param → Filters pending, completed, rejected
        - User permissions ('can_work_on_this')
        - 'permission_status' query param → Only return statuses user can work on
        """
        user = self.request.user
        queryset = OrderStatus.objects.all()

        # Handle 'newstatus' query param
        newstatus_filter = self.request.query_params.get("newstatus", None)
        if newstatus_filter is not None:
            queryset = queryset.filter(name__in=["Non Serviceable", "Accepted", "Rejected","No Response","Future Order"])

        # Get user permissions
        user_permissions = set(user.get_all_permissions())

        # Find statuses user has 'can_work_on_this' permission for
        allowed_statuses = []
        # Handle 'permission_status' query param
        permission_status_filter = self.request.query_params.get("permission_status", None)
        shipment_status_filter = self.request.query_params.get("shipment_status", None)
        if permission_status_filter is not None:
            for order_status in queryset:
                permission_codename = f"orderstatus_can_work_on_this_{order_status.name.lower().replace(' ', '_')}"
                full_permission = f"orders.{permission_codename}"
                if full_permission in user_permissions:
                    allowed_statuses.append(order_status.id)
            queryset = queryset.filter(id__in=allowed_statuses)
        elif shipment_status_filter is not None:
            for order_status in queryset:
                name = order_status.name.lower()
                if name not in ["non serviceable", "accepted", "rejected", "No Response", "future order", "pending"]:
                    permission_codename = f"orderstatus_can_work_on_this_{name.replace(' ', '_')}"
                    full_permission = f"orders.{permission_codename}"
                    if full_permission in user_permissions or user.profile.user_type == 'admin':
                        allowed_statuses.append(order_status.id)
            queryset = queryset.filter(id__in=allowed_statuses)
        elif allowed_statuses:
            queryset = queryset.filter(id__in=allowed_statuses)  # Default permission check

        return queryset

    def create(self, request, *args, **kwargs):
        """
        Handle creating an OrderStatus instance.
        """
        # user = request.user
        data = request.data.copy() 
        # data['branch'] = user.profile.branch.id
        # data['company'] = user.profile.company.id

        serializer = self.get_serializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class orderExport(APIView):
    def post(self, request, *args, **kwargs):
        if (
            "data_range" not in request.data
            or request.data["data_range"] == ""
            or "date_type" not in request.data
            or request.data["date_type"] == ""
            or "status" not in request.data
            or request.data["status"] == ""
        ):
            return Response(
                {
                    "success": False,
                    "massage": "data_range ,date_type and status all fields are mandatory and not pass empty",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        data = exportOrders(request.user.id, request.data)
        return Response({"success": True, "Data": data}, status=status.HTTP_200_OK)


class invoiceDetails(APIView):
    def post(self, request, *args, **kwargs):
        if "invoices" not in request.data or request.data["invoices"] == None:
            return Response(
                {
                    "success": False,
                    "massage": "invoices id ,fields mandatory and not pass empty",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        data = ivoiceDeatail(request.user.id, request.data)
        return Response({"success": True, "Data": data}, status=status.HTTP_200_OK)


class CheckServiceability(APIView):
    def get(self, request, pk=None):
        pincode = request.GET.get("pincode")
        mobile = request.GET.get("mobile")
        re_order=request.GET.get("re_order")
        data = checkServiceability(
            request.user.profile.branch_id,
            request.user.profile.company_id,
            {"pincode": pincode, "mobile": mobile,"re_order":re_order},
        )
        if data == 1:
            return Response(
                {
                    "success": True,
                    "data": {"massage": f"Re Order"},
                },
                status=status.HTTP_208_ALREADY_REPORTED,
            )
        elif data == 2:
            return Response(
                {
                    "success": True,
                    "data": {"massage": f"Non serviceable"},
                },
                status=status.HTTP_208_ALREADY_REPORTED,
            )
        elif data:
            return Response(
                {
                    "success": True,
                    "data": data,
                },
                status=status.HTTP_200_OK,
            )
        else:
            return Response(
                {
                    "success": False,
                    "data": {"massage": f"Non serviceable {pincode}"},
                },
                status=status.HTTP_404_NOT_FOUND,
            )


class GetUserPerformance(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        if "user_id" not in request.data:
            return Response(
                {"massage": "user_id is mandatory"}, status.HTTP_400_BAD_REQUEST
            )
        orders = Order_Table.objects.filter(order_created_by=request.user.id,is_deleted=False)
        serializer = OrderTableSerializer(orders, many=True)
        return Response({"massage": "HI", "data": serializer.data}, status.HTTP_200_OK)

class FilterOrdersPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 10000 


def get_date_range(self, request):
        """Extract and validate the date range from the request."""
        if 'date_range' in request.GET and request.GET['date_range']:
            date_range = request.GET['date_range'].split(' ')
            if len(date_range) != 2:
                raise ValueError("Date Range invalid")
            
            
            # Parse the start and end dates
            start_date = datetime.fromisoformat(date_range[0]).date()
            end_date = datetime.fromisoformat(date_range[1]).date()

            # If the end date is the same as the start date, adjust the end time to the last moment of the day
            if start_date == end_date:
                end_date = start_date  # Keep the same day
                end_datetime = datetime.combine(end_date, time.max)  # Set to 23:59:59.999999
            else:
                end_datetime = datetime.combine(end_date, time.max)  # Set to 23:59:59.999999

            start_datetime = datetime.combine(start_date, time.min)  # Set start time to 00:00:00

            return start_datetime, end_datetime
        
        else:
            today = datetime.now().date()
            # print(today, today, "------------------647")

            # If no date range is provided, return the full range of today
            start_datetime = datetime.combine(today, time.min)  # Start of today
            end_datetime = datetime.combine(today, time.max)    # End of today

            return start_datetime, end_datetime
        
class FilterOrdersView(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]  # Replace with actual permissions
    pagination_class = FilterOrdersPagination  # Adjust as necessary
    def get_date_range(self, request):
        """Extract and validate the date range from request.data (POST body)."""
        date_range = request.data.get('date_range')
        
        if date_range:
            if isinstance(date_range, str):
                date_range = date_range.split(' ')
                if len(date_range) != 2:
                    raise ValueError("Date Range invalid")

                start_date = datetime.fromisoformat(date_range[0]).date()
                end_date = datetime.fromisoformat(date_range[1]).date()
            elif isinstance(date_range, dict):
                start_date = date_range.get("start_date")
                end_date = date_range.get("end_date", datetime.now().strftime('%Y-%m-%d'))

                start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
                end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
            else:
                raise ValueError("Invalid date_range format.")
        else:
            today = datetime.now().date()
            start_date = today
            end_date = today

        start_datetime = timezone.make_aware(datetime.combine(start_date, time.min))
        end_datetime = timezone.make_aware(datetime.combine(end_date, time.max))

        return start_datetime, end_datetime
    def create(self, request):
        filters = request.data
        if not filters:
            raise ValueError("No filters provided")
        queryset = Order_Table.objects.all()
        filter_conditions = Q()

        # Mapping API fields to model fields
        filterable_fields = {
            "order_id": "order_id",
            "awb": "order_wayBill",
            "phone_no": "customer_phone",
            "payment_type": "payment_type__id",  # Assuming payment_type has a name field
            "customer_state__id": "state", 
            "city":"customer_city",
            "zone": "zone",
                 # Assuming customer_state has a name field
        }

        # Apply filters for exact matches
        for api_field, model_field in filterable_fields.items():
            value = filters.get(api_field)
            if value is not None:
                filter_conditions &= Q(**{model_field: filters[api_field]})

        # Additional manual adjustments
        # if "product_name" in filters:
        #     product_name = filters["product_name"]
        #     # Adjust based on JSON structure
        #     filter_conditions &= Q(product_details__icontains=product_name)
        if filters.get("product_id") is not None:
            product_id = filters["product_id"]
            # Filter orders that have related OrderDetail entries with the specified product_id
            filter_conditions &= Q(orderdetail__product_id=product_id)
        if filters.get("order_status") is not None:
            order_status = filters["order_status"]
            if order_status == "repeat":
                filter_conditions &= Q(repeat_order=1)  # Repeat Orders

            elif order_status == "running":
                today = now().date()
                start_datetime, end_datetime =  self.get_date_range(request)
                filter_conditions &= Q(created_at__range=(start_datetime, end_datetime))|Q(updated_at__range=(start_datetime, end_datetime))
                
            elif isinstance(order_status, int):
                filter_conditions &= Q(order_status__id=order_status)
            elif isinstance(order_status, str):
                filter_conditions &= Q(order_status__name__icontains=order_status)
            else:
                return Response({"detail": "Invalid order_status format."}, status=status.HTTP_400_BAD_REQUEST)
        if filters.get("agent_name") is not None:
            agent_name = filters["agent_name"]
            filter_conditions &= Q(order_created_by__username__icontains=agent_name)
        if filters.get("user_id") is not None:
            user_id = filters["user_id"]
            filter_conditions &= Q(order_created_by=user_id) | Q(updated_by=user_id)
        
        # Handle date range filtering
        if filters.get("date_range") is not None:
            date_range = filters["date_range"]
            start_date = date_range.get("start_date")
            end_date = date_range.get("end_date", datetime.now().strftime('%Y-%m-%d'))

            # Convert to aware datetime objects
            if start_date and end_date:
                try:
                    start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
                    start_date = timezone.make_aware(datetime.combine(start_date, datetime.min.time()))
                    end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
                    end_date = timezone.make_aware(datetime.combine(end_date, datetime.max.time()))
                    filter_conditions &= Q(created_at__range=(start_date, end_date)) | Q(updated_at__range=(start_date, end_date))
                    
                    # filter_conditions &= (Q(created_at__gte=start_date) | Q(updated_at__gte=start_date))
                except ValueError:
                    return Response({"detail": "Invalid start_date format. Use YYYY-MM-DD."}, status=status.HTTP_400_BAD_REQUEST)

            # if end_date:
            #     try:
            #         end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
            #         end_date = timezone.make_aware(datetime.combine(end_date, datetime.max.time()))
            #         filter_conditions &= (Q(created_at__lte=end_date) | Q(updated_at__lte=end_date))
            #     except ValueError:
            #         return Response({"detail": "Invalid end_date format. Use YYYY-MM-DD."}, status=status.HTTP_400_BAD_REQUEST)
        # Apply the filter conditions to the queryset
        queryset = queryset.filter(filter_conditions)

        # Apply pagination and serialize the queryset
        paginator = self.pagination_class()
        paginated_queryset = paginator.paginate_queryset(queryset, request)
        serializer = FilterOrdersSerializer(paginated_queryset, many=True)
        return paginator.get_paginated_response(serializer.data)




class PincodeLocalityViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing Pincode and Locality data.
    """
    queryset = PincodeLocality.objects.all()
    serializer_class = PincodeLocalitySerializer
    permission_classes = [IsAuthenticated]  # Default permission for viewing data

    # def get_permissions(self):
    #     permissions = super().get_permissions()
    #     if self.action in ['create', 'bulk_upload']:
    #         permissions = [IsSuperAdmin()]  # Only superadmins can create or bulk upload
    #     return permissions

    def create(self, request, *args, **kwargs):
        pincode = request.data.get('pincode')
        locality_name = request.data.get('locality_name')

        if not pincode or not locality_name:
            return Response({"error": "Both pincode and locality name are required."}, status=status.HTTP_400_BAD_REQUEST)

        # Ensure locality_name is unique for the given pincode
        if PincodeLocality.objects.filter(pincode=pincode, locality_name=locality_name).exists():
            return Response({"error": "Locality name already exists for the given pincode."}, status=status.HTTP_400_BAD_REQUEST)

        # Call the default create method if no validation error
        try:
            return super().create(request, *args, **kwargs)
        except IntegrityError:
            return Response({"error": "Error while saving data."}, status=status.HTTP_400_BAD_REQUEST)

    

    @action(detail=False, methods=['post'], permission_classes=[IsSuperAdmin])
    def bulk_upload(self, request, *args, **kwargs):
        if 'file' not in request.FILES:
            return Response({"error": "No file provided"}, status=status.HTTP_400_BAD_REQUEST)

        csv_file = request.FILES['file']

        # Ensure the file is a CSV
        if not csv_file.name.endswith('.csv'):
            return Response({"error": "File is not a CSV"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Read the CSV file
            file_data = csv_file.read().decode('utf-8')
            io_string = io.StringIO(file_data)
            reader = csv.DictReader(io_string)

            processed_records = []
            skipped_records = []
            errors = []

            with transaction.atomic():  # Start a database transaction
                for row in reader:
                    try:
                        pincode = row.get('pincode')
                        locality_name = row.get('locality_name')

                        # Validate data
                        if not pincode or not locality_name:
                            skipped_records.append(row)
                            continue

                        # Skip duplicates
                        if PincodeLocality.objects.filter(pincode=pincode, locality_name=locality_name).exists():
                            skipped_records.append(row)
                            continue

                        # Create a new record
                        PincodeLocality.objects.create(pincode=pincode, locality_name=locality_name)
                        processed_records.append(row)

                    except Exception as e:
                        errors.append({"row": row, "error": str(e)})

            return Response({
                "success": True,
                "message": "Bulk upload completed.",
                "processed": len(processed_records),
                "skipped": len(skipped_records),
                "errors": errors,
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": f"Error: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def retrieve_by_pincode(self, request, *args, **kwargs):
        """
        Custom action to retrieve localities based on pincode.
        """
        pincode = request.query_params.get('pincode')

        if not pincode:
            return Response({"error": "Pincode is required."}, status=status.HTTP_400_BAD_REQUEST)

        localities = PincodeLocality.objects.filter(pincode=pincode)

        if not localities.exists():
            return Response({"message": "No localities found for this pincode."}, status=status.HTTP_404_NOT_FOUND)

        serializer = PincodeLocalitySerializer(localities, many=True)
        return Response({
            "pincode": pincode,
            "localities": serializer.data
        }, status=status.HTTP_200_OK)
    


class PaymentStatusViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Payment_Status
    """
    queryset = Payment_Status.objects.all()
    serializer_class = PaymentStatusSerializer
    permission_classes = [IsAuthenticated, CanCreateOrDeletePaymentStatus]

    def get_queryset(self):
        """
        Optionally filter payment statuses by branch or company via query parameters.
        """
        queryset = super().get_queryset()
        # branch_id = self.request.query_params.get('branch', None)
        # company_id = self.request.query_params.get('company', None)

        # if branch_id:
            # queryset = queryset.filter(branch_id=branch_id)
        # if company_id:
            # queryset = queryset.filter(company_id=company_id)

        return queryset
    
    def perform_create(self, serializer):
        """
        Automatically set `company` and `branch` fields for the created Payment_Status instance.
        """
        # Set the company and branch based on the logged-in user's context
        user = self.request.user
        # branch = user.profile.branch  # Assuming the user has a related `profile` model with `branch`
        # company = user.profile.company  # Assuming the user has a related `profile` model with `company`

        # Save the instance with the additional fields
        serializer.save()



class CustomerStateViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing Customer_State.
    """
    queryset = Customer_State.objects.all()
    serializer_class = CustomerStateSerializer
    permission_classes = [IsAuthenticated & CanCreateAndDeleteCustomerState]

    def get_queryset(self):
        """
        Optionally filter states via query parameters.
        """
        queryset = super().get_queryset()
        name = self.request.query_params.get('name', None)
        if name:
            queryset = queryset.filter(name__icontains=name)
        return queryset

    def create(self, request, *args, **kwargs):
        """
        Override create to ensure unique state names and check permissions.
        """
        return super().create(request, *args, **kwargs)

    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated & CanCreateAndDeleteCustomerState])
    def bulk_upload(self, request, *args, **kwargs):
        """
        Bulk upload Customer_State data from a CSV file.
        """
        if 'file' not in request.FILES:
            return Response({"error": "No file provided."}, status=status.HTTP_400_BAD_REQUEST)

        csv_file = request.FILES['file']

        if not csv_file.name.endswith('.csv'):
            return Response({"error": "File is not a CSV."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            file_data = csv_file.read().decode('utf-8')
            io_string = io.StringIO(file_data)
            reader = csv.DictReader(io_string)

            states_data = []
            errors = []

            with transaction.atomic():
                for row in reader:
                    state_name = row.get('name')
                    gst_state_code = row.get('gst_state_code')
                    if not state_name:
                        errors.append({"row": row, "error": "State name is required."})
                        continue

                    if Customer_State.objects.filter(name=state_name).exists():
                        errors.append({"row": row, "error": f"State '{state_name}' already exists."})
                        continue

                    states_data.append({'name': state_name,"gst_state_code":gst_state_code})

                serializer = CustomerStateSerializer(data=states_data, many=True)
                if serializer.is_valid():
                    serializer.save()
                    return Response({
                        "success": True,
                        "message": "States uploaded successfully.",
                        "errors": errors
                    }, status=status.HTTP_201_CREATED)
                else:
                    return Response({"success": False, "errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({"error": f"Error processing file: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)


# class BulkOrderUploadView(APIView):
#     def post(self, request, *args, **kwargs):
#         file = request.FILES.get('file')  # Get the uploaded file from request
#         if not file:
#             return Response({"error": "No file uploaded."}, status=status.HTTP_400_BAD_REQUEST)

#         try:
#             # Read the file
#             csv_file = io.StringIO(file.read().decode('utf-8'))
#             csv_reader = csv.DictReader(csv_file)
#             orders_data = []

#             for row in csv_reader:
#                 order_data = self.parse_row(row)
#                 if order_data:
#                     orders_data.append(order_data)

#             # Now you have a list of orders_data to create orders
#             return self.create_orders(orders_data, request.user.id)

#         except Exception as e:
#             return Response({"error": f"Error processing CSV: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)

    
#     def parse_row(self, row):
#         try:
#             # Handle missing fields
#             network_ip = row.get('network_ip', '')
#             order_remark = row.get('order_remark', '')
#             is_booked = row.get('is_booked')  # Convert to boolean

#             # Handle foreign key (PK) fields - assume the IDs are integers
#             payment_type = row.get('payment_type')
#             payment_status = row.get('payment_status')
#             order_status = row.get('order_status')
#             customer_state = row.get('customer_state')
#             customer_country = row.get('customer_country')

#             # Fetch PKs using your methods
#             payment_type_id =payment_type
#             payment_status_id = payment_status
#             order_status_id = order_status
#             customer_state_id = customer_state
            

#             # Parse product details
#             product_details = []
#             for i in range(1, 2):  # Assuming 1 product for each row
#                 product_key = f'product_{i}'
#                 product_qty_key = f'product_{i}_qty'
#                 product_price_key = f'product_{i}_price'

#                 if row.get(product_key) and row.get(product_qty_key) and row.get(product_price_key):
#                     product_details.append({
#                         'product': row.get(product_key),  # Assuming this column contains the product IDs
#                         'product_qty': int(row.get(product_qty_key)),
#                         'product_price': float(row.get(product_price_key)),
#                     })

#             # Construct order data
#             order_data = {
#                 'customer_name': row['customer_name'],
#                 'customer_phone': row['customer_phone'],
#                 'customer_address': row['customer_address'],
#                 'product_details': product_details,
#                 'order_status': order_status_id,
#                 'payment_type': payment_type_id,
#                 'payment_status': payment_status_id,
#                 'total_amount': float(row['total_amount']),
#                 'gross_amount': float(row.get('gross_amount', row['total_amount'])),  # Use total_amount if gross_amount is missing
#                 'discount': float(row.get('discount', 0.0)),  # Default to 0 if missing
#                 'prepaid_amount': float(row.get('prepaid_amount', 0.0)),  # Default to 0 if missing
#                 'customer_city': row['customer_city'],
#                 'customer_state': customer_state_id,  # Foreign key to state model
#                 'customer_postal': row['customer_postal'],
#                 'customer_country': customer_country,  # Foreign key to country model
#                 'repeat_order': int(row.get('repeat_order', 0)) if row.get('repeat_order', '').isdigit() else 0,
#                 'network_ip': network_ip,
#                 'order_remark': order_remark,
#                 'is_booked': is_booked,
#             }

#             return order_data

#         except KeyError as e:
#             raise ValueError(f"Missing column: {e}")
#     def create_orders(self, orders_data, user_id):
#         created_orders = []
#         for order_data in orders_data:
#             try:
#                 # Create the order using the existing createOrder service
#                 order = createOrders(order_data, user_id)  # Assuming you have this service available
#                 created_orders.append(order.id)
#             except ValueError as e:
#                 return Response({"error": f"Error creating order: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)

#         return Response({"message": f"Orders successfully created: {created_orders}"}, status=status.HTTP_201_CREATED)
    




class BulkOrderUploadView(APIView):
    permission_classes = [IsAuthenticated,OrderPermissions]
    def post(self, request, *args, **kwargs):
        file = request.FILES.get('file')  # Get the uploaded file from request
        if not file:
            return Response({"error": "No file uploaded."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Read the file
            csv_file = io.StringIO(file.read().decode('utf-8'))
            csv_reader = csv.DictReader(csv_file)
            orders_data = []

            for row in csv_reader:
                order_data = self.parse_row(row)
                if order_data:
                    orders_data.append(order_data)

            # Create orders with transaction atomicity
            return self.create_orders(orders_data, request.user.id)

        except Exception as e:
            return Response({"error": f"Error processing CSV: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)

    def parse_row(self, row):
        try:
            # Handle missing fields
            network_ip = row.get('network_ip', '')
            order_remark = row.get('order_remark', '')
            is_booked = int(row.get('is_booked', 0))  # Convert to integer

            # Foreign key fields
            payment_type_id = int(row.get('payment_type'))
            payment_status_id = int(row.get('payment_status'))
            order_status_id = int(row.get('order_status'))
            customer_state_id = int(row.get('customer_state'))

            # Parse product details
            product_details = []
            for i in range(1, 10):  # Assuming 1 product per row
                product_key = f'product_{i}'
                product_qty_key = f'product_{i}_qty'
                product_price_key = f'product_{i}_price'

                if row.get(product_key) and row.get(product_qty_key) and row.get(product_price_key):
                    product_details.append({
                        'product': int(row.get(product_key)),
                        'product_qty': int(row.get(product_qty_key)),
                        'product_price': float(row.get(product_price_key)),
                    })

            # Construct order data
            order_data = {
                'customer_name': row['customer_name'],
                'customer_phone': row['customer_phone'],
                'customer_address': row['customer_address'],
                'product_details': product_details,
                'order_status': order_status_id,
                'payment_type': payment_type_id,
                'payment_status': payment_status_id,
                'total_amount': float(row['total_amount']),
                'cod_amount':float(row['cod_amount']),
                'gross_amount': float(row.get('gross_amount', row['total_amount'])),
                'discount': float(row.get('discount', 0.0)),
                'prepaid_amount': float(row.get('prepaid_amount', 0.0)),
                'customer_city': row['customer_city'],
                'customer_state': customer_state_id,
                'customer_postal': row['customer_postal'],
                'customer_country': row['customer_country'],
                'repeat_order': int(row.get('repeat_order', 0)),
                'network_ip': network_ip,
                'order_remark': order_remark,
                'is_booked': is_booked,
            }

            return order_data

        except KeyError as e:
            raise ValueError(f"Missing column: {e}")

    @transaction.atomic
    def create_orders(self, orders_data, user_id):
        created_orders = []
        for order_data in orders_data:
            try:
                # Create the order using the existing createOrder service
                order = createOrders(order_data, user_id)
                created_orders.append(order.id)
            except ValueError as e:
                # Rolling back the transaction on failure
                transaction.set_rollback(True)
                return Response({"error": f"Error creating order: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)

        return Response({"message": f"Orders successfully created: {created_orders}"}, status=status.HTTP_201_CREATED)

class PaymentTypeViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Payment_Status
    """
    queryset = Payment_Type.objects.all()
    serializer_class = PaymentTypeSerializer
    permission_classes = [IsAuthenticated, CanCreateOrDeletePaymentStatus]

    def get_queryset(self):
        """
        Optionally filter payment statuses by branch or company via query parameters.
        """
        queryset = super().get_queryset()
        branch_id = self.request.query_params.get('branch', None)
        company_id = self.request.query_params.get('company', None)

        if branch_id:
            queryset = queryset.filter(branch_id=branch_id)
        if company_id:
            queryset = queryset.filter(company_id=company_id)

        return queryset
    
    def perform_create(self, serializer):
        """
        Automatically set `company` and `branch` fields for the created Payment_Status instance.
        """ 
        user = self.request.user
        # branch = user.profile.branch  # Assuming the user has a related `profile` model with `branch`
        # company = user.profile.company  # Assuming the user has a related `profile` model with `company`

        # Save the instance with the additional fields
        serializer.save()


class OrderValueSettingViewSet(viewsets.ModelViewSet):
    queryset = OrderValueSetting.objects.all()
    serializer_class = OrderValueSettingSerializer
    permission_classes = [IsAuthenticated]
    def get_queryset(self):
        queryset = OrderValueSetting.objects.all()
        """
        Optionally filter payment statuses by branch or company via query parameters.
        """
        user = self.request.user
        branch = user.profile.branch 
        company = user.profile.company 
        if branch:
            queryset = queryset.filter(branch_id=branch)
        if company:
            queryset = queryset.filter(company_id=company)

        return queryset
    def perform_create(self, serializer):
        """
        Automatically set `company` and `branch` fields for the created Payment_Status instance.
        """
       
        user = self.request.user
        branch = user.profile.branch  
        company = user.profile.company  
        serializer.save(branch=branch, company=company)
      







class OrderAggregationByStatusAPIView(APIView):

    def get(self, request, *args, **kwargs):
        branch_id = request.query_params.get('branch', None)
        start_date = request.query_params.get('start_date', None)
        end_date = request.query_params.get('end_date', None)
        tl_id = request.query_params.get('tl_id', None)
        date_range = request.query_params.get('date_range',None)
        manager_id = request.query_params.get('manager_id', None)
        agent_id = request.query_params.get('agent_id', None)
        company_id = self.request.user.profile.company
        branch_id = self.request.user.profile.branch
        filter_conditions = {}
        q_filters = Q() 
        if branch_id:
            filter_conditions['branch_id'] = branch_id
        if date_range:
            date_range = date_range.split(' ')
            if len(date_range) != 2:
                raise ValueError("Date Range invalid")
            start_date = datetime.fromisoformat(date_range[0]).date()
            end_date = datetime.fromisoformat(date_range[1]).date()

            # If the end date is the same as the start date, adjust the end time to the last moment of the day
            if start_date == end_date:
                end_date = start_date  # Keep the same day
                end_datetime = datetime.combine(end_date, time.max)  # Set to 23:59:59.999999
            else:
                end_datetime = datetime.combine(end_date, time.max)  # Set to 23:59:59.999999

            start_datetime = datetime.combine(start_date, time.min)
        else:
            today = date.today()
            start_datetime = datetime.combine(today, time.min)  # 00:00:00
            end_datetime = datetime.combine(today, time.max) 
        month_year = start_date.strftime("%Y-%m")

        def apply_date_filter(query, start_datetime, end_datetime,count=True):
                if count:
                    return query.filter(
                        Q(created_at__range=(start_datetime, end_datetime)),
                        is_deleted=False,
                    ).count()
                    # return query.filter(
                    #     Q(created_at__range=(start_datetime, end_datetime)) |
                    #     Q(updated_at__range=(start_datetime, end_datetime)),
                    #     is_deleted=False,
                    # ).count()
                else:
                    return query.filter(
                        Q(created_at__range=(start_datetime, end_datetime)),
                        is_deleted=False,
                    )
                    # return query.filter(
                    #     Q(created_at__range=(start_datetime, end_datetime)) |
                    #     Q(updated_at__range=(start_datetime, end_datetime)),
                    #     is_deleted=False,
                    # )
        if not date_range and start_date and end_date:
            try:
                # Ensure string to date conversion
                start_date_obj = datetime.strptime(start_date, "%Y-%m-%d").date()
                end_date_obj = datetime.strptime(end_date, "%Y-%m-%d").date()

                # Apply full-day range
                start_datetime = datetime.combine(start_date_obj, time.min)  # 00:00:00
                end_datetime = datetime.combine(end_date_obj, time.max)      # 23:59:59.999999

            except ValueError:
                return Response({"error": "Invalid date format. Use YYYY-MM-DD."}, status=status.HTTP_400_BAD_REQUEST)
# Apply date filter 
        all_employee_ids = set()

        if manager_id:
            employees_under_manager = Employees.objects.filter(manager_id=manager_id,status=1)
            manager_ids = employees_under_manager.values_list('user_id', flat=True)
            # filter_conditions['order_created_by_id__in'] = list(manager_ids)
            q_filters &= Q(order_created_by_id__in=manager_ids) | Q(updated_by_id__in=manager_ids)

        if tl_id:
            employees_under_tl = Employees.objects.filter(teamlead_id=tl_id,status=1)
            tl_ids = employees_under_tl.values_list('user_id', flat=True)
            q_filters &= Q(order_created_by_id__in=tl_ids) | Q(updated_by_id__in=tl_ids) |Q(order_created_by_id=tl_id) | Q(updated_by_id=tl_id)
            # filter_conditions['updated_by_id__in'] = list(tl_ids)


        if agent_id:
            # filter_conditions['order_created_by_id__in'] = [agent_id]
            q_filters &= Q(order_created_by_id=agent_id) | Q(updated_by_id=agent_id)
            # all_employee_ids.add(agent_id)

        # if all_employee_ids:
        #     filter_conditions['order_created_by_id__in'] = list(all_employee_ids)

        filter_conditions['is_deleted'] = False

        orders = Order_Table.objects.filter(**filter_conditions).filter(q_filters)

        order_statuses = OrderStatus.objects.all()
        orders = apply_date_filter(orders, start_datetime, end_datetime, False)
        status_data = []
        for status1 in order_statuses:
            status_orders = orders.filter(order_status=status1)
            order_summary = status_orders.aggregate(
                order_count=Count('id'),
                total_price=Sum('total_amount'),
                total_discount=Sum('discount'),
                total_gross_amount=Sum('gross_amount')
            )

            status_data.append({
                'status': status1.name,
                'order_count': order_summary['order_count'] or 0,
                'total_price': order_summary['total_price'] or 0.0,
                'total_discount': order_summary['total_discount'] or 0.0,
                'total_gross_amount': order_summary['total_gross_amount'] or 0.0
            })

        total_orders = orders.aggregate(
            total_order_count=Count('id'),
            total_order_price=Sum('total_amount'),
            total_order_discount=Sum('discount'),
            total_order_gross_amount=Sum('gross_amount')
        )

        total_summary = {
            'total_order_count': total_orders['total_order_count'] or 0,
            'total_order_price': total_orders['total_order_price'] or 0.0,
            'total_order_discount': total_orders['total_order_discount'] or 0.0,
            'total_order_gross_amount': total_orders['total_order_gross_amount'] or 0.0
        }

        target_data = {}

        if manager_id:
            manager_targets = UserTargetsDelails.objects.filter(
                user__id=manager_id,
                monthyear=month_year,
                in_use=True
            ).first()
            # manager_targets = UserTargetsDelails.objects.filter(user__id=manager_id)
            if manager_targets:
                target = manager_targets
                target_data['manager_target'] = {
                    'daily_amount_target': target.daily_amount_target,
                    'daily_orders_target':target.daily_orders_target,
                    'monthly_amount_target': target.monthly_amount_target,
                    'monthly_orders_target': target.monthly_orders_target,
                    'achieve_target': target.achieve_target
                }

        if tl_id:
            tl_targets = UserTargetsDelails.objects.filter(
                user__id=tl_id,
                monthyear=month_year,
                in_use=True
            ).first()
            # tl_targets = UserTargetsDelails.objects.filter(user__id=tl_id)
            if tl_targets:
                target = tl_targets
                target_data['tl_target'] = {
                    'daily_amount_target': target.daily_amount_target,
                    'daily_orders_target':target.daily_orders_target,
                    'monthly_amount_target': target.monthly_amount_target,
                    'monthly_orders_target': target.monthly_orders_target,
                    'achieve_target': target.achieve_target
                }

        if agent_id:
            agent_targets = UserTargetsDelails.objects.filter(
                user__id=agent_id,
                monthyear=month_year,
                in_use=True
            ).first()
            # agent_targets = UserTargetsDelails.objects.filter(user__id=agent_id)
            if agent_targets:
                target = agent_targets
                target_data['agent_target'] = {
                    'daily_amount_target': target.daily_amount_target,
                    'daily_orders_target':target.daily_orders_target,
                    'monthly_amount_target': target.monthly_amount_target,
                    'monthly_orders_target': target.monthly_orders_target,
                    'achieve_target': target.achieve_target
                }

        # === Agent List Section === #
        today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = timezone.now().replace(hour=23, minute=59, second=59, microsecond=999999)
        agents = Employees.objects.filter(
                company_id=company_id,
                branch_id=branch_id,status=1
            )
        if manager_id:
            agents = Employees.objects.filter(manager_id=manager_id,status=1)
        if tl_id:
            agents = Employees.objects.filter(teamlead_id=tl_id,status=1)
        if agent_id:
            agents = Employees.objects.filter(
                company_id=company_id,
                branch_id=branch_id,
                user__id=agent_id,status=1
            )
            # agents = Employees.objects.all()
        message = []
        agent_list = []
        extra_users = Employees.objects.filter(
            Q(user__id=manager_id) | Q(user__id=tl_id),
            status=1
        )

        # Combine agents + manager + team lead
        agents = agents.union(extra_users)
        
        for agent in agents:
            user = agent.user

            # Orders created or updated today
            today_orders = Order_Table.objects.filter(
                Q(order_created_by=user) | Q(updated_by=user),
                is_deleted=False,
            ).filter(
                Q(created_at__range=(start_datetime, end_datetime)) |
                Q(updated_at__range=(start_datetime, end_datetime))
            )

            # Status-based filtering
            today_accepted = apply_date_filter(today_orders.filter(order_status__name='Accepted'), start_datetime, end_datetime)
            today_rejected = apply_date_filter(today_orders.filter(order_status__name='Rejected'), start_datetime, end_datetime)
            no_response = apply_date_filter(today_orders.filter(order_status__name='No Response'), start_datetime, end_datetime)

            # Daily target
            target = UserTargetsDelails.objects.filter(user=user).first()
            daily_target = target.daily_orders_target if target else 0
            total_today = apply_date_filter(today_orders, start_datetime, end_datetime)

            # Progress %
            progress = (today_accepted / daily_target) * 100 if daily_target else 0

            # Attendance
            has_clocked_in = Attendance.objects.filter(
                user=user, date=timezone.now().date(), clock_in__isnull=False
            ).exists()
            agent_status = "Active" if has_clocked_in else "Inactive"

            # Token activity (online/offline)
            token = Token.objects.filter(user=user).first()
            if not token:
                activity = "offline"
            elif timezone.now() - token.last_used > timedelta(minutes=15):
                activity = "offline"
            else:
                activity = "online"

            # Cloudconnect Status
            cloudconnect_status = None
            channels = CloudTelephonyChannel.objects.filter(company=company_id, branch=branch_id, status=1)
            for channel in channels:
                if channel.cloudtelephony_vendor.name.lower() == 'cloudconnect':
                    cloud_connect_service = CloudConnectService(channel.token, channel.tenent_id)
                    response = cloud_connect_service.agent_current_status()
                    if response.get("code") == 200:
                        cloudconnect_response = response.get("result", {})
                        try:
                            channel_assign = CloudTelephonyChannelAssign.objects.get(user=user)
                            agent_id = channel_assign.agent_id
                            cloudconnect_status = next(
                                (a["status"] for a in cloudconnect_response if a["agent_id"] == agent_id),
                                None
                            )
                        except CloudTelephonyChannelAssign.DoesNotExist:
                            pass

            # ✅ Payment Type Aggregation (per agent)
            payment_type_summary = today_orders.filter(
                order_status__name="Accepted"
            ).values("payment_type__name").annotate(
                total=Count("id")
            )

            # ✅ Prepare list of orders with payment type
            order_list = today_orders.values(
                "id", "order_id", "customer_name", "total_amount", "payment_type__name", "order_status__name"
            )

            # Final Response
            agent_list.append({
                "agent_id": user.id,
                "username": user.username,
                "agent_name": user.get_full_name(),
                "profile_image": user.profile.profile_image.url if hasattr(user, 'profile') and user.profile.profile_image else None,
                "agent_status": agent_status,
                "today_orders": total_today,
                "today_accepted": today_accepted,
                "today_rejected": today_rejected,
                "no_response": no_response,
                "cloudconnect_status": cloudconnect_status,
                "activity": activity,
                "daily_target": daily_target,
                "progress": round(progress, 2),

                # ✅ New Fields
                "payment_type_summary": list(payment_type_summary),  # e.g. [{"payment_type__name": "COD", "total": 5}]
                # "orders": list(order_list),  # every order with payment type and status
            })
        team_total_order_target = 0
        team_total_amount_target = 0
        team_total_delivered_orders = 0
        team_total_delivered_amount = 0

        for agent in agents:
            user = agent.user

            # Fetch user target
            target = UserTargetsDelails.objects.filter(
                user=user,
                monthyear=month_year,
                in_use=True
            ).first()
            if target:
                team_total_order_target += target.monthly_orders_target or 0
                team_total_amount_target += target.monthly_amount_target or 0
            today = date.today()

            # First day of current month
            first_day = date(today.year, today.month, 1)

            # Last day of current month
            last_day = date(today.year, today.month, calendar.monthrange(today.year, today.month)[1])

            # Convert to datetime if needed
            start_datetime = datetime.combine(first_day, time.min)
            end_datetime = datetime.combine(last_day, time.max)
            # Today's Delivered Orders (Accepted orders)
            delivered_orders = Order_Table.objects.filter(
                Q(order_created_by=user) | Q(updated_by=user),
                order_status__name="Delivered",
                is_deleted=False
            ).filter(
                Q(created_at__range=(start_datetime, end_datetime))
            )

            delivered_amount = delivered_orders.aggregate(
                amount=Sum("total_amount")
            )["amount"] or 0

            team_total_delivered_orders += delivered_orders.count()
            team_total_delivered_amount += delivered_amount

        # Calculate percentage safely
        order_percentage = (
            (team_total_delivered_orders / team_total_order_target) * 100
            if team_total_order_target else 0
        )

        amount_percentage = (
            (float(team_total_delivered_amount) / float(team_total_amount_target)) * 100
            if team_total_amount_target else 0
        )


        team_target_summary = {
            "total_order_target": team_total_order_target,
            "total_amount_target": team_total_amount_target,
            "total_delivered_orders": team_total_delivered_orders,
            "total_delivered_amount": team_total_delivered_amount,
            "order_percentage": round(order_percentage, 2),
            "amount_percentage": round(amount_percentage, 2),
        }
        response_data = {
            'total_summary': total_summary,
            'status_data': status_data,
            'target_data': target_data,
            'agent_list': agent_list,
            'team_target_summary': team_target_summary,
            "message":message
        }

        return Response(response_data, status=status.HTTP_200_OK)
    
class OrderAggregationByStatusAPIViewPerformance(APIView):

    def get(self, request, *args, **kwargs):
        branch_id = request.query_params.get('branch', None)
        start_date = request.query_params.get('start_date', None)
        end_date = request.query_params.get('end_date', None)
        tl_id = request.query_params.get('tl_id', None)
        date_range = request.query_params.get('date_range',None)
        manager_id = request.query_params.get('manager_id', None)
        agent_id = request.query_params.get('agent_id', None)
        company_id = self.request.user.profile.company
        branch_id = self.request.user.profile.branch
        filter_conditions = {}
        q_filters = Q() 
        if branch_id:
            filter_conditions['branch_id'] = branch_id
        if date_range:
            date_range = date_range.split(' ')
            if len(date_range) != 2:
                raise ValueError("Date Range invalid")
            start_date = datetime.fromisoformat(date_range[0]).date()
            end_date = datetime.fromisoformat(date_range[1]).date()

            # If the end date is the same as the start date, adjust the end time to the last moment of the day
            if start_date == end_date:
                end_date = start_date  # Keep the same day
                end_datetime = datetime.combine(end_date, time.max)  # Set to 23:59:59.999999
            else:
                end_datetime = datetime.combine(end_date, time.max)  # Set to 23:59:59.999999

            start_datetime = datetime.combine(start_date, time.min)
        else:
            today = date.today()
            start_datetime = datetime.combine(today, time.min)  # 00:00:00
            end_datetime = datetime.combine(today, time.max) 

        def apply_date_filter(query, start_datetime, end_datetime,count=True):
                if count:
                    return query.filter(
                        Q(created_at__range=(start_datetime, end_datetime)),
                        is_deleted=False,
                    ).count()
                    # return query.filter(
                    #     Q(created_at__range=(start_datetime, end_datetime)) |
                    #     Q(updated_at__range=(start_datetime, end_datetime)),
                    #     is_deleted=False,
                    # ).count()
                else:
                    return query.filter(
                        Q(created_at__range=(start_datetime, end_datetime)),
                        is_deleted=False,
                    )
                    # return query.filter(
                    #     Q(created_at__range=(start_datetime, end_datetime)) |
                    #     Q(updated_at__range=(start_datetime, end_datetime)),
                    #     is_deleted=False,
                    # )
        if not date_range and start_date and end_date:
            try:
                # Ensure string to date conversion
                start_date_obj = datetime.strptime(start_date, "%Y-%m-%d").date()
                end_date_obj = datetime.strptime(end_date, "%Y-%m-%d").date()

                # Apply full-day range
                start_datetime = datetime.combine(start_date_obj, time.min)  # 00:00:00
                end_datetime = datetime.combine(end_date_obj, time.max)      # 23:59:59.999999

            except ValueError:
                return Response({"error": "Invalid date format. Use YYYY-MM-DD."}, status=status.HTTP_400_BAD_REQUEST)
# Apply date filter 
        all_employee_ids = set()

        if manager_id:
            employees_under_manager = Employees.objects.filter(manager_id=manager_id,status=1)
            manager_ids = employees_under_manager.values_list('user_id', flat=True)
            # filter_conditions['order_created_by_id__in'] = list(manager_ids)
            q_filters &= Q(order_created_by_id__in=manager_ids) | Q(updated_by_id__in=manager_ids)

        if tl_id:
            try:
                # ✅ Treat tl_id as USER ID
                tl_employee = Employees.objects.get(user_id=tl_id, status=1)
                tl_user_id = tl_employee.user.id  # same as tl_id
            except Employees.DoesNotExist:
                return Response({"error": "Invalid teamlead_id"}, status=status.HTTP_400_BAD_REQUEST)

            employees_under_tl = Employees.objects.filter(teamlead_id=tl_user_id, status=1)
            tl_team_user_ids = list(employees_under_tl.values_list('user_id', flat=True))
            tl_team_user_ids.append(tl_user_id)

            q_filters |= (
                Q(order_created_by_id__in=tl_team_user_ids) |
                Q(updated_by_id__in=tl_team_user_ids)
            )


        if agent_id:
            # filter_conditions['order_created_by_id__in'] = [agent_id]
            q_filters &= Q(order_created_by_id=agent_id) | Q(updated_by_id=agent_id)
            # all_employee_ids.add(agent_id)

        # if all_employee_ids:
        #     filter_conditions['order_created_by_id__in'] = list(all_employee_ids)

        filter_conditions['is_deleted'] = False

        orders = Order_Table.objects.filter(**filter_conditions).filter(q_filters)

        order_statuses = OrderStatus.objects.all()
        orders = apply_date_filter(orders, start_datetime, end_datetime, False)
        status_data = []
        for status1 in order_statuses:
            status_orders = orders.filter(order_status=status1)
            order_summary = status_orders.aggregate(
                order_count=Count('id'),
                total_price=Sum('total_amount'),
                total_discount=Sum('discount'),
                total_gross_amount=Sum('gross_amount')
            )

            status_data.append({
                'status': status1.name,
                'order_count': order_summary['order_count'] or 0,
                'total_price': order_summary['total_price'] or 0.0,
                'total_discount': order_summary['total_discount'] or 0.0,
                'total_gross_amount': order_summary['total_gross_amount'] or 0.0
            })

        total_orders = orders.aggregate(
            total_order_count=Count('id'),
            total_order_price=Sum('total_amount'),
            total_order_discount=Sum('discount'),
            total_order_gross_amount=Sum('gross_amount')
        )

        total_summary = {
            'total_order_count': total_orders['total_order_count'] or 0,
            'total_order_price': total_orders['total_order_price'] or 0.0,
            'total_order_discount': total_orders['total_order_discount'] or 0.0,
            'total_order_gross_amount': total_orders['total_order_gross_amount'] or 0.0
        }

        target_data = {}

        if manager_id:
            manager_targets = UserTargetsDelails.objects.filter(user__id=manager_id)
            if manager_targets.exists():
                target = manager_targets.first()
                target_data['manager_target'] = {
                    'daily_amount_target': target.daily_amount_target,
                    'daily_orders_target':target.daily_orders_target,
                    'monthly_amount_target': target.monthly_amount_target,
                    'monthly_orders_target': target.monthly_orders_target,
                    'achieve_target': target.achieve_target
                }

        if tl_id:
            tl_targets = UserTargetsDelails.objects.filter(user__id=tl_id)
            if tl_targets.exists():
                target = tl_targets.first()
                target_data['tl_target'] = {
                    'daily_amount_target': target.daily_amount_target,
                    'daily_orders_target':target.daily_orders_target,
                    'monthly_amount_target': target.monthly_amount_target,
                    'monthly_orders_target': target.monthly_orders_target,
                    'achieve_target': target.achieve_target
                }

        if agent_id:
            agent_targets = UserTargetsDelails.objects.filter(user__id=agent_id)
            if agent_targets.exists():
                target = agent_targets.first()
                target_data['agent_target'] = {
                    'daily_amount_target': target.daily_amount_target,
                    'daily_orders_target':target.daily_orders_target,
                    'monthly_amount_target': target.monthly_amount_target,
                    'monthly_orders_target': target.monthly_orders_target,
                    'achieve_target': target.achieve_target
                }

        # === Agent List Section === #
        today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = timezone.now().replace(hour=23, minute=59, second=59, microsecond=999999)
        agents = Employees.objects.filter(
                company_id=company_id,
                branch_id=branch_id,status=1
            )
        if manager_id:
            agents = Employees.objects.filter(manager_id=manager_id,status=1)
        if tl_id:
            agents = Employees.objects.filter(teamlead_id=tl_id,status=1)
        if agent_id:
            agents = Employees.objects.filter(
                company_id=company_id,
                branch_id=branch_id,
                user__id=agent_id,status=1
            )
            # agents = Employees.objects.all()
        message = []
        agent_list = []
        extra_users = Employees.objects.filter(
            Q(user__id=manager_id) | Q(user__id=tl_id),
            status=1
        )

        # Combine agents + manager + team lead
        agents = agents.union(extra_users)
        
        for agent in agents:
            user = agent.user

            # Orders created or updated today
            today_orders = Order_Table.objects.filter(
                Q(order_created_by=user) | Q(updated_by=user),
                is_deleted=False,
            ).filter(
                Q(created_at__range=(start_datetime, end_datetime)) |
                Q(updated_at__range=(start_datetime, end_datetime))
            )

            # Status-based filtering
            today_accepted = apply_date_filter(today_orders.filter(order_status__name='Accepted'), start_datetime, end_datetime)
            today_rejected = apply_date_filter(today_orders.filter(order_status__name='Rejected'), start_datetime, end_datetime)
            no_response = apply_date_filter(today_orders.filter(order_status__name='No Response'), start_datetime, end_datetime)

            # Daily target
            target = UserTargetsDelails.objects.filter(user=user).first()
            daily_target = target.daily_orders_target if target else 0
            total_today = apply_date_filter(today_orders, start_datetime, end_datetime)

            # Progress %
            progress = (today_accepted / daily_target) * 100 if daily_target else 0

            # Attendance
            has_clocked_in = Attendance.objects.filter(
                user=user, date=timezone.now().date(), clock_in__isnull=False
            ).exists()
            agent_status = "Active" if has_clocked_in else "Inactive"

            # Token activity (online/offline)
            token = Token.objects.filter(user=user).first()
            if not token:
                activity = "offline"
            elif timezone.now() - token.last_used > timedelta(minutes=15):
                activity = "offline"
            else:
                activity = "online"

            # Cloudconnect Status
            cloudconnect_status = None
            channels = CloudTelephonyChannel.objects.filter(company=company_id, branch=branch_id, status=1)
            for channel in channels:
                if channel.cloudtelephony_vendor.name.lower() == 'cloudconnect':
                    cloud_connect_service = CloudConnectService(channel.token, channel.tenent_id)
                    response = cloud_connect_service.agent_current_status()
                    if response.get("code") == 200:
                        cloudconnect_response = response.get("result", {})
                        try:
                            channel_assign = CloudTelephonyChannelAssign.objects.get(user=user)
                            agent_id = channel_assign.agent_id
                            cloudconnect_status = next(
                                (a["status"] for a in cloudconnect_response if a["agent_id"] == agent_id),
                                None
                            )
                        except CloudTelephonyChannelAssign.DoesNotExist:
                            pass

            # ✅ Payment Type Aggregation (per agent)
            payment_type_summary = today_orders.filter(
                order_status__name="Accepted"
            ).values("payment_type__name").annotate(
                total=Count("id")
            )

            # ✅ Prepare list of orders with payment type
            order_list = today_orders.values(
                "id", "order_id", "customer_name", "total_amount", "payment_type__name", "order_status__name"
            )

            # Final Response
            agent_list.append({
                "agent_id": user.id,
                "username": user.username,
                "agent_name": user.get_full_name(),
                "profile_image": user.profile.profile_image.url if hasattr(user, 'profile') and user.profile.profile_image else None,
                "agent_status": agent_status,
                "today_orders": total_today,
                "today_accepted": today_accepted,
                "today_rejected": today_rejected,
                "no_response": no_response,
                "cloudconnect_status": cloudconnect_status,
                "activity": activity,
                "daily_target": daily_target,
                "progress": round(progress, 2),

                # ✅ New Fields
                "payment_type_summary": list(payment_type_summary),  # e.g. [{"payment_type__name": "COD", "total": 5}]
                # "orders": list(order_list),  # every order with payment type and status
            })

        response_data = {
            'total_summary': total_summary,
            'status_data': status_data,
            'target_data': target_data,
            'agent_list': agent_list,
            "message":message
        }

        return Response(response_data, status=status.HTTP_200_OK)




class UpdateOrderStatusAndPaymentStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        order = get_object_or_404(Order_Table, pk=pk)
        updated_fields = {}
    
        # Check if user is trying to update order status
        new_order_status_id = request.data.get("order_status_id")
        if new_order_status_id:
            if not request.user.has_perm('accounts.edit_order_others'):
                if not request.user.has_perm('accounts.edit_order_status_others'):
                    return Response(
                        {"error": "You do not have permission to edit order status."},
                        status=status.HTTP_403_FORBIDDEN
                    )
            try:
                status_obj = OrderStatus.objects.get(id=new_order_status_id)
                order.order_status = status_obj
                updated_fields["order_status"] = new_order_status_id
            except OrderStatus.DoesNotExist:
                return Response(
                    {"error": "Invalid order_status_id"},
                    status=status.HTTP_400_BAD_REQUEST
                )

        # Check if user is trying to update payment status
        new_payment_status_id = request.data.get("payment_status_id")
        if new_payment_status_id:
            if not request.user.has_perm('accounts.edit_order_others'):
                if not request.user.has_perm('accounts.edit_order_payment_status_others'):
                    return Response(
                        {"error": "You do not have permission to edit order payment status."},
                        status=status.HTTP_403_FORBIDDEN
                    )
            try:
                payment_status_obj = Payment_Status.objects.get(id=new_payment_status_id)
                order.payment_status = payment_status_obj
                updated_fields["payment_status"] = new_payment_status_id
            except Payment_Status.DoesNotExist:
                return Response(
                    {"error": "Invalid payment_status_id"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
        # Save only if any field is updated
        if updated_fields:
            order.save()
            return Response(
                {
                    "success": True,
                    "message": "Order updated successfully",
                    "updated_fields": updated_fields,
                },
                status=status.HTTP_200_OK,
            )

        return Response(
            {"error": "No valid fields provided for update"},
            status=status.HTTP_400_BAD_REQUEST,
        )

class OrderLogListView(generics.ListAPIView):
    """
    API View to retrieve order logs by order ID.
    """
    serializer_class = OrderLogSerializer

    def get_queryset(self):
        """
        Fetch order logs based on the provided order ID.
        """
        order_id = self.kwargs.get('order_id')
        return OrderLogModel.objects.filter(order_id=order_id).order_by('-created_at')

    def list(self, request, *args, **kwargs):
        """
        Customize the response to return logs or a message if no logs are found.
        """
        queryset = self.get_queryset()
        if not queryset.exists():
            return Response(
                {"message": "No logs found for this order."},
                status=status.HTTP_404_NOT_FOUND
            )
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

class OrderMetricsAPIView(APIView):
    permission_classes = [IsAuthenticated,OrderPermissions]
    def get(self, request, *args, **kwargs):
        try:
            # Get the filter parameters from the request
            branch_id = request.query_params.get('branch', None)
            start_date = request.query_params.get('start_date', None)
            end_date = request.query_params.get('end_date', None)
            tl_id = request.query_params.get('tl_id', None)
            manager_id = request.query_params.get('manager_id', None)
            agent_id = request.query_params.get('agent_id', None)

            # Build the filter conditions
            filter_conditions = {}

            if branch_id:
                filter_conditions['branch_id'] = branch_id

            if start_date and end_date:
                try:
                    start_date = datetime.strptime(start_date, '%Y-%m-%d')
                    end_date = datetime.strptime(end_date, '%Y-%m-%d')
                    filter_conditions['created_at__range'] = [start_date, end_date]
                except ValueError:
                    return Response({
                        "success": False,
                        "message": "Invalid date format. Use YYYY-MM-DD."
                    }, status=status.HTTP_400_BAD_REQUEST)
            
            if manager_id:
                employees_under_manager = Employees.objects.filter(manager_id=manager_id)
                employee_ids = employees_under_manager.values_list('user_id', flat=True)
                filter_conditions['order_created_by_id__in'] = employee_ids

            if tl_id:
                employees_under_tl = Employees.objects.filter(teamlead_id=tl_id)
                employee_ids = employees_under_tl.values_list('user_id', flat=True)
                filter_conditions['order_created_by_id__in'] = employee_ids
            
            if agent_id:
                filter_conditions['order_created_by_id'] = agent_id
            
            filter_conditions['is_deleted'] = False
            # Get all orders based on filters
            orders = Order_Table.objects.filter(**filter_conditions)

            # Get specific order statuses
            accepted_status = OrderStatus.objects.filter(name="Accepted").first()
            rejected_status = OrderStatus.objects.filter(name="Rejected").first()
            no_response_status = OrderStatus.objects.filter(name="No Response").first()

            # Calculate metrics
            total_orders = orders.count()
            
            # Get daily target from UserTargetsDelails
            daily_target = 0
            if agent_id:
                agent_target = UserTargetsDelails.objects.filter(user__id=agent_id).first()
                if agent_target:
                    daily_target = agent_target.daily_target
            elif tl_id:
                tl_target = UserTargetsDelails.objects.filter(user__id=tl_id).first()
                if tl_target:
                    daily_target = tl_target.daily_target
            elif manager_id:
                manager_target = UserTargetsDelails.objects.filter(user__id=manager_id).first()
                if manager_target:
                    daily_target = manager_target.daily_target

            # Get counts for specific statuses
            accepted_orders = orders.filter(order_status=accepted_status).count() if accepted_status else 0
            rejected_orders = orders.filter(order_status=rejected_status).count() if rejected_status else 0
            no_response_orders = orders.filter(order_status=no_response_status).count() if no_response_status else 0

            # Calculate total leads (all orders that are not rejected)
            total_leads = orders.exclude(order_status=rejected_status).count() if rejected_status else total_orders

            response_data = {
                "success": True,
                "data": {
                    "total_orders": total_orders,
                    "daily_target": daily_target,
                    "total_leads": total_leads,
                    "accepted_orders": accepted_orders,
                    "rejected_orders": rejected_orders,
                    "no_response_orders": no_response_orders
                }
            }

            return Response(response_data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                "success": False,
                "message": f"An error occurred: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        

class ProductOrderSummaryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        order_status_name = request.query_params.get('order_status', 'Accepted')
        month = request.GET.get('month', '').lower()
        year = request.GET.get('year', '')

        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        if month and year:
            try:
                month = int(month)
                year = int(year)
                if month < 1 or month > 12:
                    raise ValueError("Month must be between 1 and 12")
                start_date = datetime(year, month, 1)
                end_date = datetime(year, month, calendar.monthrange(year, month)[1])
                # last_day = datetime.combine(last_day, time.max)
                # orders = orders.filter(created_at__range=(start_date, last_day))
            except ValueError as e:
                return Response({
                    "status": False,
                    "message": "Invalid month or year provided.",
                    "data": [],
                    "errors": str(e)
                }, status=status.HTTP_400_BAD_REQUEST)
        # Set default date range to this month's 1st day to today
        now = timezone.now()
        if not month:
            start_date = now.replace(day=1)
        if not month:
            end_date = now.date()
        start_date = datetime.combine(start_date, datetime.min.time())
        end_date = datetime.combine(end_date, datetime.max.time())
        # Get orders for the user's branch and company, with order status and date range filter
        orders = Order_Table.objects.filter(
            branch=user.profile.branch,
            company=user.profile.company,
            order_status__name=order_status_name,
            is_deleted=False
        ).filter(
            Q(created_at__range=(start_date, end_date)) |
            Q(updated_at__range=(start_date, end_date)),
            is_deleted=False,
        )
        order_details = OrderDetail.objects.filter(order__in=orders) \
            .values('product_id', 'product__product_name') \
            .annotate(
                total_quantity_sold=Sum('product_qty'),
                total_amount_sold=Sum('product_total_price')
            )

        return Response(list(order_details))

class ProductOrderSummaryView1(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        order_status_name = request.query_params.get('order_status', 'Accepted')
        month = request.query_params.get('month')
        year = request.query_params.get('year')

        # Step 1: Parse Date Range
        now = timezone.now()
        try:
            if month and year:
                month = int(month)
                year = int(year)
                if not (1 <= month <= 12):
                    raise ValueError("Month must be between 1 and 12")

                start_date = datetime(year, month, 1)
                end_date = datetime(year, month, calendar.monthrange(year, month)[1], 23, 59, 59)
            else:
                # Default to current month
                start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                end_date = now
        except ValueError as e:
            return Response({
                "status": False,
                "message": "Invalid month or year provided.",
                "data": [],
                "errors": str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

        # Step 2: Use JOIN instead of `order__in`
        order_details = (
            OrderDetail.objects
            .select_related('order', 'product')  # prefetch related objects
            .filter(
                order__branch=user.profile.branch,
                order__company=user.profile.company,
                order__order_status__name=order_status_name,
                order__is_deleted=False,
                order__created_at__range=(start_date, end_date)
            )
            .values('product_id', 'product__product_name')
            .annotate(
                total_quantity_sold=Sum('product_qty'),
                total_amount_sold=Sum('product_total_price')
            )
            .order_by('-total_quantity_sold')
        )

        return Response({
            "status": True,
            "message": "Product order summary fetched successfully.",
            "data": list(order_details),
            "errors": None
        })
class ScanOrderAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        order_id = request.data.get('order_id')
        order_type = request.data.get('order_type')
        remark = request.data.get('remark', 'Order status updated via scan')

        if not order_id or order_type is None:
            return Response({'error': 'order_id and order_type are required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = request.user
            branch = user.profile.branch
            company = user.profile.company
            orders = Order_Table.objects.filter(branch=branch, company=company, order_id=order_id)
        except Order_Table.DoesNotExist:
            return Response({'error': 'Order not found.'}, status=status.HTTP_404_NOT_FOUND)

        if not orders.exists():
            return Response({'error': 'No orders found matching the provided criteria.'}, status=status.HTTP_404_NOT_FOUND)

        for order in orders:
            # Case 1: Pickup Done
            if order_type == 1:
                pickup_status = ReturnType.objects.filter(status_code="1").first()

                if not pickup_status:
                    return Response({'error': 'Pickup status not configured in ReturnType.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

                if order.is_pickups == pickup_status:
                    return Response({'error': 'Order already marked as Pickup Done.'}, status=status.HTTP_400_BAD_REQUEST)
                order_status, created = OrderStatus.objects.get_or_create(
                                name='IN TRANSIT'
                                # branch=branch_id,
                                # company=company_id
                            )
                order.order_status = order_status
                order.is_pickups = pickup_status
                order.order_remark = remark
                order.save()

                # Deduct stock
                order_details = OrderDetail.objects.filter(order=order)
                for detail in order_details:
                    product = detail.product
                    if product.product_quantity >= detail.product_qty:
                        product.product_quantity -= detail.product_qty
                        product.save()
                    else:
                        return Response({'error': f'Insufficient stock for {product.product_name}'}, status=status.HTTP_400_BAD_REQUEST)

                # Log entry
                orderLogInsert({
                    "order": order.id,
                    "order_status": order.order_status.id if order.order_status else None,
                    "action_by": user.id,
                    "remark": remark
                })

                return Response({'status': 'Pickup marked as done and stock reduced.'})

            # Case 2: RTO Received
            elif order_type == 2:
                rto_status = ReturnType.objects.filter(status_code="2").first()
                if not rto_status:
                    return Response({'error': 'RTO status not configured in ReturnType.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

                if order.is_pickups == rto_status:
                    return Response({'error': 'Order already marked as RTO Received.'}, status=status.HTTP_400_BAD_REQUEST)
                order_status, created = OrderStatus.objects.get_or_create(
                                name='RTO DELIVERED'
                                # branch=branch_id,
                                # company=company_id
                            )
                order.order_status = order_status
                order.is_pickups = rto_status
                order.order_remark = remark
                order.save()

                # Restore stock
                order_details = OrderDetail.objects.filter(order=order)
                for detail in order_details:
                    product = detail.product
                    product.product_quantity += detail.product_qty
                    product.save()

                # Log entry
                orderLogInsert({
                    "order": order.id,
                    "order_status": order.order_status.id if order.order_status else None,
                    "action_by": user.id,
                    "remark": remark
                })

                return Response({'status': 'RTO received and stock restored.'})

            # Case 3: Any other type — mark as exception
            else:
                order_status, created = OrderStatus.objects.get_or_create(
                                    name='EXCEPTION'
                                    # branch=branch_id,
                                    # company=company_id
                                )
                order.order_status = order_status
                rto_status = ReturnType.objects.filter(status_code=str(order_type)).first()
                if not rto_status:
                    return Response({'error': 'RTO status not configured in ReturnType.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                exception_status = OrderStatus.objects.filter(name__iexact="Exception").first()
                if not exception_status:
                    return Response({'error': 'Exception status not configured in OrderStatus.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                order.is_pickups = rto_status
                order.order_status = exception_status
                order.order_remark = remark
                order.save()

                # Log entry
                orderLogInsert({
                    "order": order.id,
                    "order_status": exception_status.id,
                    "action_by": user.id,
                    "remark": remark
                })

                return Response({'status': 'Order marked as exception with no stock operations.'})

        return Response({'error': 'Unexpected error occurred.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


        

class OrderStatusWorkflowViewSet(viewsets.ModelViewSet):
    serializer_class = OrderStatusWorkflowSerializer
    queryset = OrderStatusWorkflow.objects.all()
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        order_status_name = request.data.get('order_status')
        shipment_vendor_name = request.data.get('shipmentvendor')
        allow_status_ids = request.data.get('allow_status', [])

        # Get related objects
        order_status = get_object_or_404(OrderStatus, name=order_status_name)
        shipment_vendor = get_object_or_404(ShipmentVendor, name=shipment_vendor_name)
        allow_status_objs = AllowStatus.objects.filter(id__in=allow_status_ids)

        # Create or update the workflow
        workflow, created = OrderStatusWorkflow.objects.get_or_create(
            order_status=order_status,
            shipment_vendor=shipment_vendor
        )
        workflow.allow_status.set(allow_status_objs)

        serializer = self.get_serializer(workflow)
        return Response(serializer.data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)
    
    def get_queryset(self):
        queryset = OrderStatusWorkflow.objects.all()
        shipment_vendor_id = self.request.query_params.get("shipment_vendor")

        if shipment_vendor_id:
            queryset = queryset.filter(shipment_vendor_id=shipment_vendor_id)

        return queryset

class AllowStatusViewSet(viewsets.ModelViewSet):
    queryset = AllowStatus.objects.all()
    serializer_class = AllowStatusSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = AllowStatus.objects.all()
        shipment_vendor_id = self.request.query_params.get("shipment_vendor")

        if shipment_vendor_id:
            queryset = queryset.filter(shipment_vendor_id=shipment_vendor_id)

        return queryset

class ReturnTypeViewSet(viewsets.ModelViewSet):
    queryset = ReturnType.objects.all()
    serializer_class = ReturnTypeSerializer
    permission_classes = [IsAuthenticated]











from django.shortcuts import get_object_or_404


class LableLayoutAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, id=None):
        user = request.user
        usertype = user.profile.user_type.lower() 


        if id:
            layout = get_object_or_404(LableLayout, id=id)
            serializer = LableLayoutSerializer(layout)
            return Response(serializer.data)

      
        layouts = LableLayout.objects.all()

        if usertype in ['admin', 'superadmin']:
            branch_id = request.GET.get('branch_id')
            company_id = request.GET.get('company_id')

          
            if not branch_id:
                branch_id = user.profile.branch.id
            if not company_id:
                company_id = user.profile.company.id

            layouts = layouts.filter(branch_id=branch_id, company_id=company_id)

        elif usertype == 'agent':
            
            branch_id = user.profile.branch.id
            company_id = user.profile.company.id
            layouts = layouts.filter(branch_id=branch_id, company_id=company_id)

        else:
            return Response(
                {"detail": "Unauthorized user type."},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = LableLayoutSerializer(layouts, many=True)
        return Response(serializer.data)

    def post(self, request):

        user = request.user

        branch=user.profile.branch
        company=user.profile.company

        serializer = LableLayoutSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(branch=branch, company=company) 
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, id=None):
        if not id:
            return Response({"detail": "ID required for update."}, status=status.HTTP_400_BAD_REQUEST)
        layout = get_object_or_404(LableLayout, id=id)
        serializer = LableLayoutSerializer(layout, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, id=None):
        if not id:
            return Response({"detail": "ID required for partial update."}, status=status.HTTP_400_BAD_REQUEST)
        layout = get_object_or_404(LableLayout, id=id)
        serializer = LableLayoutSerializer(layout, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, id=None):
        if not id:
            return Response({"detail": "ID required for deletion."}, status=status.HTTP_400_BAD_REQUEST)
        layout = get_object_or_404(LableLayout, id=id)
        layout.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)





class LableInvoiceAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, id=None):
        user = request.user
        usertype = user.profile.user_type.lower() 


        if id:
            invoice = get_object_or_404(invoice_layout, id=id)
            serializer = LableinvoiceSerializer(invoice)
            return Response(serializer.data)

      
        invoice = invoice_layout.objects.all()

        if usertype in ['admin', 'superadmin']:
            branch_id = request.GET.get('branch_id')
            company_id = request.GET.get('company_id')

          
            if not branch_id:
                branch_id = user.profile.branch.id
            if not company_id:
                company_id = user.profile.company.id

            invoice = invoice.filter(branch_id=branch_id, company_id=company_id)

        elif usertype == 'agent':
            
            branch_id = user.profile.branch.id
            company_id = user.profile.company.id
            invoice = invoice.filter(branch_id=branch_id, company_id=company_id)

        else:
            return Response(
                {"detail": "Unauthorized user type."},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = LableinvoiceSerializer(invoice, many=True)
        return Response(serializer.data)

    def post(self, request):

        user = request.user

        branch=user.profile.branch
        company=user.profile.company

        serializer = LableinvoiceSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(branch=branch, company=company) 
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, id=None):
        if not id:
            return Response({"detail": "ID required for update."}, status=status.HTTP_400_BAD_REQUEST)
        invoice = get_object_or_404(invoice_layout, id=id)
        serializer = LableinvoiceSerializer(invoice, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, id=None):
        if not id:
            return Response({"detail": "ID required for partial update."}, status=status.HTTP_400_BAD_REQUEST)
        invoice = get_object_or_404(invoice_layout, id=id)
        serializer = LableinvoiceSerializer(invoice, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, id=None):
        if not id:
            return Response({"detail": "ID required for deletion."}, status=status.HTTP_400_BAD_REQUEST)
        invoice = get_object_or_404(invoice_layout, id=id)
        invoice.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class CSVProductUploadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if 'file' not in request.FILES:
            return Response({"Error": "No CSV file provided"}, status=status.HTTP_400_BAD_REQUEST)

        csv_file = request.FILES['file']
        if not csv_file.name.endswith('.csv'):
            return Response({"Error": "Uploaded file is not a CSV"}, status=status.HTTP_400_BAD_REQUEST)

        file_data = csv_file.read().decode('utf-8')
        io_string = io.StringIO(file_data)
        reader = csv.DictReader(io_string)

        success_count = 0
        errors = []

        for index, row in enumerate(reader, start=1):
            try:
                # Try to create each product
                createProduct(row, request.user.id)
                success_count += 1
            except Exception as e:
                errors.append({
                    "row": index,
                    "error": str(e),
                    "data": row
                })

        return Response({
            "Success": True,
            "message": f"{success_count} products uploaded successfully.",
            "errors": errors
        }, status=status.HTTP_200_OK)



class NotificationsConfigViewSet(viewsets.ModelViewSet):
    queryset = SmsConfig.objects.all()
    serializer_class = NotificationsConfigSerializer

    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        usertype = user.profile.user_type.lower() 
        notification_type = self.request.query_params.get('notification_type')

        # Superadmin: return all
        if usertype == 'superadmin':
            return SmsConfig.objects.all()

        # Others: filter by company and optional notification_type
        company_id = user.profile.company.id
        queryset = SmsConfig.objects.filter(company_id=company_id)

        if notification_type:
            queryset = queryset.filter(notification_type=notification_type)
            
        return queryset
    
    def create(self, request, *args, **kwargs):
        """
        Handle creating an OrderStatus instance.
        """
        user = request.user
        data = request.data.copy() 
        # data['branch'] = user.profile.branch.id
        data['company'] = user.profile.company.id

        serializer = self.get_serializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)




class ExternalOrderCreateView(APIView):
    def post(self, request, *args, **kwargs):
        try:
            # Get and remove api_key before processing
            api_key = request.data.get("api_key")
            if not api_key:
                return Response({"error": "API key is required."}, status=status.HTTP_400_BAD_REQUEST)

            try:
                company_user = CompanyUserAPIKey.objects.select_related('user').get(api_key=api_key,status=True)
            except CompanyUserAPIKey.DoesNotExist:
                return Response({"error": "Invalid API key."}, status=status.HTTP_401_UNAUTHORIZED)

            time_threshold = timezone.now() - timedelta(hours=48)
            network_ip = request.data.get("network_ip")
            recent_orders_count = Order_Table.objects.filter(
                network_ip=network_ip,
                created_at__gte=time_threshold,
                is_deleted=False
            ).count()

            if recent_orders_count >= 2:
                 return Response({"error": "You have already created 2 orders in the last 48 hours. Please try again later"}, status=status.HTTP_401_UNAUTHORIZED)
            user = company_user.user
            request.user = user

            # Remove api_key from data to avoid polluting your order logic
            mutable_data = request.data.copy()
            mutable_data.pop("api_key", None)
            request._full_data = mutable_data  # Override request.data with cleaned data

            mutable_data, error_response = attach_product_details(mutable_data)
            if error_response:
                return error_response
            
            mutable_data.pop("product_id", None)
            mutable_data.pop("proudct_qty", None)
            payment_type_id = mutable_data["payment_type"]
            payment_type = Payment_Type.objects.filter(id=payment_type_id).first()
            if not payment_type:
                return Response({"error": "Invalid payment type"}, status=status.HTTP_400_BAD_REQUEST)

            total_amount = float(mutable_data['total_amount'])
            prepaid_amount = mutable_data.get("prepaid_amount", 0.0)

            branch_id = user.profile.branch
            company_id = user.profile.company
            
            data = checkServiceability(
                request.user.profile.branch_id,
                request.user.profile.company_id,
                {"pincode": mutable_data["customer_postal"], "mobile": mutable_data['customer_phone'],"re_order":0},
            )
            if data and isinstance(data, list) and len(data) > 0:
                delivery_state = data[0].get('delivery_state')
                delivery_city = data[0].get('delivery_city')
            else:
                delivery_state = None
                delivery_city = None
                return Response({"error": "Not Serviceability"}, status=status.HTTP_400_BAD_REQUEST)
            
            state = Customer_State.objects.get(name=delivery_state)
            state_id = state.id
            payment_type_name = payment_type.name.lower()
            order_status = OrderStatus.objects.filter(name="Pending").first()
            if order_status:
                mutable_data["order_status"] = order_status.id
            
            if payment_type_name == "partial payment":
                payment_status = Payment_Status.objects.filter(name="Partial Payment Received").first()
            elif payment_type_name == "prepaid payment":
                payment_status = Payment_Status.objects.filter(name="Payment Received").first()
            else:
                payment_status = Payment_Status.objects.filter(name="Payment Pending").first()

            if payment_status:
                mutable_data["payment_status"] = payment_status.id

            payment_setting = OrderValueSetting.objects.filter(
                payment_type_id=payment_type,
                company_id=company_id,
                branch_id=branch_id
            ).first()

            amount_to_check = prepaid_amount if payment_type_name == "partial payment" else total_amount
            if payment_setting and float(payment_setting.amount) > amount_to_check:
                return Response(
                    {
                        "Success": False,
                        "Error": f"Order value must be greater than {payment_setting.amount}.",
                        "message": f"We can't proceed. Ensure the order value is greater than {payment_setting.amount}."
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            mutable_data["order_created_by"] = user.id
            mutable_data["customer_state"] = state_id
            mutable_data['customer_city'] = delivery_city
            order_serializer = OrderTableSerializer(data=mutable_data)
            if order_serializer.is_valid():
                create_order_response = createOrders(mutable_data, user.id)
                return Response(
                    {
                        "Success": True,
                        "data": OrderTableSerializer(create_order_response).data,
                    },
                    status=status.HTTP_201_CREATED,
                )
            return Response(order_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        except Customer_State.DoesNotExist:
            return Response({"Success": False, "Error": "Customer state not found."}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({"Success": False, "Error": str(e)}, status=status.HTTP_400_BAD_REQUEST)




class FilterOrdersCreatedView(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]  # Replace with actual permissions
    pagination_class = FilterOrdersPagination  # Adjust as necessary
    def get_date_range(self, request):
        """Extract and validate the date range from request.data (POST body)."""
        date_range = request.data.get('date_range')
        
        if date_range:
            if isinstance(date_range, str):
                date_range = date_range.split(' ')
                if len(date_range) != 2:
                    raise ValueError("Date Range invalid")

                start_date = datetime.fromisoformat(date_range[0]).date()
                end_date = datetime.fromisoformat(date_range[1]).date()
            elif isinstance(date_range, dict):
                start_date = date_range.get("start_date")
                end_date = date_range.get("end_date", datetime.now().strftime('%Y-%m-%d'))

                start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
                end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
            else:
                raise ValueError("Invalid date_range format.")
        else:
            today = datetime.now().date()
            start_date = today
            end_date = today

        start_datetime = timezone.make_aware(datetime.combine(start_date, time.min))
        end_datetime = timezone.make_aware(datetime.combine(end_date, time.max))

        return start_datetime, end_datetime
    def create(self, request):
        filters = request.data
        if not filters:
            raise ValueError("No filters provided")
        queryset = Order_Table.objects.filter(is_deleted=False).order_by("-created_at")

        filter_conditions = Q()

        # Mapping API fields to model fields
        filterable_fields = {
            "order_id": "order_id",
            "awb": "order_wayBill",
            "phone_no": "customer_phone",
            "payment_type": "payment_type__id",  # Assuming payment_type has a name field
            "customer_state__id": "state", 
            "city":"customer_city",
            "zone": "zone",
                 # Assuming customer_state has a name field
        }

        # Apply filters for exact matches
        for api_field, model_field in filterable_fields.items():
            value = filters.get(api_field)
            if value is not None:
                filter_conditions &= Q(**{model_field: filters[api_field]})

        # Additional manual adjustments
        # if "product_name" in filters:
        #     product_name = filters["product_name"]
        #     # Adjust based on JSON structure
        #     filter_conditions &= Q(product_details__icontains=product_name)
        if filters.get("product_id") is not None:
            product_id = filters["product_id"]
            # Filter orders that have related OrderDetail entries with the specified product_id
            filter_conditions &= Q(orderdetail__product_id=product_id)
        if filters.get("order_status") is not None:
            order_status = filters["order_status"]
            if order_status == "repeat":
                filter_conditions &= Q(repeat_order=1)  # Repeat Orders

            elif order_status == "running":
                today = now().date()
                start_datetime, end_datetime =  self.get_date_range(request)
                filter_conditions &= Q(created_at__range=(start_datetime, end_datetime))
                
            elif isinstance(order_status, int):
                filter_conditions &= Q(order_status__id=order_status)
            elif isinstance(order_status, str):
                filter_conditions &= Q(order_status__name__icontains=order_status)
            else:
                return Response({"detail": "Invalid order_status format."}, status=status.HTTP_400_BAD_REQUEST)
        if filters.get("agent_name") is not None:
            agent_name = filters["agent_name"]
            filter_conditions &= Q(order_created_by__username__icontains=agent_name)| Q(updated_by__username__icontains=agent_name)
        if filters.get("user_id") is not None:
            user_id = filters["user_id"]
            filter_conditions &= Q(order_created_by=user_id) | Q(updated_by=user_id)
        
        # Handle date range filtering
        if filters.get("date_range") is not None:
            date_range = filters["date_range"]
            start_date = date_range.get("start_date")
            end_date = date_range.get("end_date", datetime.now().strftime('%Y-%m-%d'))

            # Convert to aware datetime objects
            if start_date and end_date:
                try:
                    start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
                    start_date = timezone.make_aware(datetime.combine(start_date, datetime.min.time()))
                    end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
                    end_date = timezone.make_aware(datetime.combine(end_date, datetime.max.time()))
                    filter_conditions &= Q(created_at__range=(start_date, end_date))
                    
                    # filter_conditions &= (Q(created_at__gte=start_date) | Q(updated_at__gte=start_date))
                except ValueError:
                    return Response({"detail": "Invalid start_date format. Use YYYY-MM-DD."}, status=status.HTTP_400_BAD_REQUEST)

            # if end_date:
            #     try:
            #         end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
            #         end_date = timezone.make_aware(datetime.combine(end_date, datetime.max.time()))
            #         filter_conditions &= (Q(created_at__lte=end_date) | Q(updated_at__lte=end_date))
            #     except ValueError:
            #         return Response({"detail": "Invalid end_date format. Use YYYY-MM-DD."}, status=status.HTTP_400_BAD_REQUEST)
        # Apply the filter conditions to the queryset
        queryset = queryset.filter(filter_conditions)

        # Apply pagination and serialize the queryset
        paginator = self.pagination_class()
        paginated_queryset = paginator.paginate_queryset(queryset, request)
        serializer = FilterOrdersSerializer(paginated_queryset, many=True)
        return paginator.get_paginated_response(serializer.data)


from django.utils.dateparse import parse_date
class FilteredOrderViewSet(viewsets.ViewSet):

    def list(self, request):
        status_name = request.query_params.get('status')       # filter by status name (not ID)
        from_date = request.query_params.get('from_date')      # YYYY-MM-DD
        to_date = request.query_params.get('to_date')          # YYYY-MM-DD

        queryset = Order_Table.objects.filter(is_deleted=False).order_by('-created_at')


        if status_name:
            queryset = queryset.filter(order_status__name__icontains=status_name)

        if from_date:
            queryset = queryset.filter(created_at__date__gte=parse_date(from_date))

        if to_date:
            queryset = queryset.filter(created_at__date__lte=parse_date(to_date))

        serializer = OrderTableSerializer(queryset, many=True)
        return Response({
            "success": True,
            "message": "Filtered order list by status name and date",
            "data": serializer.data
        }, status=status.HTTP_200_OK)


class ChangeOrderStatusAPIView(APIView):
    def post(self, request):
        serializer = OrderStatusUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        order_ids = serializer.validated_data['order_ids']

        try:
            accepted_status = OrderStatus.objects.get(name__iexact='Accepted')
        except OrderStatus.DoesNotExist:
            return Response({"error": "Accepted status not found."}, status=status.HTTP_400_BAD_REQUEST)

        orders = Order_Table.objects.filter(order_id__in=order_ids)

        if not orders.exists():
            return Response({"error": "No matching orders found."}, status=status.HTTP_404_NOT_FOUND)

        updated_orders = []
        for order in orders:
            order.order_status = accepted_status
            order.save()
            updated_orders.append(order.order_id)

        return Response({
            "message": "Orders updated successfully.",
            "updated_order_ids": updated_orders
        }, status=status.HTTP_200_OK)


class FilterOrdersView1(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    pagination_class = FilterOrdersPagination

    def get_date_range(self, request):
        date_range = request.query_params.get('date_range')
        try:
            if date_range:
                if isinstance(date_range, str):
                    date_range = date_range.split(' ')
                    if len(date_range) != 2:
                        raise ValueError("Date range invalid")
                    start_date = datetime.fromisoformat(date_range[0]).date()
                    end_date = datetime.fromisoformat(date_range[1]).date()
                elif isinstance(date_range, dict):
                    start_date = date_range.get("start_date")
                    end_date = date_range.get("end_date", datetime.now().strftime('%Y-%m-%d'))
                    start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
                    end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
                else:
                    raise ValueError("Invalid date_range format.")
            else:
                today = datetime.now().date()
                start_date = end_date = today

            start_datetime = timezone.make_aware(datetime.combine(start_date, time.min))
            end_datetime = timezone.make_aware(datetime.combine(end_date, time.max))
            return start_datetime, end_datetime

        except Exception as e:
            return None, None  # Could also raise an error if needed

    def _scope_queryset(self, qs, user):
        agent_ids = Employees.objects.filter(manager=user.id).values_list('user', flat=True)
        mgr_ids = Employees.objects.filter(Q(teamlead__in=agent_ids) | Q(user=user.id)).values_list('user', flat=True)
        mgr = set(mgr_ids) | set(agent_ids)
        tl_ids = list(Employees.objects.filter(teamlead=user.id).values_list('user', flat=True))
        tl_ids.append(user.id)

        if user.profile.user_type in ["admin", "superadmin"]:
            return qs
        elif user.has_perm("accounts.view_all_order_others"):
            return qs
        elif user.has_perm("accounts.view_manager_order_others"):
            return qs.filter(Q(order_created_by__in=mgr) | Q(updated_by__in=mgr))
        elif user.has_perm("accounts.view_teamlead_order_others"):
            return qs.filter(Q(order_created_by__in=tl_ids) | Q(updated_by__in=tl_ids))
        elif user.has_perm("accounts.view_own_order_others"):
            return qs.filter(Q(order_created_by=user.id) | Q(updated_by=user.id))
        else:
            return qs.none()

    def list(self, request, pk=None):
        filters = request.query_params
        branch = request.user.profile.branch
        company = request.user.profile.company

        queryset = Order_Table.objects.filter(
        branch=branch,
        company=company,
        is_deleted=False
    ).order_by("-created_at")
        filter_conditions = Q()

        # Filter by basic fields
        filterable_fields = {
            "order_id": "order_id",
            "awb": "order_wayBill",
            "phone_no": "customer_phone",
            "payment_type": "payment_type__id",
            "city": "customer_city",
            "zone": "zone",
        }

        for api_field, model_field in filterable_fields.items():
            value = filters.get(api_field)
            if value:
                filter_conditions &= Q(**{model_field: value})

        # Product filter
        if filters.get("product_id"):
            filter_conditions &= Q(orderdetail__product_id=filters["product_id"])

        # State filter
        if filters.get("state_id"):
            filter_conditions &= Q(customer_state__id=filters["state_id"])

        # Pickup point filter
        if filters.get("pick_up_point_id"):
            filter_conditions &= Q(pick_up_point__id=filters["pick_up_point_id"])

        # Order status
        if filters.get("order_status"):
            order_status = filters["order_status"]
            if order_status == "repeat":
                filter_conditions &= Q(repeat_order=1)
            elif order_status == "running":
                start_datetime, end_datetime = self.get_date_range(request)
                if start_datetime and end_datetime:
                    filter_conditions &= (
                        Q(created_at__range=(start_datetime, end_datetime)) |
                        Q(updated_at__range=(start_datetime, end_datetime))
                    )
            else:
                try:
                    order_status_int = int(order_status)
                    filter_conditions &= Q(order_status__id=order_status_int)
                except (ValueError, TypeError):
                    filter_conditions &= Q(order_status__name__icontains=str(order_status))
        if filters.get('counter'):
            counter = filters['counter']
            if '+' in counter:  
                # Example: "3+"
                try:
                    base_value = int(counter.replace('+', ''))
                    filter_conditions &= Q(ofd_counter__gt=base_value)
                except ValueError:
                    pass  # ignore invalid value
            else:
                # Normal number case: "1", "2", "3"
                try:
                    base_value = int(counter)
                    filter_conditions &= Q(ofd_counter=base_value)
                except ValueError:
                    pass  # ignore invalid value


        # Agent name
        if filters.get("agent_name"):
            filter_conditions &= Q(order_created_by__username__icontains=filters["agent_name"])

        # User ID filter (fixed parentheses)
        if filters.get("user_id"):
            user_id = filters["user_id"]
            filter_conditions &= Q(order_created_by=user_id) | Q(updated_by=user_id)

        # Date range filter (non-running)
        if filters.get("date_range") and filters.get("order_status") != "running":
            start_datetime, end_datetime = self.get_date_range(request)
            if start_datetime and end_datetime:
                filter_conditions &= (
                    Q(created_at__range=(start_datetime, end_datetime)) |
                    Q(updated_at__range=(start_datetime, end_datetime))
                )

        # Course repeated filter
        if str(filters.get("course")).lower() == "true":
            filter_conditions &= Q(course_order_repeated__gt=0)

        # Apply filters
        queryset = queryset.filter(filter_conditions).distinct()

        # Apply permission-based filtering
        queryset = self._scope_queryset(queryset, request.user)

        # Pagination
        paginator = self.pagination_class()
        paginated_queryset = paginator.paginate_queryset(queryset, request)
        serializer = OrderTableSerializer(paginated_queryset, many=True)

        return paginator.get_paginated_response(serializer.data)


class OrderPagination(pagination.PageNumberPagination):
    page_size_query_param = "page_size"
    max_page_size = 10000
    page_size = 50
# class OrderListView(APIView):
#     """
#     /orders/                 -> list (paginated)
#     /orders/<id>/            -> single order
#     Query params:
#         branch          int
#         month / year    int (1-12 / yyyy)
#         page / page_size int
#     """
#     permission_classes = [IsAuthenticated]
#     pagination_class = OrderPagination

#     # same mapping as before
#     TILES = {
#         "running_tile": None,
#         "pending_tile": "Pending",
#         "accepted_tile": "Accepted",
#         "rejected_tile": "Rejected",
#         "no_response_tile": "No Response",
#         "future_tile": "Future Order",
#         "non_serviceable_tile": "Non Serviceable",
#         "pendingspickup_tile": "PICKUP PENDING",
#         "in_transit_tile": "IN TRANSIT",
#         "ofd_tile": "OUT FOR DELIVERY",
#         "delivered_tile": "DELIVERED",
#         "initiatedrto": "RTO INITIATED",
#         "rtodelivered_tile": "RTO DELIVERED",
#         "exception_tile": "EXCEPTION",
#         "ndr_tile": "NDR",
#     }

#     # ----------------------------------------------------------
#     # 1. Build query filters
#     # ----------------------------------------------------------
#     def _filters(self, request):
#         branch = int(request.GET.get("branch", request.user.profile.branch_id))
#         company = request.user.profile.company
#         month = request.GET.get("month", "").lower()
#         year = request.GET.get("year", "")
#         filters = {"branch": branch, "company": company}

#         if month and year:
#             try:
#                 m, y = int(month), int(year)
#                 if not 1 <= m <= 12:
#                     raise ValueError
#                 first = timezone.make_aware(datetime(y, m, 1))
#                 last = timezone.make_aware(
#                     datetime(y, m, calendar.monthrange(y, m)[1], 23, 59, 59)
#                 )
#                 filters["created_at__range"] = (first, last)
#             except ValueError:
#                 raise ValueError("month must be 1-12 and year must be integer")
#         return filters

#     # ----------------------------------------------------------
#     # 2. Permission scopes
#     # ----------------------------------------------------------
#     def _scope_queryset(self, qs, user):
#         # user-id lists
#         agent_ids = list(user.__class__.objects.filter(manager=user.id).values_list('id', flat=True))
#         mgr = set(agent_ids) | set(
#             user.__class__.objects.filter(
#                 Q(teamlead__in=agent_ids) | Q(id=user.id)
#             ).values_list('id', flat=True)
#         )
#         tl = list(user.__class__.objects.filter(teamlead=user.id).values_list('id', flat=True))
#         tl.append(user.id)

#         # base permission filter
#         if user.user_type in ["admin", "superadmin"]:
#             pass
#         elif user.has_perm("accounts.view_all_order_others"):
#             pass
#         elif user.has_perm("accounts.view_manager_order_others"):
#             qs = qs.filter(Q(order_created_by__in=mgr) | Q(updated_by__in=mgr))
#         elif user.has_perm("accounts.view_teamlead_order_others"):
#             qs = qs.filter(Q(order_created_by__in=tl) | Q(updated_by__in=tl))
#         elif user.has_perm("accounts.view_own_order_others"):
#             qs = qs.filter(Q(order_created_by=user.id) | Q(updated_by=user.id))
#         else:
#             qs = qs.none()

#         # agent tile filter
#         if user.user_type == "agent":
#             tile_q = Q()
#             for suffix, status in self.TILES.items():
#                 scopes = Q()
#                 if user.has_perm(f"dashboard.view_all_dashboard_{suffix}"):
#                     scopes |= Q()
#                 if user.has_perm(f"dashboard.view_manager_dashboard_{suffix}"):
#                     scopes |= Q(order_created_by__in=mgr) | Q(updated_by__in=mgr)
#                 if user.has_perm(f"dashboard.view_teamlead_dashboard_{suffix}"):
#                     scopes |= Q(order_created_by__in=tl) | Q(updated_by__in=tl)
#                 if user.has_perm(f"dashboard.view_own_dashboard_{suffix}"):
#                     scopes |= Q(order_created_by=user.id) | Q(updated_by=user.id)

#                 if status is None:
#                     tile_q |= scopes
#                 else:
#                     tile_q |= scopes & Q(order_status__name=status)

#             qs = qs.filter(tile_q).distinct()
#         return qs

#     # ----------------------------------------------------------
#     # 3. Add permission flags once – no loops
#     # ----------------------------------------------------------
#     def _inject_permissions(self, data, user):
#         perms = {
#             "product_permission": user.has_perm("accounts.view_Product_Information_others"),
#             "payment_permission": user.has_perm("accounts.view_order_payment_status_others"),
#             "status_permission":  user.has_perm("accounts.view_order_status_tracking_others"),
#             "customer_permission": user.has_perm("accounts.view_customer_information_others"),
#         }
#         if user.user_type in ["admin", "superadmin"]:
#             perms = {k: True for k in perms}

#         for order in data:
#             order.update(perms)
#         return data

#     # ----------------------------------------------------------
#     # 4. GET (list or single)
#     # ----------------------------------------------------------
#     def get(self, request, *args, **kwargs):
#         pk = kwargs.get("id")
#         try:
#             filters = self._filters(request)
#         except ValueError as e:
#             return Response(
#                 {"status": False, "message": str(e), "data": [], "errors": str(e)},
#                 status=status.HTTP_400_BAD_REQUEST,
#             )

#         qs = Order_Table.objects.filter(**filters)
#         qs = self._scope_queryset(qs, request.user)

#         if pk is not None:
#             qs = qs.filter(id=pk)

#         qs = qs.prefetch_related("orderdetail_set")

#         paginator = self.pagination_class()
#         page_qs = paginator.paginate_queryset(qs, request)

#         serializer = OrderTableSerializer(page_qs, many=True)
#         data = serializer.data

#         # inject permission flags
#         data = self._inject_permissions(data, request.user)

#         # inject product details (already prefetched)
#         for order in data:
#             order["product_details"] = [
#                 OrderDetailSerializer(d).data
#                 for d in order.pop("orderdetail_set")
#             ]

#         if pk is not None:
#             return Response(
#                 {"status": True, "message": "Order retrieved", "data": data[0] if data else None, "errors": None},
#                 status=status.HTTP_200_OK,
#             )

#         return paginator.get_paginated_response(
#             {"status": True, "message": "Orders retrieved successfully", "data": data, "errors": None}
#         )

from django.contrib.auth import get_user_model
class OrderListView(APIView):
    permission_classes = [IsAuthenticated]
    pagination_class = OrderPagination

    TILES = {
        "running_tile": None,
        "pending_tile": "Pending",
        "accepted_tile": "Accepted",
        "rejected_tile": "Rejected",
        "no_response_tile": "No Response",
        "future_tile": "Future Order",
        "non_serviceable_tile": "Non Serviceable",
        "pendingspickup_tile": "PICKUP PENDING",
        "in_transit_tile": "IN TRANSIT",
        "ofd_tile": "OUT FOR DELIVERY",
        "delivered_tile": "DELIVERED",
        "initiatedrto": "RTO INITIATED",
        "rtodelivered_tile": "RTO DELIVERED",
        "exception_tile": "EXCEPTION",
        "ndr_tile": "NDR",
    }

    def _filters(self, request):
        branch = request.GET.get("branch", request.user.profile.branch_id)
        company = request.user.profile.company
        filters = {"branch": branch, "company": company}

        month = request.GET.get("month")
        year = request.GET.get("year")
        start_date = request.GET.get("start_date")
        end_date = request.GET.get("end_date")
        order_status_name = request.GET.get("order_status")

        awb = request.GET.get("awb")
        phone = request.GET.get("phone")
        payment_type = request.GET.get("payment_type")
        agent_id = request.GET.get("agent_id")
        order_id = request.GET.get("order_id")

        if awb:
            filters["order_wayBill__icontains"] = awb
        if phone:
            filters["customer_phone__icontains"] = phone
        if payment_type:
            filters["payment_type__name__icontains"] = payment_type
        if agent_id:
            filters["order_created_by__id"] = agent_id
        if order_id:
            filters["order_id"] = order_id

        today = timezone.now().date()
        start_dt = timezone.make_aware(datetime.combine(today, time.min))
        end_dt = timezone.make_aware(datetime.combine(today, time.max))

        try:
            if start_date and end_date:
                start_dt = timezone.make_aware(datetime.strptime(start_date, "%Y-%m-%d"))
                end_dt = timezone.make_aware(
                    datetime.strptime(end_date, "%Y-%m-%d") + timedelta(hours=23, minutes=59, seconds=59)
                )
            elif month and year:
                m, y = int(month), int(year)
                if not 1 <= m <= 12:
                    raise ValueError("Month must be between 1-12")
                start_dt = timezone.make_aware(datetime(y, m, 1))
                end_dt = timezone.make_aware(datetime(y, m, calendar.monthrange(y, m)[1], 23, 59, 59))
        except ValueError:
            raise ValueError("Invalid date/month/year format")

        if order_status_name:
            if order_status_name.lower() != "running":
                filters["order_status__name__iexact"] = order_status_name.strip()

        return filters, order_status_name, start_dt, end_dt

    def _scope_queryset(self, qs, user, status_name=None):
        agent_ids = Employees.objects.filter(manager=user.id).values_list('user', flat=True)
        mgr_ids = Employees.objects.filter(Q(teamlead__in=agent_ids) | Q(user=user.id)).values_list('user', flat=True)
        mgr = set(mgr_ids) | set(agent_ids)
        tl_ids = list(Employees.objects.filter(teamlead=user.id).values_list('user', flat=True))
        tl_ids.append(user.id)
        
        if user.profile.user_type in ["admin", "superadmin"]:
            print("3078")
            pass
        elif user.has_perm("accounts.view_all_order_others"):
            print("3081")
            pass
        # elif user.has_perm("accounts.view_manager_order_others"):
        #     print("3084")
        #     qs = qs.filter(Q(order_created_by__in=mgr) | Q(updated_by__in=mgr))
        # elif user.has_perm("accounts.view_teamlead_order_others"):
        #     print("3097")
        #     qs = qs.filter(Q(order_created_by__in=tl_ids) | Q(updated_by__in=tl_ids))
        # elif user.has_perm("accounts.view_own_order_others"):
        #     print("3090")
        #     qs = qs.filter(Q(order_created_by=user.id) | Q(updated_by=user.id))
        # else:
        #     print("3093")
            # return qs.none()
        if user.profile.user_type == "agent":
            tile_q = Q()
            if status_name:
                for suffix, tile_status in self.TILES.items():
                    if tile_status and tile_status.lower() == status_name.lower():
                        status_q = Q()
                        print(suffix,user.has_perm(f"dashboard.view_all_dashboard_{suffix}"),f"dashboard.view_all_dashboard_{suffix}")
                        if user.has_perm(f"dashboard.view_all_dashboard_{suffix}"):
                            status_q |= Q()
                        elif user.has_perm(f"dashboard.view_manager_dashboard_{suffix}"):
                            status_q |= Q(order_created_by__in=mgr) | Q(updated_by__in=mgr)
                        elif user.has_perm(f"dashboard.view_teamlead_dashboard_{suffix}"):
                            status_q |= Q(order_created_by__in=tl_ids) | Q(updated_by__in=tl_ids)
                        elif user.has_perm(f"dashboard.view_own_dashboard_{suffix}"):
                            status_q |= Q(order_created_by=user.id) | Q(updated_by=user.id)

                        if status_q:
                            if tile_status is None:
                                return qs.filter(status_q).distinct()
                            else:
                                return qs.filter(status_q & Q(order_status__name=tile_status)).distinct()
                return qs
            else:
                for suffix, tile_status in self.TILES.items():
                    print(suffix,user.has_perm(f"dashboard.view_all_dashboard_{suffix}"),f"dashboard.view_all_dashboard_{suffix}")
                    scopes = Q()
                    if user.has_perm(f"dashboard.view_all_dashboard_{suffix}"):
                        scopes |= Q()
                    elif user.has_perm(f"dashboard.view_manager_dashboard_{suffix}"):
                        scopes |= Q(order_created_by__in=mgr) | Q(updated_by__in=mgr)
                    elif user.has_perm(f"dashboard.view_teamlead_dashboard_{suffix}"):
                        scopes |= Q(order_created_by__in=tl_ids) | Q(updated_by__in=tl_ids)
                    elif user.has_perm(f"dashboard.view_own_dashboard_{suffix}"):
                        scopes |= Q(order_created_by=user.id) | Q(updated_by=user.id)
                    print('user.has_perm(f"dashboard.view_all_dashboard_{suffix}")')
                    # print(scopes,"--------------3123")
                    if scopes:
                        if tile_status is None:
                            tile_q |= scopes
                        else:
                            tile_q |= scopes & Q(order_status__name=tile_status)

                return qs.filter(tile_q).distinct()

        return qs

    def _inject_permissions(self, orders, user):
        is_admin = user.profile.user_type in ["admin", "superadmin"]
        perms = {
            "product_permission": is_admin or user.has_perm("accounts.view_Product_Information_others"),
            "payment_permission": is_admin or user.has_perm("accounts.view_order_payment_status_others"),
            "status_permission": is_admin or user.has_perm("accounts.view_order_status_tracking_others"),
            "customer_permission": is_admin or user.has_perm("accounts.view_customer_information_others"),
        }
        for order in orders:
            order.update(perms)
        return orders

    def get(self, request, *args, **kwargs):
        pk = kwargs.get("id")
        try:
            filters, status_name, start_dt, end_dt = self._filters(request)
        except ValueError as e:
            return Response(
                {"status": False, "message": str(e), "data": [], "errors": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        qs = (
                Order_Table.objects
                .filter(**filters)
                .select_related("order_status", "company", "branch")
                .prefetch_related("orderdetail_set")
                .order_by("-created_at")
            )

        if status_name and status_name.lower() == "running":
            if request.user.profile.user_type == "agent" and request.user.has_perm('accounts.edit_order_others'):
                qs = qs.filter(Q(created_at__range=(start_dt, end_dt)) | Q(updated_at__range=(start_dt, end_dt)))
            else:
                qs = qs.filter(created_at__range=(start_dt, end_dt))
        else:
            if start_dt and end_dt:
                if request.user.profile.user_type == "agent" and request.user.has_perm('accounts.edit_order_others'):
                    qs = qs.filter(Q(created_at__range=(start_dt, end_dt)) | Q(updated_at__range=(start_dt, end_dt)))
                else:    
                    qs = qs.filter(created_at__range=(start_dt, end_dt))
        qs = self._scope_queryset(qs, request.user, status_name)
        
         # Add ordering: newest first (reverse chronological order by date and time)
        # qs = qs.order_by('-created_at', '-id')
        # print(qs,"0---------------------3178")
        if pk:
            qs = qs.filter(id=pk)

        paginator = self.pagination_class()
        paginated_qs = paginator.paginate_queryset(qs, request)

        serializer = OrderTableSerializer(paginated_qs, many=True)
        data = serializer.data
        data = self._inject_permissions(data, request.user)

        for i, order_obj in enumerate(paginated_qs):
            data[i]["product_details"] = OrderDetailSerializer(order_obj.orderdetail_set.all(), many=True).data

        if pk:
            return Response({
                "status": True,
                "message": "Order retrieved successfully",
                "data": data[0] if data else None,
                "errors": None,
            })

        return paginator.get_paginated_response({
            "status": True,
            "message": "Orders retrieved successfully",
            "data": data,
            "errors": None
        })



class OrderFiltersView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        branches = Branch.objects.filter(company=request.user.profile.company).values("id", "name")
        years = list(Order_Table.objects.dates('created_at', 'year').values_list('year', flat=True).distinct())
        months = list(range(1, 13))
        statuses = OrderStatus.objects.values_list("name", flat=True)

        return Response({
            "branches": list(branches),
            "years": years,
            "months": months,
            "statuses": list(statuses),
        })

from calendar import monthrange
class CreateRepeatOrderAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, order_id):
        try:
            original_order = Order_Table.objects.get(id=order_id, is_deleted=False)
        except Order_Table.DoesNotExist:
            return Response({"error": "Original order not found"}, status=status.HTTP_404_NOT_FOUND)

        # ✅ Calculate next course order count
        repeat_count = Order_Table.objects.filter(reference_order=original_order).count()
        next_course_order_count = repeat_count + 1  

        # ✅ Prepare repeat order data dictionary
        repeat_data = {
            "network_ip": original_order.network_ip,
            "customer_name": original_order.customer_name,
            "customer_parent_name": original_order.customer_parent_name,
            "customer_phone": original_order.customer_phone,
            "customer_alter_phone": original_order.customer_alter_phone,
            "customer_email": original_order.customer_email,
            "customer_address": original_order.customer_address,
            "customer_postal": original_order.customer_postal,
            "customer_city": original_order.customer_city,
            "customer_state": original_order.customer_state.id,
            "customer_country": original_order.customer_country,
            "product_details": original_order.product_details,  # list of products
            "total_amount": original_order.total_amount,
            "gross_amount": original_order.gross_amount,
            "discount": original_order.discount,
            "prepaid_amount": original_order.prepaid_amount,
            "cod_amount": original_order.cod_amount,
            "payment_type": original_order.payment_type.id,
            "payment_status": original_order.payment_status.id,
            "order_status": original_order.order_status.id,
            "order_ship_by": original_order.order_ship_by,
            "order_wayBill": None,
            "order_remark": f"Repeat Order #{next_course_order_count} created",
            "repeat_order": 1,
            "is_booked": 0,
            "is_scheduled": 0,
            "service_provider": original_order.service_provider,
            "call_id": original_order.call_id,
            "course_order": 1,  # fresh repeat always starts at 1
            "course_order_count": next_course_order_count,
            "reference_order": original_order.id,
            "product_qty": original_order.product_qty,
            "shipping_charges": original_order.shipping_charges,
            "order_created_by": request.user.id
        }

        order_status = OrderStatus.objects.filter(name="Pending").first()
        if order_status:
            repeat_data["order_status"] = order_status.id

        # ✅ Call createOrders function (reusing logic)
        try:
            new_order = createOrders(repeat_data, request.user.id)

            # ✅ Update original order progress
            original_order.course_order_count = next_course_order_count    # planned repeats
            original_order.course_order = (original_order.course_order or 0) + 1  # completed repeats
            original_order.save(update_fields=["course_order_count", "course_order"])

        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            "message": "Repeat order created successfully",
            "repeat_order_id": new_order.id,
            "reference_order_id": original_order.id,
            "course_order_count": next_course_order_count,
            "course_order_done": original_order.course_order,
        }, status=status.HTTP_201_CREATED)


class RecurringOrdersAPIView(generics.ListAPIView):
    serializer_class = OrderTableSerializer
    pagination_class = OrderPagination
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        today = date.today()
        branch = self.request.user.profile.branch
        company = self.request.user.profile.company

        # ✅ Only delivered orders are candidates for recurring
        orders = Order_Table.objects.filter(
            is_closed=False,
            is_deleted=False,
            order_status__name__iexact="DELIVERED",
            branch=branch,
            company=company
        )

        results = []

        # ✅ Current month start & end
        first_day = today.replace(day=1)
        last_day = today.replace(day=monthrange(today.year, today.month)[1])

        for order in orders:
            start_date = order.created_at.date()
            repeated = order.course_order or 0             # actual repeats done
            count = order.course_order_count or 1          # planned repeats

            # ✅ Skip if repeat already exists this month
            repeat_exists = Order_Table.objects.filter(
                reference_order=order,
                created_at__date__gte=first_day,
                created_at__date__lte=last_day,
                is_deleted=False
            ).exists()

            if repeat_exists:
                continue  

            # ✅ Loop through all remaining repeats
            for i in range(repeated + 1, count + 1):
                next_occurrence = start_date + timedelta(days=i * 30)
                window_start = next_occurrence - timedelta(days=5)
                window_end = next_occurrence

                # ✅ If today is inside any valid repeat window
                if window_start <= today <= window_end and (today - start_date).days <= 180:
                    results.append(order.id)
                    break  # no need to check further repeats for this order

        return Order_Table.objects.filter(id__in=results)

class AcceptedOrdersReportAPIView(APIView):
    permission_classes = [IsAuthenticated]

    """
    API to fetch accepted orders and summary by payment type
    with optional date filtering
    """
    def get(self, request):
        order_status = "Accepted"
        branch = request.user.profile.branch
        company = request.user.profile.company

        # Get date filters from query params
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")

        # Base queryset
        accepted_orders = Order_Table.objects.filter(
            order_status__name__iexact=order_status,
            branch=branch,
            company=company
        )

        # Apply date filter if provided
        if start_date and end_date:
            try:
                start_dt = datetime.strptime(start_date, "%Y-%m-%d")
                end_dt = datetime.strptime(end_date, "%Y-%m-%d")
                end_dt = timezone.make_aware(datetime.combine(end_dt, time.max))
                accepted_orders = accepted_orders.filter(
                    Q(created_at__range=(start_dt, end_dt)) |
                    Q(updated_at__range=(start_dt, end_dt))
                )
            except ValueError:
                return Response({"error": "Invalid date format. Use YYYY-MM-DD."}, status=400)

        # Group by payment_type
        summary = accepted_orders.values(
            'payment_type',           # ID
            'payment_type__name'      # Name
        ).annotate(
            total_orders=Count('id'),
            total_amount=Sum('total_amount')
        )

        serializer = OrderSummarySerializer(summary, many=True)
        return Response(serializer.data)
    

def get_main_order_status_for_vendor_status(shipment_vendor, vendor_status_name):
    try:
        allow_status = AllowStatus.objects.get(
            name__iexact=vendor_status_name,   # ✅ exact match, case-insensitive
            shipment_vendor=shipment_vendor    # ✅ restrict to vendor
        )
        workflow = OrderStatusWorkflow.objects.filter(
            shipment_vendor=shipment_vendor,
            allow_status=allow_status
        ).select_related('order_status').first()

        return workflow.order_status if workflow else None
    except AllowStatus.DoesNotExist:
        return None



class MainOrderStatusAPIView(APIView):
    def get(self, request, *args, **kwargs):
        vendor_id = request.query_params.get('vendor_id')
        vendor_status_name = request.query_params.get('vendor_status_name')

        if not vendor_id or not vendor_status_name:
            return Response(
                {"error": "vendor_id and vendor_status_name are required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            shipment_vendor = ShipmentVendor.objects.get(id=vendor_id)
        except ShipmentVendor.DoesNotExist:
            return Response({"error": "ShipmentVendor not found."}, status=status.HTTP_404_NOT_FOUND)

        order_status = get_main_order_status_for_vendor_status(shipment_vendor, vendor_status_name)

        if order_status:
            serializer = OrderStatusSerializer(order_status)
            return Response(serializer.data, status=status.HTTP_200_OK)

        return Response({"message": "No matching order status found."}, status=status.HTTP_404_NOT_FOUND)


STATE_CODE_MAP = {
    'ANDAMAN AND NICOBAR ISLANDS': 'AN', 'ANDHRA PRADESH': 'AP', 'ARUNACHAL PRADESH': 'AR', 'ASSAM': 'AS',
    'BIHAR': 'BR', 'CHANDIGARH': 'CH', 'CHHATTISGARH': 'CG', 'DADRA AND NAGAR HAVELI AND DAMAN AND DIU': 'DH',
    'DELHI': 'DL', 'GOA': 'GA', 'GUJARAT': 'GJ', 'HARYANA': 'HR', 'HIMACHAL PRADESH': 'HP',
    'JAMMU AND KASHMIR': 'JK', 'JHARKHAND': 'JH', 'KARNATAKA': 'KA', 'KERALA': 'KL', 'LADAKH': 'LA',
    'LAKSHADWEEP': 'LD', 'MADHYA PRADESH': 'MP', 'MAHARASHTRA': 'MH', 'MANIPUR': 'MN', 'MEGHALAYA': 'ML',
    'MIZORAM': 'MZ', 'NAGALAND': 'NL', 'ODISHA': 'OR', 'PUDUCHERRY': 'PY', 'PUNJAB': 'PB', 'RAJASTHAN': 'RJ',
    'SIKKIM': 'SK', 'TAMIL NADU': 'TN', 'TELANGANA': 'TG', 'TRIPURA': 'TR', 'UTTAR PRADESH': 'UP',
    'UTTARAKHAND': 'UK', 'WEST BENGAL': 'WB',
}


class OrderLocationReportView(APIView):
    permission_classes = [IsAuthenticated]

    def success(self, message, data=None, status_code=status.HTTP_200_OK):
        return Response({"success": True, "message": message, "data": data}, status=status_code)

    def error(self, message, errors=None, status_code=status.HTTP_400_BAD_REQUEST):
        return Response({"success": False, "message": message, "errors": errors}, status=status_code)

    def get(self, request):
        try:
            user = request.user
            company = getattr(user.profile, 'company', None)
            branch = getattr(user.profile,'branch',None)
            # user.profile.branch.id
            if not company:
                return self.error("User is not associated with a company.")

            company_id = company.id
            branch_id = branch.id
            # ============================
            # Filters
            # ============================

            date_from_str = request.query_params.get('date_from')
            date_to_str = request.query_params.get('date_to')
            state_param = request.query_params.get('state')
            city_param = request.query_params.get('district')

            if city_param and not state_param:
                return self.error("City cannot be passed without a state. Please provide a state.")

            # ============================
            # Base Query + Only Accepted Orders
            # ============================
            seller_orders_query = Order_Table.objects.filter(
                company_id=company_id,
                branch_id = branch_id,
                is_deleted=False,
                order_status__name__iexact="ACCEPTED"   # <- ONLY ACCEPTED ORDERS
            )

            # ============================
            # Date Filters
            # ============================

            if date_from_str:
                parsed_date = parse_date(date_from_str)
                if not parsed_date:
                    return self.error("Invalid date_from format. Use YYYY-MM-DD")
                seller_orders_query = seller_orders_query.filter(
                    created_at__gte=datetime.combine(parsed_date, datetime.min.time())
                )

            if date_to_str:
                parsed_date = parse_date(date_to_str)
                if not parsed_date:
                    return self.error("Invalid date_to format. Use YYYY-MM-DD")
                seller_orders_query = seller_orders_query.filter(
                    created_at__lte=datetime.combine(parsed_date, datetime.max.time())
                )

            # ============================
            # Location Filters
            # ============================

            if state_param:
                seller_orders_query = seller_orders_query.filter(
                    customer_state__name__iexact=state_param
                )
            if city_param:
                seller_orders_query = seller_orders_query.filter(
                    customer_city__iexact=city_param
                )

            # ============================
            # Fetch Only Required Fields
            # ============================
            seller_orders = list(
                seller_orders_query.annotate(
                    pincode=F("customer_postal"),
                    state_name=F("customer_state__name"),
                    city_name=F("customer_city")
                ).values("id", "pincode", "state_name", "city_name")
            )

            if not seller_orders:
                return self.success("No orders found.", {"total_orders_mapped": 0, "location_groups": []})

            # ============================
            # Group by State → City → Pincode
            # ============================

            grouped_data = {}
            total_orders_mapped = 0

            for order in seller_orders:
                state = (order['state_name'] or 'Unknown').upper()
                city = order['city_name'] or 'Unknown'
                pincode = order['pincode'] or 'Unknown'
                state_code = STATE_CODE_MAP.get(state, 'N/A')

                key = (state, state_code, city)
                grouped_data.setdefault(key, {}).setdefault(pincode, []).append(order['id'])
                total_orders_mapped += 1

            # ============================
            # Build Final Output Format
            # ============================

            location_groups = []
            for (state, state_code, city), pincode_groups in grouped_data.items():
                city_order_count = sum(len(v) for v in pincode_groups.values())
                pincode_details = [
                    {
                        "pincode": pin,
                        "order_count": len(order_ids),
                        "order_ids": sorted(order_ids)
                    }
                    for pin, order_ids in sorted(pincode_groups.items())
                ]
                location_groups.append({
                    "state": state,
                    "state_code": state_code,
                    "city": city,
                    "order_count": city_order_count,
                    "pincode_details": pincode_details,
                })

            # Sort alphabetically
            location_groups = sorted(location_groups, key=lambda x: x["state"])

            return self.success(
                "Order location report generated successfully.",
                {
                    "total_orders_mapped": total_orders_mapped,
                    "location_groups": location_groups
                }
            )

        except Exception as e:
            return self.error("An unexpected error occurred.", str(e), status.HTTP_500_INTERNAL_SERVER_ERROR)



class PaymentMethodViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Payment_Status
    """
    queryset = Payment_method.objects.all()
    serializer_class = PaymentMethodSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Optionally filter payment statuses by branch or company via query parameters.
        """
        queryset = super().get_queryset()
        user = self.request.user
        company = user.profile.company 
        branch_id = self.request.query_params.get('branch', None)
        company_id =company.id

        if branch_id:
            queryset = queryset.filter(branch_id=branch_id)
        if company_id:
            queryset = queryset.filter(company_id=company_id)

        return queryset
    
    def perform_create(self, serializer):
        """
        Automatically set `company` and `branch` fields for the created Payment_Status instance.
        """ 
        user = self.request.user
        company = user.profile.company  # Adjust if your company relation is different

        serializer.save(company=company)

class OrderAggregationByPerformance(APIView):

    def get(self, request, *args, **kwargs):
        month = request.query_params.get("month")
        tl_id = request.query_params.get('tl_id', None)
        manager_id = request.query_params.get('manager_id', None)
        agent_id = request.query_params.get('agent_id', None)

        company_id = self.request.user.profile.company
        branch_id = self.request.user.profile.branch

        q_user_filters = Q()

        # ------------------------
        # MONTH RANGE HANDLING
        # ------------------------
        if month:
            try:
                monthyear = month
                year, month_num = map(int, month.split("-"))
                start_date = date(year, month_num, 1)
            except:
                return Response({"error": "Invalid month format. Use YYYY-MM."}, status=400)
        else:
            today = timezone.now().date()
            monthyear = f"{today.year}-{today.month:02d}"
            start_date = date(today.year, today.month, 1)

        last_day = calendar.monthrange(start_date.year, start_date.month)[1]
        end_date = date(start_date.year, start_date.month, last_day)

        start_datetime = datetime.combine(start_date, time.min)
        end_datetime = datetime.combine(end_date, time.max)

        # Helper
        def apply_date_filter(query, start_datetime, end_datetime, count=True):
            if count:
                return query.filter(
                    Q(created_at__range=(start_datetime, end_datetime)),
                    is_deleted=False,
                ).count()
            else:
                return query.filter(
                    Q(created_at__range=(start_datetime, end_datetime)),
                    is_deleted=False,
                )

        # ------------------------
        # FILTER EMPLOYEES BY MANAGER / TL / AGENT
        # ------------------------
        if manager_id:
            employees_under_manager = Employees.objects.filter(manager_id=manager_id, status=1)
            manager_user_ids = list(employees_under_manager.values_list("user_id", flat=True))
            q_user_filters &= Q(user_id__in=manager_user_ids)

        elif tl_id:
            employees_under_tl = Employees.objects.filter(teamlead_id=tl_id, status=1)
            tl_user_ids = list(employees_under_tl.values_list("user_id", flat=True))
            q_user_filters &= Q(user_id__in=tl_user_ids + [int(tl_id)])

        elif agent_id:
            q_user_filters &= Q(user_id=agent_id)

        else:
            return Response(
                {"Success": False, "message": "Manager or Team Lead or Agent not found.", "agent_list": []},
                status=status.HTTP_200_OK
            )
        # ------------------------
        # EXTRA USERS (MANAGER + TL)
        # ------------------------
        extra_users = Employees.objects.filter(
            Q(user__id=manager_id) | Q(user__id=tl_id),
            status=1
        )

        # ------------------------
        # MAIN AGENT QUERY
        # ------------------------
        agents_filtered = Employees.objects.filter(
            company_id=company_id,
            branch_id=branch_id,
            status=1
        ).filter(q_user_filters)
        print(agents_filtered,"-----------------------4162")
        # Combine employees under criteria + TL/Manager
        agents = agents_filtered.union(extra_users)
        print(agents)
        if not agents:
            return Response({"Success": False,"message":"Agent found.","agent_list": []}, status=status.HTTP_200_OK)
        # ------------------------
        # BUILD RESPONSE
        # ------------------------
        agent_list = []
        team_total_order_target = 0
        team_total_amount_target = 0
        team_total_delivered_orders = 0
        team_total_delivered_amount = 0
        total_orders = 0
        total_orders_amount = 0
        total_rto_orders = 0
        total_rto_amount = 0
        rto_orders_percentage = 0
        rto_amount_percentage = 0
        for agent in agents:
            user = agent.user

            # Orders created or updated this month
            today_orders = Order_Table.objects.filter(
                Q(order_created_by=user) | Q(updated_by=user),
                is_deleted=False,
            ).filter(
                Q(created_at__range=(start_datetime, end_datetime)) |
                Q(updated_at__range=(start_datetime, end_datetime))
            )

            # delivered_order = apply_date_filter(
            #     today_orders.filter(order_status__name='Delivered'),
            #     start_datetime, end_datetime
            # )

            # Fetch target
            # target = UserTargetsDelails.objects.filter(user=user).first()
            target = UserTargetsDelails.objects.filter(
                user=user,
                monthyear=monthyear,
                in_use=True
            ).first()

            if not target:
                response_data = {
                    "user_id": user.id,
                    "username": user.username,
                    "agent_name": user.get_full_name(),
                    "month": start_date.strftime("%Y-%m"),
                    "rto":{
                            "total_order":0,
                            "total_order_amount":0,
                            "total_rto_order":0,
                            "total_rto_count":0,
                            "rto_order_percentage":0,
                            "rto_amount_percentage":0
                        },
                    "target": {
                        "order_target": 0,
                        "amount_target": 0,
                    },

                    "achieved": {
                        "delivered_orders": 0,
                        "delivered_amount": 0,
                    },

                    "percentage": {
                        "order_percentage": 0,
                        "amount_percentage": 0,
                    },

                    "target_achieved": False,
                }
                agent_list.append(response_data)
                continue

            # If target exists
            order_target = target.monthly_orders_target
            amount_target = target.monthly_amount_target
            total_order = Order_Table.objects.filter(
                order_created_by=user,
                created_at__range=(start_datetime, end_datetime),
                is_deleted=False
            )

            delivered_orders = total_order.filter(
                order_status__name="Delivered"
            )

            rto_orders = total_order.filter(
                order_status__name__in=["RTO INITIATED", "RTO DELIVERED"]
            )
            rto_order_count = rto_orders.count()
            rto_count_amount = rto_orders.aggregate(
                total=Sum("total_amount")
            )["total"] or 0
            total_order_count = total_order.count()
            total_count_amount = total_order.aggregate(
                total=Sum("total_amount")
            )["total"] or 0
            achieved_orders = delivered_orders.count()
            achieved_amount = delivered_orders.aggregate(
                total=Sum("total_amount")
            )["total"] or 0
            
            order_percentage = (
                (float(achieved_orders) / float(order_target)) * 100
                if order_target else 0
            )

            amount_percentage = (
                (float(achieved_amount) / float(amount_target)) * 100
                if amount_target else 0
            )

            rto_order_percentage = ((float(rto_count_amount) / float(total_order_count)) * 100
                if total_order_count else 0
            )
            rto_amount_percentage = (
                (float(achieved_amount) / float(total_count_amount)) * 100
                if total_count_amount else 0
            )
            target_achieved = order_percentage >= 100 or amount_percentage >= 100

            target.achieve_target = target_achieved
            target.save()
            total_orders = total_order_count + total_orders
            total_orders_amount = total_orders_amount + total_count_amount
            total_rto_orders = total_rto_orders + rto_order_count
            total_rto_amount = total_rto_amount + rto_count_amount

            response_data = {
                "user_id": user.id,
                "username": user.username,
                "agent_name": user.get_full_name(),
                "month": start_date.strftime("%Y-%m"),
                "rto":{
                    "total_order":total_order_count,
                    "total_order_amount":total_count_amount,
                    "total_rto_order":rto_order_count,
                    "total_rto_count":rto_count_amount,
                    "rto_order_percentage":rto_order_percentage,
                    "rto_amount_percentage":rto_amount_percentage
                },
                "target": {
                    "order_target": order_target,
                    "amount_target": float(amount_target),
                },

                "achieved": {
                    "delivered_orders": achieved_orders,
                    "delivered_amount": float(achieved_amount),
                },

                "percentage": {
                    "order_percentage": round(order_percentage, 2),
                    "amount_percentage": round(amount_percentage, 2),
                },

                "target_achieved": target_achieved,
            }
            team_total_order_target = team_total_order_target +order_target
            team_total_amount_target = team_total_amount_target + amount_target
            team_total_delivered_orders = team_total_delivered_orders + achieved_orders
            team_total_delivered_amount = team_total_delivered_amount + achieved_amount

            agent_list.append(response_data)
        order_percentage = (
            (team_total_delivered_orders / team_total_order_target) * 100
            if team_total_order_target else 0
        )

        amount_percentage = (
            (float(team_total_delivered_amount) / float(team_total_amount_target)) * 100
            if team_total_amount_target else 0
        )
        rto_orders_percentage = (
            (total_rto_orders / total_orders) * 100
            if total_orders else 0
        )

        rto_amount_percentage = (
            (float(total_rto_amount) / float(total_orders_amount)) * 100
            if total_orders_amount else 0
        )
        team_target_summary = {
            "total_order_target": team_total_order_target,
            "total_amount_target": team_total_amount_target,
            "total_delivered_orders": team_total_delivered_orders,
            "total_delivered_amount": team_total_delivered_amount,
            "order_percentage": round(order_percentage, 2),
            "amount_percentage": round(amount_percentage, 2),
            "total_orders":total_orders,
            "total_orders_amount":total_orders_amount,
            "total_rto_orders":total_rto_orders,
            "total_rto_amount":total_rto_amount,
            "rto_orders_percentage":rto_orders_percentage,
            "rto_amount_percentage":rto_amount_percentage

        }
        data = {
            "agent_list":agent_list,
            'team_target_summary': team_target_summary,
        }
        return Response({"Success": True,"message":"Data Fetch successfully","agent_list": data}, status=status.HTTP_200_OK)


from rest_framework.generics import GenericAPIView

class OFDListView(GenericAPIView):
    permission_classes = [IsAuthenticated]
    pagination_class = FilterOrdersPagination

    # ------------------ DATE RANGE ------------------
    def get_date_range(self, request):
        date_range = request.query_params.get('date_range')
        try:
            if date_range:
                if isinstance(date_range, str):
                    date_range = date_range.split(' ')
                    if len(date_range) != 2:
                        raise ValueError("Date range invalid")
                    start_date = datetime.fromisoformat(date_range[0]).date()
                    end_date = datetime.fromisoformat(date_range[1]).date()

                elif isinstance(date_range, dict):
                    start_date = date_range.get("start_date")
                    end_date = date_range.get("end_date", datetime.now().strftime('%Y-%m-%d'))
                    start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
                    end_date = datetime.strptime(end_date, '%Y-%m-%d').date()

            else:
                today = datetime.now().date()
                start_date = end_date = today

            start_datetime = timezone.make_aware(datetime.combine(start_date, time.min))
            end_datetime = timezone.make_aware(datetime.combine(end_date, time.max))
            return start_datetime, end_datetime

        except:
            return None, None

    # ------------------ USER SCOPE ------------------
    def _scope_queryset(self, qs, user):
        agent_ids = Employees.objects.filter(manager=user.id).values_list('user', flat=True)
        mgr_ids = Employees.objects.filter(
            Q(teamlead__in=agent_ids) | Q(user=user.id)
        ).values_list('user', flat=True)

        mgr = set(mgr_ids) | set(agent_ids)

        tl_ids = list(Employees.objects.filter(teamlead=user.id).values_list('user', flat=True))
        tl_ids.append(user.id)

        if user.profile.user_type in ["admin", "superadmin"]:
            return qs

        elif user.has_perm("accounts.view_all_order_others"):
            return qs

        elif user.has_perm("accounts.view_manager_order_others"):
            return qs.filter(Q(order_created_by__in=mgr) | Q(updated_by__in=mgr))

        elif user.has_perm("accounts.view_teamlead_order_others"):
            return qs.filter(Q(order_created_by__in=tl_ids) | Q(updated_by__in=tl_ids))

        elif user.has_perm("accounts.view_own_order_others"):
            return qs.filter(Q(order_created_by=user.id) | Q(updated_by=user.id))

        return qs.none()

    # ------------------ MAIN GET API ------------------
    def get(self, request):
        user = request.user
        params = request.query_params
        branch = request.user.profile.branch
        company = request.user.profile.company
        # OUT FOR DELIVERY Shipped status
        ofd_status = OrderStatus.objects.get(name="OUT FOR DELIVERY")

        # Subquery: latest OFD log
        latest_ofd_log = OrderLogModel.objects.filter(
            order=OuterRef('pk'),
            order_status=ofd_status
        ).order_by('-created_at').values('created_at')[:1]

        # Base queryset
        # qs = Order_Table.objects.all()
        qs = Order_Table.objects.filter(
        branch=branch,
        company=company,
        is_deleted=False
    ).order_by("-created_at")
        # Apply user scope
        qs = self._scope_queryset(qs, user)

        # DATE FILTER
        start_datetime, end_datetime = self.get_date_range(request)
        if start_datetime and end_datetime:
            qs = qs.filter(created_at__range=(start_datetime, end_datetime))

        # ORDER STATUS
        if params.get("order_status"):
            qs = qs.filter(order_status__name__icontains=params["order_status"])

        

        

        # ADD OFD DATE
        qs = qs.annotate(ofd_date=Subquery(latest_ofd_log)).order_by("-created_at")

        # ----------------- IMPORTANT FIX -----------------
        # Convert queryset to list BEFORE pagination
        list_qs = list(qs.values(
            "id",
            "order_id",
            "customer_name",
            "order_status__name",
            "estimated_delivery_date",
            "ofd_date",
            "created_at",
            "order_wayBill"
        ))

        # PAGINATE LIST
        page = self.paginate_queryset(list_qs)
        if page is not None:
            return self.get_paginated_response(page)

        return Response({"status": True, "data": list_qs})