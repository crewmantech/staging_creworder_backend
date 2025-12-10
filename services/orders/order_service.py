import os
import pycountry
import requests,json
import random,string
from rest_framework import status
from django.db.models import Q

from kyc.views import send_otp_to_number
from orders.models import Order_Table, OrderDetail,Products,OrderLogModel, SmsConfig
from rest_framework.response import Response
from orders.serializers import (
    OrderDetailSerializer,
    OrderTableSerializer,
    OrderLogSerializer,
    OrderTableSerializer1,
    ProductSerializer,
    InvoiceSerializer
)
from django.template.loader import render_to_string
from django.core.exceptions import ObjectDoesNotExist
from accounts.models import Company, Employees
from accounts.serializers import UserProfileSerializer,PickUpPointSerializer
from rest_framework.pagination import PageNumberPagination
from rest_framework.exceptions import NotFound
from phonenumbers.phonenumberutil import country_code_for_region,region_code_for_number,parse
from phonenumbers import NumberParseException
from django.db.models import Q
from datetime import datetime,time
from services.email.email_service import send_email
from shipment.models import ShipmentModel
from shipment.serializers import ShipmentSerializer
from accounts.models import PickUpPoint,User

def getShipRocketToken(email,password):
    data=None
    url = "https://apiv2.shiprocket.in/v1/external/auth/login"
    payload = json.dumps({
    "email": f"{email}",
    "password": f"{password}"
    })
    headers = {
    'Content-Type': 'application/json'
    }
    response = requests.request("POST", url, headers=headers, data=payload)
    if response.status_code==200:
        data=response.json()['token']
    return data

def check_country_code_exists(number):
    try:
        parsed_number = parse(number, None)
        country_code = parsed_number.country_code
        region_code = region_code_for_number(parsed_number)
        if region_code:
            country = pycountry.countries.get(alpha_2=region_code)
            if country:
                country_name = country.name
                return True, country_code, region_code, country_name
            else:
                return False, None, None, None
        else:
            return False, None, None, None
    except NumberParseException:
        return False, None, None, None


def orderLogInsert(data):
        logData = OrderLogModel.objects.filter(order=data['order'],order_status=data['order_status']).first()
        if logData is None:
            orderLogSerializer = OrderLogSerializer(data=data)
            if orderLogSerializer.is_valid():
                orderInsert = orderLogSerializer.save()
            else:
                raise ValueError(orderLogSerializer.errors)
        
def createOrderDetailsJson(data):
    grossTotalAmount=0
    product_qty=0
    for product in data["product_details"]:
        try:
            products = Products.objects.filter(id=product['product']).first()
            productSerializerData = ProductSerializer(products)
            productData = productSerializerData.data
            total_product_amount=int(productData['product_price']) * int(product['product_qty'])
            product_price = int(productData['product_price'])
            product_actual_price=int(total_product_amount) / (1 + (int(productData['product_gst_percent']) / 100))
            product['product_name']=productData['product_name']
            product['product_price']=int(product_price)
            product['product_total_price']=int(int(total_product_amount) / (1 + (int(productData['product_gst_percent']) / 100)))
            product['product_mrp']=int(product_price)
            product['gst_amount']=int(total_product_amount)-int(product_actual_price)
            product['taxeble_amount']=int(total_product_amount)-int(product_actual_price)
            grossTotalAmount+=float(productData['product_price']) * int(product['product_qty'])
            product['product_total']=float(productData['product_price']) * int(product['product_qty'])
            
            product_qty+=int(product['product_qty'])
        except Exception as e:
            print("error",str(e))
    data['gross_amount']=grossTotalAmount
    data['product_qty']=product_qty
    data['total_amount']=float(grossTotalAmount)-float(data['discount'])
    data['cod_amount'] = float(grossTotalAmount)-float(data['discount'])-float(data['prepaid_amount'])
    return data

def updateOrderDetailsJson(data, id):
    try:
        # Get existing order data
        orderData = Order_Table.objects.filter(id=id).first()
        if not orderData:
            raise ValueError("Order not found")
            
        orderSerializerData = OrderTableSerializer(orderData)
        existing_data = orderSerializerData.data
        
        # Initialize variables with existing values
        grossTotalAmount = 0
        product_qty = 0
        discount = data.get('discount', existing_data['discount'])
        prepaid_amount = data.get('prepaid_amount', existing_data['prepaid_amount'])
        
        # Only process product details if they are provided
        if 'product_details' in data and data['product_details']:
            # Delete existing order details
            OrderDetail.objects.filter(order=id).delete()
            
            # Process new product details
            for product in data["product_details"]:
                try:
                    products = Products.objects.filter(id=product['product']).first()
                    if not products:
                        raise ValueError(f"Product with id {product['product']} not found")
                        
                    productSerializerData = ProductSerializer(products)
                    productData = productSerializerData.data
                    
                    # Calculate product amounts
                    total_product_amount = int(productData['product_price']) * int(product['product_qty'])
                    product_actual_price = int(total_product_amount) / (1 + (int(productData['product_gst_percent']) / 100))
                    product_price = int(productData['product_price'])
                    # Update product details
                    product['order'] = id
                    product['product_name'] = productData['product_name']
                    product['product_price'] = int(product_price)
                    product['product_total_price'] = int(int(total_product_amount) / (1 + (int(productData['product_gst_percent']) / 100)))
                    product['product_mrp'] = int(product_price)
                    product['gst_amount'] = int(total_product_amount) - int(product_actual_price)
                    product['taxeble_amount'] = int(total_product_amount) - int(product_actual_price)
                    
                    # Update totals
                    grossTotalAmount += float(productData['product_price']) * int(product['product_qty'])
                    product_qty += int(product['product_qty'])
                    
                except Exception as e:
                    raise ValueError(f"Error processing product: {str(e)}")
        else:
            # If no new product details, use existing totals
            grossTotalAmount = existing_data['gross_amount']
            product_qty = existing_data['product_qty']
        
        # Update data with calculated values
        data['gross_amount'] = grossTotalAmount
        data['product_qty'] = product_qty
        data['total_amount'] = float(grossTotalAmount) - float(discount) 
        data['cod_amount'] = float(grossTotalAmount) - float(discount) - float(prepaid_amount)
        return data
        
    except Exception as e:
        raise ValueError(f"Error in updateOrderDetailsJson: {str(e)}")

def createOrders(data,user_id):
    has_country_code, country_code, region_code, country_name = check_country_code_exists(data['customer_phone'])
    if has_country_code:
        if data['customer_country'].lower()!=country_name.lower():
            raise ValueError("country code or country name not match.")
    else:
        raise ValueError("Phone number does not contain a valid country code.")
    userData = Employees.objects.filter(user_id=user_id).first()
    serializer = UserProfileSerializer(userData)
    serialized_data = serializer.data
    if int(data['repeat_order'])!=1:
        repeatMobileNumber = Order_Table.objects.filter(customer_phone=data['customer_phone'],customer_alter_phone=data['customer_phone']).first()
        if repeatMobileNumber:
            raise ValueError("Phone number exists")
        
    data=createOrderDetailsJson(data)
    print(data,"------------------186")
    orderId = "".join(random.choices(string.ascii_uppercase + string.digits, k=7))
    
    
    data["branch"] = serialized_data["branch"]
    data["company"] = serialized_data["company"]
    data["order_id"] = "ODR" + str(orderId)
    # data["order_created_by"] = user_id
    orderSerializer = OrderTableSerializer(data=data)
    if orderSerializer.is_valid():
        orderSaveResponce = orderSerializer.save()
        for product in data["product_details"]:
            products = Products.objects.filter(id=product['product']).first()
            productSerializerData = ProductSerializer(products)
            productData = productSerializerData.data
            product['order']=orderSaveResponce.id
        orderDetailsSerializer = OrderDetailSerializer(data=data["product_details"],many=True)
        if orderDetailsSerializer.is_valid():
            orderDetailsSaveResponce = orderDetailsSerializer.save()
            orderLogInsert({"order":orderSaveResponce.id,"order_status":data["order_status"],"action_by":user_id,"remark":"Order Created"})
        else:
            order_instance = Order_Table.objects.get(pk=orderSaveResponce.id)
            order_instance.delete()
            raise ValueError(orderDetailsSerializer.errors)
        return orderSaveResponce
    else:
        raise ValueError(orderSerializer.errors)
    

def updateOrders(id, data, user_id):
    try:
        # Get existing order
        order = Order_Table.objects.get(id=id)
        user = User.objects.get(id=user_id)
        if user.has_perm('accounts.view_number_masking_others') and user.profile.user_type != 'admin':
            if 'customer_phone' in data:
                data['customer_phone'] = order['customer_phone']
        
        # Process product details if provided
        if 'product_details' in data:
            data = updateOrderDetailsJson(data, id)
        
        # Update order data
        serializer = OrderTableSerializer(order, data=data, partial=True)
        if serializer.is_valid():
            # Save order changes
            updated_order = serializer.save()
            
            # Save product details if provided
            if 'product_details' in data:
                order_details_serializer = OrderDetailSerializer(data=data["product_details"], many=True)
                if order_details_serializer.is_valid():
                    order_details_serializer.save()
                else:
                    raise ValueError(f"Invalid product details: {order_details_serializer.errors}")
            
            # Log order status change if provided
            if 'order_status' in data:
                
                userData = Employees.objects.filter(user_id=user_id).values("branch", "company").first()
                if not userData:
                    return Response({"error": "User data not found"}, status=400)

                company_id = userData.get('company')
                orderLogInsert({
                    "order": id,
                    "order_status": data["order_status"],
                    "action_by": user_id,
                    "remark": "order updated"
                })
                try:
                    trigger_order_status_notifications(company_id, data["order_status"], id)
                except Exception as e:
                    pass  # continue execution silently if needed

            return updated_order
        else:
            raise ValueError(f"Invalid order data: {serializer.errors}")
            
    except Order_Table.DoesNotExist:
        return None
    except Exception as e:
        raise ValueError(f"Error updating order: {str(e)}")

def deleteOrder(id):
    try:
        data = Order_Table.objects.get(id=id)
        data.delete()
        return True
    except ObjectDoesNotExist:
        return False

def soft_delete_order(order_id):
    try:
        order = Order_Table.objects.get(id=order_id)
        order.is_deleted = True
        order.save()
        return True
    except ObjectDoesNotExist:
        return False
# def getOrderDetails(usrid,id=None):
#     try:
#         userData = Employees.objects.filter(user_id=usrid).first()
#         serializer = UserProfileSerializer(userData)
#         serialized_data = serializer.data
#         tableData = ""
#         if id is not None:
#             tableData = Order_Table.objects.filter(
#                 branch=serialized_data["branch"], company=serialized_data["company"],id=id
#             )
#             orderDetailsData = OrderDetail.objects.filter(
#                 order=id
#             )
#             orderDetailsTableData = OrderDetailSerializer(orderDetailsData, many=True)
#             orderTableData = OrderTableSerializer(tableData, many=True)
#             orderTableData.data[0]['product_details']=orderDetailsTableData.data
#         else:
#             tableData = Order_Table.objects.filter(
#                 branch=serialized_data["branch"], company=serialized_data["company"]
#             )
#             orderTableData = OrderTableSerializer(tableData, many=True)
#             for row in orderTableData.data:
#                 orderDetailsData = OrderDetail.objects.filter(order=row['id'])
#                 orderDetailsTableData = OrderDetailSerializer(orderDetailsData, many=True)
#                 row['product_details']=orderDetailsTableData.data
#         return orderTableData.data
#     except ObjectDoesNotExist:
#         return False
# def getOrderDetails(usrid, id=None):
#     try:
#         # Get employee profile
#         employee = Employees.objects.filter(user_id=usrid).first()
#         if not employee:
#             return []

#         # Get branch and company from the employee's profile
#         serializer = UserProfileSerializer(employee)
#         branch = serializer.data["branch"]
#         company = serializer.data["company"]

#         # Prepare groupings for permission logic
#         agent_ids = Employees.objects.filter(manager=usrid).values_list('user', flat=True)
#         user_ids_for_manager = set(
#             Employees.objects.filter(Q(teamlead__in=agent_ids) | Q(user=usrid)).values_list('user', flat=True)
#         ) | set(agent_ids)

#         user_ids_for_teamlead = list(Employees.objects.filter(teamlead=usrid).values_list('user', flat=True))
#         user_ids_for_teamlead.append(usrid)

#         # Permission-based filtering logic
#         user = User.objects.get(id=usrid)
#         if user.has_perm("accounts.view_own_order_others"):
#             base_query = Order_Table.objects.filter(
#                 order_created_by=usrid,
#                 branch=branch,
#                 company=company
#             )
#         elif user.has_perm("accounts.view_all_order_others") or user.profile.user_type == "admin":
#             base_query = Order_Table.objects.filter(
#                 branch=branch,
#                 company=company
#             )
#         elif user.has_perm("accounts.view_manager_order_others"):
#             base_query = Order_Table.objects.filter(
#                 order_created_by__in=user_ids_for_manager,
#                 branch=branch,
#                 company=company
#             )
#         elif user.has_perm("accounts.view_teamlead_order_others"):
#             base_query = Order_Table.objects.filter(
#                 order_created_by__in=user_ids_for_teamlead,
#                 branch=branch,
#                 company=company
#             )
#         else:
#             return []  # User has no permission

#         # Apply specific ID filter if provided
#         if id is not None:
#             base_query = base_query.filter(id=id)

#         # Serialize and attach order details
#         order_table_data = OrderTableSerializer(base_query, many=True)
#         for row in order_table_data.data:
#             order_details = OrderDetail.objects.filter(order=row['id'])
#             row['product_details'] = OrderDetailSerializer(order_details, many=True).data

#         return order_table_data.data

#     except ObjectDoesNotExist:
#         return []
def get_single_order(usrid,id=None):
        
        base_query = Order_Table.objects.filter(id=id)
        order_table_data = OrderTableSerializer(base_query, many=True)

        # Add product details
        for row in order_table_data.data:
            order_details = OrderDetail.objects.filter(order=row['id'])
            row['product_details'] = OrderDetailSerializer(order_details, many=True).data

        return order_table_data.data
def getOrderDetails(usrid, id=None,company_id=None,branch_id=None):
    try:
        employee = Employees.objects.filter(user_id=usrid).first()
        if not employee:
            return []

        serializer = UserProfileSerializer(employee)
        branch = serializer.data["branch"]
        company = serializer.data["company"]

        

        user = User.objects.get(id=usrid)

        # Initialize base_query
        base_query = None

        # Determine base query based on user permission
        if id is not None:
            base_query = Order_Table.objects.filter(id=id)
            order_table_data = OrderTableSerializer(base_query, many=True)

            # Add product details
            for row in order_table_data.data:
                order_details = OrderDetail.objects.filter(order=row['id'])
                row['product_details'] = OrderDetailSerializer(order_details, many=True).data

            return order_table_data.data
        if user.profile.user_type == "admin" or user.has_perm("accounts.view_all_order_others"):
            base_query = Order_Table.objects.filter(branch=branch, is_deleted=False, company=company)
            order_table_data = OrderTableSerializer(base_query, many=True)

            # Add product details
            # for row in order_table_data.data:
            #     order_details = OrderDetail.objects.filter(order=row['id'])
            #     row['product_details'] = OrderDetailSerializer(order_details, many=True).data

            return order_table_data.data
    
        # if user.has_perm('accounts.view_search_bar_others'):
        #     base_query = Order_Table.objects.filter(branch=branch, is_deleted=False, company=company)
        if user.has_perm("accounts.view_search_bar_others"):
            base_query = Order_Table.objects.filter(branch=branch, is_deleted=False, company=company)
        elif user.has_perm("accounts.view_manager_order_others"):
            agent_ids = Employees.objects.filter(manager=usrid).values_list('user', flat=True)
            user_ids_for_manager = set(
                Employees.objects.filter(Q(teamlead__in=agent_ids) | Q(user=usrid)).values_list('user', flat=True)
            ) | set(agent_ids)
            user_ids_for_manager.add(usrid)
            base_query = Order_Table.objects.filter(
                Q(order_created_by__in=user_ids_for_manager) | Q(updated_by__in=user_ids_for_manager),
                is_deleted=False,
                branch=branch,
                company=company
            )
        elif user.has_perm("accounts.view_teamlead_order_others"):
            user_ids_for_teamlead = list(Employees.objects.filter(teamlead=usrid).values_list('user', flat=True))
            user_ids_for_teamlead.append(usrid)
            base_query = Order_Table.objects.filter(
                Q(order_created_by__in=user_ids_for_teamlead) | Q(updated_by__in=user_ids_for_teamlead),
                branch=branch,
                is_deleted=False,
                company=company
            )
        elif user.has_perm("accounts.view_own_order_others"):
            base_query = Order_Table.objects.filter(
                Q(order_created_by=usrid) | Q(updated_by=usrid),
                is_deleted=False,
                branch=branch,
                company=company
            )
        else:
            return []  # Or Response({...}, status=403)

        # Tile-wise permission check for agents
        if user.profile.user_type == "agent":
            tile_statuses = {
                "running_tile": ["running"],
                "pending_tile": ["Pending"],
                "accepted_tile": ["Accepted"],
                "rejected_tile": ["Rejected"],
                "no_response_tile": ["No Response"],
                "future_tile": ["Future Order"],
                "non_serviceable_tile": ["Non Serviceable"],
                "pendingspickup_tile": ["PICKUP PENDING"],
                "in_transit_tile": ["IN TRANSIT"],
                "ofd_tile": ["OUT FOR DELIVERY"],
                "delivered_tile": ["DELIVERED"],
                "initiatedrto": ["RTO INITIATED"],
                "rtodelivered_tile": ['RTO DELIVERED'],
                "exception_tile": ["EXCEPTION"],
                "ndr_tile": ["NDR"],
            }

            allowed_orders = Order_Table.objects.none()

            for tile_name, status_list in tile_statuses.items():
                if tile_name == "running_tile":
                    if user.has_perm(f"dashboard.view_all_dashboard_{tile_name}"):
                        allowed_orders |= base_query.filter(
                            Q(order_created_by=usrid) | Q(updated_by=usrid),
                            is_deleted=False,
                        )

                    elif user.has_perm(f"dashboard.view_manager_dashboard_{tile_name}"):
                        agent_ids = Employees.objects.filter(manager=usrid).values_list('user', flat=True)
                        user_ids_for_manager = set(
                            Employees.objects.filter(Q(teamlead__in=agent_ids) | Q(user=usrid)).values_list('user', flat=True)
                        ) | set(agent_ids)
                        user_ids_for_manager.add(usrid)
                        
                        allowed_orders |= base_query.filter(
                            Q(order_created_by__in=user_ids_for_manager) | Q(updated_by__in=user_ids_for_manager),
                            is_deleted=False,
                        )

                    elif user.has_perm(f"dashboard.view_teamlead_dashboard_{tile_name}"):
                        user_ids_for_teamlead = list(Employees.objects.filter(teamlead=usrid).values_list('user', flat=True))
                        user_ids_for_teamlead.append(usrid)
                        allowed_orders |= base_query.filter(
                            Q(order_created_by__in=user_ids_for_teamlead) | Q(updated_by__in=user_ids_for_teamlead),
                            is_deleted=False,
                        )

                    elif user.has_perm(f"dashboard.view_own_dashboard_{tile_name}"):
                        allowed_orders |= base_query.filter(
                            Q(order_created_by=usrid) | Q(updated_by=usrid),
                            is_deleted=False,
                            order_created_by=usrid
                        )
                else:
                    for status_name in status_list:
                        if user.has_perm(f"dashboard.view_all_dashboard_{tile_name}"):
                            allowed_orders |= base_query.filter(order_status__name=status_name, is_deleted=False)

                        elif user.has_perm(f"dashboard.view_manager_dashboard_{tile_name}"):
                            agent_ids = Employees.objects.filter(manager=usrid).values_list('user', flat=True)
                            user_ids_for_manager = set(
                                Employees.objects.filter(Q(teamlead__in=agent_ids) | Q(user=usrid)).values_list('user', flat=True)
                            ) | set(agent_ids)
                            user_ids_for_manager.add(usrid)
                            allowed_orders |= base_query.filter(
                                Q(order_created_by__in=user_ids_for_manager) | Q(updated_by__in=user_ids_for_manager),
                                is_deleted=False,
                                order_status__name=status_name,
                            )

                        elif user.has_perm(f"dashboard.view_teamlead_dashboard_{tile_name}"):
                            user_ids_for_teamlead = list(Employees.objects.filter(teamlead=usrid).values_list('user', flat=True))
                            user_ids_for_teamlead.append(usrid)
                            allowed_orders |= base_query.filter(
                                Q(order_created_by__in=user_ids_for_teamlead) | Q(updated_by__in=user_ids_for_teamlead),
                                order_status__name=status_name,
                                is_deleted=False,
                            )

                        elif user.has_perm(f"dashboard.view_own_dashboard_{tile_name}"):
                            allowed_orders |= base_query.filter(
                                Q(order_created_by=usrid) | Q(updated_by=usrid),
                                order_status__name=status_name,
                                is_deleted=False,
                            )

            allowed_orders = allowed_orders.distinct()
            if id is not None:
                allowed_orders = allowed_orders.filter(id=id)

            order_table_data = OrderTableSerializer(allowed_orders, many=True)
        else:
            # Non-agent: filter by ID if given
            if id is not None:
                base_query = base_query.filter(id=id)

            order_table_data = OrderTableSerializer(base_query, many=True)

        # Add product details
        # for row in order_table_data.data:
        #     order_details = OrderDetail.objects.filter(order=row['id'])
        #     row['product_details'] = OrderDetailSerializer(order_details, many=True).data

        return order_table_data.data

    except ObjectDoesNotExist:
        return []

def exportOrders(user_id, data):
    userData = Employees.objects.filter(user_id=user_id).first()
    if not userData:
        return {"error": "User not found"}
    serializer = UserProfileSerializer(userData)
    userSerializedData = serializer.data
    
    # Extract date range
    date_range = data.get('data_range', {})
    start_date_str = date_range.get('start_date')
    end_date_str = date_range.get('end_date')
    if not start_date_str or not end_date_str:
        return {"error": "Invalid date range: start_date or end_date is missing"}
    
    try:
        # Convert strings to datetime
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
        start_datetime = datetime.combine(start_date, time.min)
        end_datetime = datetime.combine(end_date, time.max)
    except ValueError as e:
        return {"error": f"Invalid date format: {str(e)}"}
    
    # Apply date filter based on date_type
    if data.get('date_type') == 'created_at':
        date_filter = Q(created_at__range=(start_datetime, end_datetime))
    else:
        date_filter = Q(updated_at__range=(start_datetime, end_datetime))

    filters = Q(branch=userSerializedData.get("branch")) & Q(company=userSerializedData.get("company"))
    filters &= date_filter
    if data.get('status') != 0:
        filters &= Q(order_status=data.get('status'))

    tableData = Order_Table.objects.filter(filters)
    orderTableData = OrderTableSerializer1(tableData, many=True)
    return orderTableData.data


def ivoiceDeatail(user_id, data):
    tableData = Order_Table.objects.filter(order_id__in=data['invoices'])
    orderTableData = InvoiceSerializer(tableData, many=True)
    return orderTableData.data


def checkServiceability(branch_id,company_id,data):
    pincode=data['pincode']
    mobile=data['mobile']
    re_order=data['re_order']
    trackdata = ShipmentModel.objects.filter(branch=None,company=None,status=1)
    pickUppointData = PickUpPoint.objects.filter(company=company_id,status=1)
    pickUpSerializerData = PickUpPointSerializer(pickUppointData, many=True)
    serializer = ShipmentSerializer(trackdata, many=True)
    serialized_data = serializer.data
    if mobile:
        orderData = Order_Table.objects.filter(branch=branch_id,company=company_id,customer_phone=f'+91{mobile[-10:]}'
    ).first()
        if orderData and int(re_order) == 0:
            return 1
    eddshortestTime=365
    EddList=[]
    odablock = False
    for pickUpPinCode in pickUpSerializerData.data:
        EddDataShowDict={}
        for data in serialized_data:
            token=None
            EddDataShowDict['provider_name']=data['shipment_vendor']['name'].lower() 
            EddDataShowDict['name']= data['shipment_vendor']['name'].lower() 
            EddDataShowDict['shipment_id']=data['id']
            EddDataShowDict['pickup_point']=pickUpPinCode['pincode']
            EddDataShowDict['pickupname']= pickUpPinCode['contact_person_name']
            EddDataShowDict['pickup_city']=pickUpPinCode['city']
            EddDataShowDict['pickup_id']=pickUpPinCode['id']
            if data['shipment_vendor']['name'].lower()=='shiprocket':
                if data['credential_username']!='' or data['credential_username']!=None:
                    token=getShipRocketToken(data['credential_username'],data['credential_password'])
                url = "https://apiv2.shiprocket.in/v1/external/courier/serviceability/"
                payload = json.dumps({
                "pickup_postcode": f"{pickUpPinCode['pincode']}",
                "delivery_postcode": f"{pincode}",
                "weight": 0.5,
                "cod": 1
                })
                print(payload,"------------------------------------655")
                headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {token}'
                }
                response = requests.request("GET", url, headers=headers, data=payload)
                print(response,"-------------------------------660",response.json())
                a=0
                shortestDayData={}
                cutomerCity=''
                cutomerState=''
                if response.json()['status']==200:
                    for apiData in response.json()['data']['available_courier_companies']:
                        if apiData['odablock']==True:
                            odablock = True
                        if int(eddshortestTime)>int(apiData['estimated_delivery_days']):
                            eddshortestTime=int(apiData['estimated_delivery_days'])
                            shortestDayData['courier_name']=apiData['courier_name']
                            shortestDayData['EDD']=apiData['estimated_delivery_days']
                            cutomerCity=apiData['city']
                            cutomerState=apiData['state']
                    EddDataShowDict['eddtime']=eddshortestTime
                    EddDataShowDict['delivery_city']=cutomerCity
                    EddDataShowDict['delivery_state']=cutomerState
                    EddDataShowDict['odablock'] = odablock
                    EddList.append(EddDataShowDict)
                    eddshortestTime=365
                else:
                    return 2
                    # EddDataShowDict['massage']=response.json()['message']
                    # EddList.append(EddDataShowDict)
            else:
                pass
        print(EddList,"---------------eddlist")
    return EddList


from django.utils.html import strip_tags
def trigger_order_status_notifications(company_id, order_status_id, order_id):
    try:
        order = Order_Table.objects.get(id=order_id)
    except Order_Table.DoesNotExist:
        return

    services_enabled = ['sms', 'email', 'whatsapp']
    for service in services_enabled:
        sms_config = SmsConfig.objects.filter(
            company_id=company_id,
            order_status__id=order_status_id,
            notification_type=service
        ).first()
    
        if sms_config:
            first_product = OrderDetail.objects.filter(order=order).first()
            product_name = first_product.product_name if first_product else "Product"

            # message = f"""Hey {order.customer_name}!
            # Your order from {sms_config.brand_name or order.company.name} is {order.order_status.name}
            # You can find the order details below👇:
            # Order ID: {order.order_id}
            # Item(s) Included in the shipment:
            # {product_name}
            # Order Amount: ₹{order.total_amount}
            # Payment Mode: {order.payment_type.name} for more info call
            # Support Contact {sms_config.mobile_number}
            # From {sms_config.website}
            # Thank you for choosing {sms_config.brand_name or order.company.name}!!
            # Ordered via CrewOrder"""
            message = f"""Hey {order.customer_name}!
Your order from {sms_config.brand_name or order.company.name} is {order.order_status.name}
You can find the order details below: Order ID: {order.order_id}
Item(s) Included in the shipment:
{product_name}
Order Amount: ₹{order.total_amount}
Payment Mode: {order.payment_type.name}
for more info call Support Contact {sms_config.mobile_number}
From {sms_config.email}
Thank you for choosing {sms_config.brand_name or order.company.name}!!
Ordered via CrewOrder"""
            if service == 'sms':
                send_otp_to_number(
                    number=order.customer_phone,
                    otp="",
                    purpose="order_notify",
                    custom_message=strip_tags(message)
                )

            elif service == 'email':
                subject = "Order Status Updated"
                template = "emails/order_status_update.html"
                context = {
                    "order_id": order.order_id,
                    "status": order.order_status.status,
                    "customer_name": order.customer_name,
                    "product_names": product_name,
                    "amount": order.total_amount,
                    "brand_name":sms_config.brand_name,
                    "payment_mode":order.payment_type.name,
                    "support_contact":  sms_config.mobile_number,
                    "website": sms_config.website,
                }
                html_message = render_to_string(template, context)
                recipient_list = [order.customer_email]

                send_email(subject, html_message, recipient_list, email_type='order')

            # elif service == 'whatsapp':
            #     send_whatsapp_to_customer(order.customer_phone, message)






def attach_product_details(mutable_data):
    product = Products.objects.filter(product_id=mutable_data.get('product_id')).first()
    if not product:
        return None, Response({"error": "Product not found."}, status=status.HTTP_400_BAD_REQUEST)

    product_details = [{
        "product": product.id,
        "product_qty": int(mutable_data.get("product_qty",0))
    }]

    mutable_data.pop("product_id", None)
    mutable_data.pop("product_qty", None)
    mutable_data['product_details'] = product_details

    return mutable_data, None
