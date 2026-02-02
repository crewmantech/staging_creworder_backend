import datetime
import json
import requests
import logging
from accounts.models import Employees, PickUpPoint
from accounts.serializers import UserProfileSerializer, PickUpPointSerializer
from middleware.request_middleware import get_request
from services.orders.order_service import checkServiceability, orderLogInsert
from services.products.products_service import getProduct
from shipment.models import ShipmentModel
from shipment.serializers import ShipmentSerializer
from orders.models import Customer_State, Order_Table,OrderLogModel, OrderStatus
from orders.serializers import OrderTableSerializer, ProductSerializer
from django.core.exceptions import ObjectDoesNotExist
from utils.custom_logger import setup_logging

logger = logging.getLogger(__name__)
setup_logging(log_file='logs/shipment_service.log', log_level=logging.WARNING)
from datetime import datetime

def eshopbox_date(dt_string):
    """
    Converts '29-Jan-2026 03:08 PM'
    to '2026-01-29 15:08:00'
    """
    dt = datetime.strptime(dt_string, "%d-%b-%Y %I:%M %p")
    return dt.strftime("%Y-%m-%d %H:%M:%S")
def sanitize_for_eshopbox(payload):
    import time
    import re

    payload["ewaybillNumber"] = "0"
    payload["shipmentValue"] = payload["invoiceTotal"]
    payload["collectableAmount"] = payload["balanceDue"]

    for addr in ["shippingAddress", "billingAddress"]:
        payload[addr]["contactPhone"] = re.sub(r"\D", "", payload[addr]["contactPhone"])
        payload[addr]["email"] = payload[addr]["email"] or "noreply@creworder.com"

    payload["pickupLocation"]["contactNumber"] = re.sub(
        r"\D", "", payload["pickupLocation"]["contactNumber"]
    )

    payload["package"]["code"] = str(int(time.time()))

    return payload

class ShiprocketScheduleOrder:
    """
    A class to handle Shiprocket scheduling orders.
    """
    base_url="https://apiv2.shiprocket.in/v1"
    LOGIN_URL=base_url+'/external/auth/login'
    SERVICEABILITY=base_url+'/external/courier/serviceability/'
    create_custom_order=base_url+'/external/orders/create/adhoc'
    create_specific_order = base_url+'/external/orders/create'
    GET_AWB=base_url+'/external/courier/assign/awb'
    channel_url = base_url+"/external/channels"
    genrate_pickup_url= base_url+"/external/courier/generate/pickup"
    NDR_ALL_URL = base_url + "/external/ndr/all"
    NDR_DETAIL_URL = base_url + "/external/ndr/"
    NDR_ACTION_URL = base_url + "/external/ndr"
    PICKUP_LOCATIONS_URL = base_url + "/external/settings/company/pickup"
    ADD_PICKUP_LOCATION_URL = base_url + "/external/settings/company/addpickup"
    WALLET_BALANCE_URL = base_url+"/external/account/details/wallet-balance"
    GET_ORDER_DETAILS_API = base_url+"/external/orders/show/"
    cancel_order_url = base_url+"/external/orders/cancel"
    manifest_url = base_url+"/external/manifests/generate"
    teacker_url = base_url+"/external/courier/track/shipment/"
    gnerate_manifest_url = base_url+"/external/manifests/generate"
    print_manifest_url = base_url+"/external/manifests/print"
    genrate_label_url = base_url+"/external/labels/generate"
    generate_invoice_url = base_url+"external/invoices/generate"
    shipment_details_url = base_url+"/external/shipments"
    token=''
    def __init__(self,email:str,password:str):
        """
        Initializes the ShiprocketScheduleOrder class with API credentials.

        :param api_key: API key for authenticating requests.
        :param base_url: Base URL for Shiprocket API.
        """
        self.email=email
        self.password=password
        self.base_url = self.base_url
        self.token=self._get_token(self.email,self.password)
        self.headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.token}'
        }

    def _get_token(self, email: str, password: str) -> str:
        """
        Private method to get the Shiprocket token.
        """
        url = f"{self.base_url}/external/auth/login"
        payload = json.dumps({
            "email": email,
            "password": password
        })

        try:
            response = requests.post(url, headers={'Content-Type': 'application/json'}, data=payload)
            response.raise_for_status()
            return response.json().get('token')
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching token: {e}")
            return None

    @staticmethod
    def makeJsonForApi(order_data: dict,channel_id,pickup) -> bool:
        """
        Static method to validate order data before scheduling.
        :param order_data: Dictionary containing order details.
        :return: True if valid, False otherwise.
        """
        _itemsList = []
        if order_data['order_details']:
            for _item in order_data['order_details']:
                _itemDict = { 
                    "name": _item["product_name"],
                    "sku": _item["product_sku"],
                    "selling_price": _item["product_price"],
                    "units": _item["product_qty"],
                }
                _itemsList.append(_itemDict)
            
        _RequestJson = {
            "order_id": f"{order_data['order_id']}",
            "order_date": f"{order_data['created_at']}",
            "pickup_location": pickup.pickup_code,
            "channel_id": str(channel_id),
            "comment": f"{order_data['order_remark']}",
            "billing_customer_name": f"{order_data['customer_name']}",
            "billing_last_name": "",
            "billing_address": f"{order_data['customer_address']}",
            "billing_address_2": "",
            "billing_city": f"{order_data['customer_city']}",
            "billing_pincode": f"{order_data['customer_postal']}",
            "billing_state": f"{order_data['customer_state_name']}",
            "billing_country": order_data['customer_country'],
            "billing_email": pickup.contact_email,
            "billing_phone": f"{order_data['customer_phone'][-10:]}",
            "shipping_is_billing": True,
            "shipping_customer_name": f"{order_data['customer_name']}",
            "shipping_last_name": "",
            "shipping_address": f"{order_data['customer_address']}",
            "shipping_address_2": "",
            "shipping_city": order_data['customer_city'],
            "shipping_pincode": f"{order_data['customer_postal']}",
            "shipping_country": order_data['customer_country'],
            "shipping_state": f"{order_data['customer_state_name']}",
            "shipping_email": "",
            "shipping_phone": f"{order_data['customer_phone'][-10:]}",
            "order_items": _itemsList,
            "payment_method": "Prepaid" if order_data['payment_type_name'] == "Prepaid Payment" else "COD",
            "shipping_charges": 0,
            "giftwrap_charges": 0,
            "transaction_charges": 0,
            "total_discount": 0,
            "sub_total": order_data['cod_amount'],
            "length": "13",
            "breadth": "13",
            "height": "8",
            "weight": "0.5"
        }
        return  _RequestJson

    def schedule_order(self, order_list:list, branch_id:int ,company_id:int,channel_id,user_id,pickup_id,shipment_vendor):
        """
        Public method to schedule an order using the Shiprocket API.

        :param order_data: Dictionary containing order details.
        :return: Response from the Shiprocket API.
        """
        OrdersData = Order_Table.objects.filter(company=company_id,id__in=order_list)
        OrdersDataSerializer = OrderTableSerializer(OrdersData, many=True)
        _OrderLogJson=[]
        _ResponsesDict=[]
        for order in OrdersDataSerializer.data:
            pickup_point_id = pickup_id
            if not pickup_point_id:
                return {"status": "error", "message": "Pickup point not provided in order data."}
            try:
                pickup = PickUpPoint.objects.get(id=pickup_point_id)
                pickup_pincode = pickup.pincode 
                pickup_location = pickup.pickup_code # Adjust field name if different
            except PickUpPoint.DoesNotExist:
                return {"status": "error", "message": f"Pickup point with ID {pickup_point_id} does not exist."}
            _request_json = self.makeJsonForApi(order, channel_id,pickup)
            api_endpoint = self.create_specific_order if channel_id else self.create_custom_order
            

            # Fetch pickup pincode from the Pickup model
            

            # Extract other details from the order_data
            delivery_pincode = order.get("customer_postal")
            # order_weight = 0.5  # Replace with the actual weight of the order if available
            cod = 0 if order.get("payment_type_name", "").lower() == "prepaid" else 1
            result = self.check_serviceability(
            pickup_pincode= pickup_pincode,
            delivery_pincode=delivery_pincode,
            weight=1.0,
            cod=cod
            )
            try:
                response = requests.post(api_endpoint, headers=self.headers, json=_request_json)
                
                # response.raise_for_status()
                # Process response
                if response.status_code == 200:
                    response_data = response.json()
                    print(response_data)
                    if response_data.get('status') == 'NEW':
                        shipment_id = response_data.get('shipment_id', "")
                        vendor_order_id =str(response_data.get('order_id', ""))
                        _awbJson = {
                            "shipment_id": response_data.get('shipment_id', ""),
                            # "courier_id": "",
                            # "status": ""
                        }
                        
                        try:
                            # Fetch AWB details
                            try:
                                awb_response = requests.post(self.GET_AWB, headers=self.headers, json=_awbJson)
                                awb_response.raise_for_status()
                                awb_data = awb_response.json()
                                awb_data = awb_response.json().get('response', {}).get('data', {})
                                # order_details_json = {
                                #     "awb_code": awb_data.get('awb_code', '')  # Using the AWB code from the response
                                # }
                                # order_details_response = requests.request("GET", self.GET_ORDER_DETAILS_API+vendor_order_id, headers=self.headers, data={})
                                # # order_details_response = requests.post(self.GET_ORDER_DETAILS_API+vendor_order_id, headers=self.headers, json=order_details_json)
                                # order_details_response.raise_for_status()
                                # order_details_data = order_details_response.json().get('response', {})
                                # estimated_delivery_date = order_details_data.get('edd', None)
                                print("AWB Response:", awb_data)
                            except requests.exceptions.HTTPError as e:
                                print("AWB Request Failed:", awb_response.text)
                                raise
                            UpdateInstance = Order_Table.objects.filter(branch=branch_id, company=company_id, id=order['id'])
                            order_status, created = OrderStatus.objects.get_or_create(
                                name='PICKUP PENDING'
                                # branch=branch_id,
                                # company=company_id
                            )
                            # order_status, created = OrderStatus.objects.get_or_create(name='SCHEDULED')
                            status_id = order_status.id
                            res = UpdateInstance.update(
                                order_wayBill=awb_data.get('awb_code', ''),
                                order_ship_by=awb_data.get('courier_name', ''),
                                assigned_date_time=awb_data.get('assigned_date_time', {}).get('date', {}),
                                freight_charges=awb_data.get('freight_charges', None),
                                awb_response=awb_data, 
                                estimated_delivery_date=result.get('estimated_delivery_date', None),
                                shipment_id =shipment_id, 
                                vendor_order_id=vendor_order_id,
                                is_booked=1,
                                order_status = status_id,
                                shipment_vendor = shipment_vendor
                            )
                            _ResponsesDict.append({"order": f"{order['id']}", "message": "Order IN PICKUP PENDING successfully"})
                            # Log the action
                            _logJson = {
                                'order': order['id'],
                                'order_status': status_id,
                                'action_by': user_id,  # Assuming you have access to the current user
                                'remark': 'Order PICKUP PENDING successfully',
                            }
                            # orderLogInsert(_logJson)
                            orderLogInsert({
                                "order": order['id'],
                                "order_status": status_id,
                                "action_by": user_id,
                                "action": 'Order in PICKUP PENDING successfully',
                                
                                "remark": 'Order in PICKUP PENDING successfully'
                            })
                           
                            _OrderLogJson.append(_logJson)
                            print("AWB Response:", awb_data)
                        except requests.exceptions.RequestException as e:
                            print(str(e))
                            _ResponsesDict.append({"order": f"{order['id']}", "message": str(e)})
                            print("Error fetching AWB:", e)
                    else:
                        _ResponsesDict.append({
                            "order": f"{order['id']}",
                            "message": f"Order created but status on Shiprocket is {response_data.get('status')}"
                        })
                else:
                    _ResponsesDict.append({"order": f"{order['id']}", "message": response.text})
                    print(f"Request failed for order {order['id']}: {response.text}")
            
            except requests.exceptions.RequestException as e:
                _ResponsesDict.append({"order": f"{order['id']}", "message": str(e)})
                print(f"An error occurred for order {order['id']}:", e)
        # OrderLogModel
        return _ResponsesDict
    
    def Ship_channels(self):
        """
        Fetch the available shipping channels from Shiprocket.
        :return: List of available shipping channels or an error message.
        """
        try:
            response = requests.get(self.channel_url, headers=self.headers)
            response.raise_for_status()
            channels_data = response.json()
            if 'data' in channels_data:
                return channels_data
            else:
                logger.error("No channel data found in the response.")
                return {"error": "No channel data found"}
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching channels: {e}")
            return {"error": f"Error fetching channels: {e}"}
        
    def generate_pickup(self, order_list: list, branch_id: int, company_id: int):
        orders_data = Order_Table.objects.filter(branch=branch_id, company=company_id, id__in=order_list)
        orders_serializer = OrderTableSerializer(orders_data, many=True)
        pickup_responses = []
        log_entries = []
        for order in orders_serializer.data:
            # Construct payload for pickup request
            pickup_payload = {
                "shipment_id": order.get("shipment_id"),
                # "pickup_location": order.get("pickup_location"),  # Replace with actual field or static value
            }
            try:
                # Make API call to generate pickup
                response = requests.post(
                    url=self.genrate_pickup_url,
                    headers=self.headers,
                    json=pickup_payload,
                )
                # response.raise_for_status()
                response_data = response.json()
                order_status, created = OrderStatus.objects.get_or_create(
                                name='IN_TRANSIT'
                                # branch=branch_id,
                                # company=company_id
                            )
                status_id = order_status.id
                if response_data.get("pickup_status") == 1:
                    # Update order with pickup details
                    Order_Table.objects.filter(
                        branch=branch_id, company=company_id, id=order["id"]
                    ).update(is_pickup_scheduled=True, pickup_id=response_data.get("response",{}).get("Reference No"),order_status = status_id)

                    # Add successful pickup log
                    log_entries.append({
                        "order_id": order["id"],
                        "status": "Pickup IN TRANSIT",
                        "pickup_id": response_data.get("pickup_id"),
                    })
                else:
                    # Log error response from API
                    pickup_responses.append({
                        "order_id": order["id"],
                        "error": response_data.get("message", "Unknown Error"),
                    })

            except requests.exceptions.RequestException as e:
                # Handle request errors
                pickup_responses.append({
                    "order_id": order["id"],
                    "error": str(e),
                })

        # Log results
        print("Pickup Responses:", pickup_responses)
        print("Pickup Logs:", log_entries)

        # Return the result of pickups
        return {
            "success_logs": log_entries,
            "errors": pickup_responses,
        }
    
    def track_order(self, shipment_id: str):
        tracking_url = f"{self.teacker_url}{shipment_id}"
        try:
            response = requests.get(tracking_url, headers=self.headers)
            print(response.json(),"--------------340")
            response.raise_for_status()
            tracking_data = response.json()
            # Check for valid tracking data
            if "tracking_data" in tracking_data:
                return {
                    "status": "success",
                    "tracking_data": tracking_data["tracking_data"],
                }
            else:
                return {
                    "status": "failed",
                    "message": tracking_data.get("message", "No tracking data found."),
                }
        except requests.RequestException as e:
            logger.error(f"Error tracking shipment ID {shipment_id}: {e}")
            return {
                "status": "error",
                "message": f"An error occurred while tracking the shipment: {str(e)}",
            }
        
    def get_wallet_balance(self):
        """
        Fetches the wallet balance details from the Shiprocket API.

        :return: Wallet balance details as a dictionary.
        """
        try:
            response = requests.get(self.WALLET_BALANCE_URL, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Error fetching wallet balance: {e}")
            return {
                "status": "error",
                "message": f"An error occurred while fetching wallet balance: {str(e)}",
            }
        
    def get_all_ndr_shipments(self):
        """
        Fetch all NDR shipments.
        """
        try:
            response = requests.get(self.NDR_ALL_URL, headers=self.headers)
            # response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Error fetching all NDR shipments: {e}")
            return {"status": "error", "message": str(e)}

    def get_ndr_shipment_details(self, shipment_id: str):
        """
        Fetch details of a specific NDR shipment.
        """
        try:
            url = f"{self.NDR_DETAIL_URL}{shipment_id}"
            response = requests.get(url, headers=self.headers)
            # response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Error fetching NDR shipment details: {e}")
            return {"status": "error", "message": str(e)}

    def action_ndr(
    self,
    awb: str,
    action: str,
    comments: str = None,
    phone: str = None,
    proof_audio: str = None,
    proof_image: str = None,
    remarks: str = None,
    address1: str = None,
    address2: str = None,
    deferred_date: str = None,
    **kwargs
    ):
        """
        Perform an NDR action for Shiprocket, supporting ALL documented parameters.
        Unknown kwargs are ignored safely.
        """

        url = f"{self.NDR_ACTION_URL}/{awb}/action"

        # Base payload required by Shiprocket
        payload = {
            "action": action,
            "comments": comments or "",
        }

        # Optional documented Shiprocket fields (only include if provided)
        if phone:
            payload["phone"] = phone
        if proof_audio:
            payload["proof_audio"] = proof_audio
        if proof_image:
            payload["proof_image"] = proof_image
        if remarks:
            payload["remarks"] = remarks
        if address1:
            payload["address1"] = address1
        if address2:
            payload["address2"] = address2
        if deferred_date:
            payload["deferred_date"] = deferred_date

        # Ignore unknown kwargs but log them
        if kwargs:
            logger.debug(f"Ignored unsupported kwargs in Shiprocket.action_ndr: {kwargs}")

        try:
            response = requests.post(url, headers=self.headers, json=payload)

            # Return BOTH body and status code (important for your API view)
            try:
                body = response.json()
            except Exception:
                body = {"message": response.text}

            return body, response.status_code

        except requests.RequestException as e:
            logger.error(f"Error performing action on NDR shipment: {e}")
            return {"status": "error", "message": str(e)}, 500
    # def action_ndr(self, shipment_id: str, action: str, date: str = None):
    #     """
    #     Perform an action on an NDR shipment.
    #     """
    #     payload = {
    #         "shipment_id": shipment_id,
    #         "action": action,
    #     }
    #     if action == "reschedule_delivery" and date:
    #         payload["date"] = date

    #     try:
    #         print("---------------424",self.NDR_ACTION_URL,"-----------------424")
    #         response = requests.post(self.NDR_ACTION_URL, headers=self.headers, json=payload)
    #         print(response,"------------------425")
    #         # response.raise_for_status()
    #         return response.json()
    #     except requests.RequestException as e:
    #         logger.error(f"Error performing action on NDR shipment: {e}")
    #         return {"status": "error", "message": str(e)}
        
    def get_all_pickup_locations(self):
        """
        Fetch all pickup locations.
        """
        try:
            response = requests.get(self.PICKUP_LOCATIONS_URL, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Error fetching all pickup locations: {e}")
            return {"status": "error", "message": str(e)}

    def add_pickup_location(self, location_data: dict):
        """
        Add a new pickup location.
        """
        try:
            response = requests.post(self.ADD_PICKUP_LOCATION_URL, headers=self.headers, json=location_data)
            # response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Error adding pickup location: {e}")
            return {"status": "error", "message": str(e)}
        
    def check_serviceability(self, pickup_pincode: str, delivery_pincode: str, weight: float = 0.5, cod: bool = False):
        try:
            # Construct the serviceability URL
            serviceability_url = f"{self.SERVICEABILITY}?pickup_postcode={pickup_pincode}&delivery_postcode={delivery_pincode}&weight={weight}&cod={str(cod).lower()}"

            # Make the API request
            response = requests.get(serviceability_url, headers=self.headers)
            response.raise_for_status()
            serviceability_data = response.json()

            # Return serviceability details if available
            if "status" in serviceability_data and serviceability_data["status"] == 200:
                courier_data = serviceability_data["data"]
                eddshortestTime=365
                for apiData in response.json()['data']['available_courier_companies']:
                    if int(eddshortestTime)>int(apiData['estimated_delivery_days']):
                        eddshortestTime=int(apiData['estimated_delivery_days'])
                today = datetime.date.today()
                eddshortestTime = today + datetime.timedelta(days=eddshortestTime)
                return {
                    "status": "serviceable",
                    "estimated_delivery_date": eddshortestTime
                }
            else:
                return {
                    "status": "error",
                    "message": serviceability_data.get("message", "Unknown error occurred."),
                }

        except requests.RequestException as e:
            logger.error(f"Error checking serviceability: {e}")
            return {"status": "error", "message": f"An error occurred: {str(e)}"}
        

    def cancel_order(self, order_id, reason):
       
        payload = {"ids": [order_id]}
        if reason:
            payload["reason"] = reason

        try:
            response = requests.post(self.cancel_order_url, headers=self.headers, json=payload)
            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            print(f"An error occurred while canceling order {order_id}: {e}")
            return {"error": str(e)}
        

    def generate_manifest(self, shipment_ids: list):
        """
        Generate a manifest for the provided shipment IDs.
        """
        url = self.gnerate_manifest_url
        payload = {"shipment_ids": shipment_ids}
        try:
            response = requests.post(url, json=payload, headers=self.headers)
            print(response.status_code, response.text, "------ Manifest Response ------")
            response.raise_for_status()  # Raise an exception for HTTP errors
            manifest_data = response.json()

            if "manifest_url" in manifest_data and manifest_data["manifest_url"]:
                return {"status": "success", "manifest_url": manifest_data["manifest_url"]}
            else:
                print(f"Manifest generation failed. Response data: {manifest_data}")
                return {
                    "status": "failed",
                    "message": manifest_data.get("message", "Manifest URL not available."),
                    "error_details": manifest_data.get("error", "No additional error details."),
                }
        except requests.RequestException as e:
            logger.error(f"Error generating manifest: {e}")
            return {
                "status": "error",
                "message": f"An error occurred while generating the manifest: {str(e)}",
            }

    def print_manifest(self, manifest_id: str):
        """
        Print a manifest using the provided manifest ID.
        """
        url = self.print_manifest_url
        payload = {"manifest_id": manifest_id}
        try:
            response = requests.post(url, json=payload, headers=self.headers)
            print(response.status_code, response.text, "------ Print Manifest Response ------")
            # response.raise_for_status()  # Raises an HTTPError if the response contains an HTTP error status code
            print_data = response.json()
            print(print_data.get('error'))
            if "manifest_url" in print_data and print_data["manifest_url"]:
                return {"status": "success", "manifest_url": print_data["manifest_url"]}
            else:
                return {
                    "status": "failed",
                    "message": print_data.get("message", "Manifest URL not available."),
                    "error_details": print_data.get("error", "No additional error details."),
                }

        except requests.HTTPError as http_err:
            # Attempt to parse the response JSON for error details
            try:
                error_data = response.json()
                message = error_data.get("message", "An unexpected error occurred.")
                error_details = error_data.get("error", [])
            except ValueError:  # If response JSON cannot be parsed
                message = str(http_err)
                error_details = []

            logger.error(f"HTTPError while printing manifest: {http_err}")
            return {
                "status": "failed",
                "message": f"HTTP error occurred: {message}",
                "error_details": error_details,
            }

        except requests.RequestException as req_err:
            logger.error(f"RequestException while printing manifest: {req_err}")
            return {
                "status": "error",
                "message": f"An error occurred while printing the manifest: {str(req_err)}",
                "error_details": [],
            }

    def generate_label(self, shipment_ids: list):
        """
        Generate labels for the provided shipment IDs.
        """
        url = self.genrate_label_url
        payload = {"shipment_ids": shipment_ids}
        try:
            response = requests.post(url, json=payload, headers=self.headers)
            print(response.status_code, response.text, "------ Label Generation Response ------")
            # response.raise_for_status()
            label_data = response.json()

            if "label_url" in label_data and label_data["label_url"]:
                return {"status": "success", "label_url": label_data["label_url"]}
            else:
                print(f"Label generation failed. Response data: {label_data}")
                return {
                    "status": "failed",
                    "message": label_data.get("message", "Label URL not available."),
                    "error_details": label_data.get("error", "No additional error details."),
                }
        except requests.RequestException as e:
            logger.error(f"Error generating label: {e}")
            return {
                "status": "error",
                "message": f"An error occurred while generating the label: {str(e)}",
            }

    def generate_invoice(self, shipment_ids: list):
        """
        Generate invoices for the provided shipment IDs.
        """
        url = self.generate_invoice_url
        payload = {"shipment_ids": shipment_ids}
        try:
            response = requests.post(url, json=payload, headers=self.headers)
            print(response.status_code, response.text, "------ Invoice Generation Response ------")
            # response.raise_for_status()
            invoice_data = response.json()

            if "invoice_url" in invoice_data and invoice_data["invoice_url"]:
                return {"status": "success", "invoice_url": invoice_data["invoice_url"]}
            else:
                print(f"Invoice generation failed. Response data: {invoice_data}")
                return {
                    "status": "failed",
                    "message": invoice_data.get("message", "Invoice URL not available."),
                    "error_details": invoice_data.get("error", "No additional error details."),
                }
        except requests.RequestException as e:
            logger.error(f"Error generating invoice: {e}")
            return {
                "status": "error",
                "message": f"An error occurred while generating the invoice: {str(e)}",
            }
    def shipment_details(self, shipment_id=None):
        """
        Fetch shipment details for a given shipment ID.
        """
        if shipment_id :
            url = f"{self.shipment_details_url}/{shipment_id}"
        else:
            url = self.shipment_details_url
        try:
            response = requests.get(url, headers=self.headers)
            # response.raise_for_status()
            details = response.json()
            return {
                "status": "success",
                "shipment_details": details
            }

        except requests.RequestException as e:
            self.logger.error(f"Error fetching shipment details for {shipment_id}: {e}")
            return {
                "status": "error",
                "message": f"An error occurred while fetching shipment details: {str(e)}"
            }
        



import requests
import json
import logging

logger = logging.getLogger(__name__)

class TekipostService:
    BASE_URL = "https://app.tekipost.com"
    LOGIN_URL = "/api-login"
    def __init__(self, email: str, password: str):
        """
        Initializes the TekipostService class with automatic token generation.
        """
        self.email = email
        self.password = password
        self.token = self._get_token()
        
        if not self.token:
            raise Exception("Failed to authenticate with TEKIPOST API.")
        
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.token}"
        }

    def _get_token(self) -> str:
        """
        Private method to get the TEKIPOST token during initialization.
        """
        data = {"email": self.email, "password": self.password}
        try:
            response = requests.post(f"{self.BASE_URL}{self.LOGIN_URL}", json=data)
            response.raise_for_status()
            print(response.json(),"--------------------------------")
            token = response.json().get("data",{}).get("token")
            if not token:
                logger.error("Token not found in the response.")
            return token
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching token: {e}")
            return None

    def _post(self, endpoint, data=None):
        url = f"{self.BASE_URL}{endpoint}"
        try:
            response = requests.post(url, headers=self.headers, json=data)
            # response.raise_for_status()
           
         

            return response.json()
        
        except requests.exceptions.RequestException as e:
            logger.error(f"POST Request Failed: {url} - {e}")
            return {"error": str(e)}

    def _get(self, endpoint):
        url = f"{self.BASE_URL}{endpoint}"
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"GET Request Failed: {url} - {e}")
            return {"error": str(e)}
        
    @staticmethod
    def makeJsonForApi(self,order_data: dict,channel_id,pickup) -> bool:
        """
        Static method to validate order data before scheduling.
        :param order_data: Dictionary containing order details.
        :return: True if valid, False otherwise.
        """
        print(order_data,"-----------------------70")
        _itemsList = []
        product_height =0
        prouduct_length = 0
        product_weight = 0
        product_width = 0
        product_hsn = ''
        if order_data['order_details']:
            for _item in order_data['order_details']:
                request = get_request()
                user = request.user
                data = getProduct(user.id, _item["product"])
                serializer = ProductSerializer(data, many=True)
                product_data = serializer.data[0]
                prouduct_length = product_data.get('product_size') if prouduct_length < product_data.get('product_size') else prouduct_length
                product_height = product_data.get('product_height') if product_height < product_data.get('product_height') else product_height
                product_weight = product_data.get('product_weight')+product_weight
                product_width = product_data.get('product_width') if product_width < product_data.get('product_width') else product_width
                product_hsn = product_data.get('product_hsn_number')
                _itemDict = { 
                    "product_name": _item["product_name"],
                    "sku_number": _item["product_sku"],
                    "product_value": _item["product_price"],
                    "product_quantity": _item["product_qty"],
                }
                _itemsList.append(_itemDict)
        try:
            state = Customer_State.objects.get(id=order_data['customer_state'])
            state_name = state.name
        except Customer_State.DoesNotExist:
            print("State not found")
        _RequestJson = {
                # "logistic_id" : 1,
                # "isorder" : 1,
                "consignee_name": f"{order_data['customer_name']}",
                "mobile_no": f"{order_data['customer_phone']}",
                "alternate_mobile_no": f"{order_data['customer_alter_phone']}",
                "email_id": pickup.get('contact_email'),
                "receiver_address": f"{order_data['customer_address']}",
                "receiver_pincode": f"{order_data['customer_postal']}",
                "receiver_city": f"{order_data['customer_city']}",
                "receiver_state":state_name,
                "receiver_landmark": f"{order_data['customer_name']}",
                "customer_order_no": f"{order_data['order_id']}",
                "order_type":"0" if order_data['payment_type_name'] == "Prepaid Payment" else "1",
                "product_quantity": len(_itemsList),
                "cod_amount":  float(order_data['cod_amount']),
                "physical_weight": product_weight,
                "product_length": prouduct_length,
                "product_width": product_width,
                "product_height": product_height,
                "hsn_number": product_hsn,
                "order_value": f"{order_data['total_amount']}",
                "productdetatis":_itemsList,
                "sender_address_id": pickup.get('pickup_code'),
                "return_address_same_as_pickup_address": 1,
                "return_consignee_name": pickup.get('contact_person_name'),
                "return_mobile_no": pickup.get('contact_number'),
                "return_alternate_mobile_no": pickup.get('alternate_contact_number'),
                "return_address": pickup.get('complete_address'),
                "return_pincode": pickup.get('pincode'),
                "return_city": pickup.get('city'),
                "return_state": pickup.get('state'),
                "return_landmark": pickup.get('landmark')
                }
        return  _RequestJson
    def schedule_order(self, order_list:list, branch_id:int ,company_id:int,channel_id,user_id,pickup_id,shipment_vendor):

        OrdersData = Order_Table.objects.filter(company=company_id,id__in=order_list)
        OrdersDataSerializer = OrderTableSerializer(OrdersData, many=True)
        _OrderLogJson=[]
        _ResponsesDict=[]
        for order in OrdersDataSerializer.data:
            pickup_point_id = pickup_id
            if not pickup_point_id:
                return {"status": "error", "message": "Pickup point not provided in order data."}
            try:
                pickup = PickUpPoint.objects.get(id=pickup_point_id)
                print(pickup,"-------------------843-------------------")
                pickup_data = PickUpPointSerializer(pickup)
                pickup = pickup_data.data
                print(pickup,"-------------------843-------------------",shipment_vendor)
                print(pickup.get('contact_email'))
                # pickup_pincode = pickup.get('pincode') 
                # pickup_location = pickup.pickup_code
                # pickup_location = pickup.contact_person_name # Adjust field name if different

            except PickUpPoint.DoesNotExist:
                return {"status": "error", "message": f"Pickup point with ID {pickup_point_id} does not exist."}
            print(order,"---------------155")
            _request_json = self.makeJsonForApi(self,order, channel_id,pickup)
            print(_request_json,"------------------830",self)
           
            

            # Fetch pickup pincode from the Pickup model
            

            # Extract other details from the order_data
            delivery_pincode = order.get("customer_postal")
            # order_weight = 0.5  # Replace with the actual weight of the order if available
            cod = 0 if order.get("payment_type_name", "").lower() == "prepaid" else 1
            # result = self.check_serviceability(
            # pickup_pincode= pickup_pincode,
            # delivery_pincode=delivery_pincode,
            # weight=1.0,
            # cod=cod
            # )
            try:
                response = self.Quick_ship(_request_json)
                UpdateInstance = Order_Table.objects.filter(company=company_id, id=order['id'])
                print(response, "-----------------------------871",UpdateInstance)
                response_data1 = response
                if not response or not isinstance(response, dict):
                    _ResponsesDict.append({"order": f"{order['id']}", "message": "Empty or invalid response from API"})
                    continue
                
                # Instead of checking 'success' and 'data', check 'status'
                if not response.get("tracking_number"):
                    UpdateInstance.update(
                        awb_response=response_data1, 
                        is_booked=1,
                        shipment_vendor = shipment_vendor
                    )
                    _ResponsesDict.append({"order": f"{order['id']}", "message": response.get("message", "Unknown error")})
                    continue

                # No need to extract 'data' separately, use response directly
                
                print("API Response Data:", response_data1)

                
                order_status, created = OrderStatus.objects.get_or_create(name='PICKUP PENDING')

                status_id = order_status.id
                UpdateInstance.update(
                    order_wayBill=response_data1.get('tracking_number', ''),
                    vendor_order_id=response_data1.get('tracking_number', ''),
                    awb_response=response_data1, 
                    is_booked=1,
                    order_status=status_id,
                    shipment_vendor = shipment_vendor
                )

                _ResponsesDict.append({"order": f"{order['id']}", "message": "Order IN PICKUP PENDING successfully"})
                
                _logJson = {
                    'order': order['id'],
                    'order_status': status_id,
                    'action_by': user_id,
                    'remark': 'Order IN PICKUP PENDING successfully',
                }
               
                # orderLogInsert(_logJson)
                orderLogInsert({
                                "order": order['id'],
                                "order_status": status_id,
                                "action_by": user_id,
                                "action": 'Order in PICKUP PENDING successfully',
                                "remark": 'Order in PICKUP PENDING successfully'
                            })
               
            except requests.exceptions.RequestException as e:
                _ResponsesDict.append({"order": f"{order['id']}", "message": str(e)})
                print(f"An error occurred for order {order['id']}:", e)
        # OrderLogModel
        return _ResponsesDict
    def login(self, email, password):
        data = {"email": email, "password": password}
        return self._post("/api-login", data)

    def add_warehouse(self, warehouse_data):
        return self._post("/api-warehouse-add", warehouse_data)

    def create_b2c_order(self, order_data):
        return self._post("/api-b2c-single-order", order_data)
     

    def Quick_ship(self,order_data):
        return self._post("/api-b2c-quick-shipment",order_data
                          )
    def create_b2b_order(self, order_data):
        return self._post("/api-create-b2b-order", order_data)
    
    def create_bulk_b2c_order(self, bulk_order_data):
        return self._post("/api-create-b2c-bulk-order", bulk_order_data)

    def b2c_quick_shipment(self, shipment_data):
        return self._post("/api-b2c-quick-shipment", shipment_data)

    def b2b_quick_shipment(self, shipment_data):
        return self._post("/api-b2b-quick-shipment", shipment_data)

    def bulk_b2c_quick_shipment(self, bulk_shipment_data):
        return self._post("/api-bulk-b2c-quick-shipment", bulk_shipment_data)

    def ship_order(self, order_data):
        return self._post("/api-ship-order", order_data)

    def delete_order(self, order_id):
        return self._post(f"/api-delete-order/{order_id}")

    def logistic_price(self, logistic_data):
        return self._post("/api-logistic-price/209785", logistic_data)

    def calculate_price(self, pricing_data):
        return self._post("/api-calculate-price", pricing_data)

    def track_order(self, tracking_id):
        return self._get(f"/api-tracking-details/{tracking_id}")
    

    



import requests
from django.http import JsonResponse
from django.views import View
from django.conf import settings
class NimbuspostAPI:
    BASE_URL = "https://api.nimbuspost.com/v1"
    def __init__(self, email: str, password: str):
        """
        Initializes the TekipostService class with automatic token generation.
        """
        self.email = email
        self.password = password
        self.token = self._get_token()
        
        if not self.token:
            raise Exception("Failed to authenticate with TEKIPOST API.")
        
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.token}"
        }

    def _get_token(self) -> str:
        """
        Private method to get the TEKIPOST token during initialization.
        """
       
        try:
            url = f"{self.BASE_URL}/users/login"
            headers = {"content-type": "application/json"}
            payload =  {"email": self.email, "password": self.password}

            print(payload,"=------------------997")
            response = requests.post(url, json=payload, headers=headers)
            token = response.json()
            print(token.get('data'))
            print(token,"----------------1000")
            if not token.get('data'):
                logger.error("Token not found in the response.")
            return token.get('data')
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching token: {e}")
            return None
        
    @staticmethod
    def makeJsonForApi(order_data: dict,channel_id,pickup) -> bool:
        """
        Static method to validate order data before scheduling.
        :param order_data: Dictionary containing order details.
        :return: True if valid, False otherwise.
        """
        print(order_data,"-----------------------70")
        _itemsList = []
        product_height =0
        prouduct_length = 0
        product_weight = 0
        product_width = 0
        product_hsn = ''
        if order_data['order_details']:
            for _item in order_data['order_details']:
                request = get_request()
                user = request.user
                print(user,_item)
                data = getProduct(user.id, _item["product"])
                serializer = ProductSerializer(data, many=True)
                product_data = serializer.data[0]
                print(product_data,"----------222")
                prouduct_length = product_data.get('product_size') if prouduct_length < product_data.get('product_size') else prouduct_length
                product_height = product_data.get('product_height') if product_height < product_data.get('product_height') else product_height
                product_weight = product_data.get('product_weight')+product_weight
                product_width = product_data.get('product_width') if product_width < product_data.get('product_width') else product_width
                product_hsn = product_data.get('product_hsn_number')
                _itemDict = { 
                    "name": _item["product_name"],
                    "sku": _item["product_sku"],
                    "selling_price": _item["product_price"],
                    "qty": _item["product_qty"],
                }
                _itemsList.append(_itemDict)
        if isinstance(order_data['customer_state'], dict):
            state_name = order_data['customer_state'].get('name', 'Unknown')
        elif isinstance(order_data['customer_state'], int):
            try:
                state_obj = Customer_State.objects.filter(id=order_data['customer_state']).first()
                state_name = state_obj.name if state_obj else 'Unknown'
            except Exception:
                state_name = 'Unknown'
        else:
            state_name = 'Unknown'
        _RequestJson = {
                    "order_number": f"{order_data['order_id']}",
                    "payment_type": "prepaid" if order_data['payment_type_name'] == "Prepaid Payment" else "cod",
                    "order_amount": float(f"{order_data['cod_amount']}") if float(f"{order_data['cod_amount']}")>0 else float(f"{order_data['prepaid_amount']}"),
                    "package_weight": int(float(product_weight)*1000),
                    "package_length": prouduct_length,
                    "package_breadth": product_width,
                    "package_height": product_height,                
                    "consignee": {
                        "name": f"{order_data['customer_name']}",
                        "address": f"{order_data['customer_address']}",
                        "address_2": f"{order_data['customer_address']}",
                        "city": f"{order_data['customer_city']}",
                        "state": f"{state_name}",
                        "pincode": f"{order_data['customer_postal']}",
                        "phone": f"{order_data['customer_phone'][-10:]}"
                    },
                    "pickup": {
                        "warehouse_name": pickup.get('pickup_location_name'),
                        "name" : pickup.get('contact_person_name'),
                        "address": pickup.get('complete_address'),
                        "address_2": pickup.get('complete_address'),
                        "city": pickup.get('city'),
                        "state": pickup.get('state'),
                        "pincode":pickup.get('pincode'),
                        "phone": pickup.get('contact_number')[-10:]
                    },
                    "order_items": _itemsList
                }
        return  _RequestJson

    def schedule_order(self, order_list:list, branch_id:int ,company_id:int,channel_id,user_id,pickup_id,shipment_vendor):
        """
        Public method to schedule an order using the Shiprocket API.

        :param order_data: Dictionary containing order details.
        :return: Response from the Shiprocket API.
        """
        OrdersData = Order_Table.objects.filter(company=company_id,id__in=order_list)
        OrdersDataSerializer = OrderTableSerializer(OrdersData, many=True)
        
        _OrderLogJson=[]
        _ResponsesDict=[]
        for order in OrdersDataSerializer.data:
            pickup_point_id = pickup_id
            if not pickup_point_id:
                return {"status": "error", "message": "Pickup point not provided in order data."}
            try:
                pickup = PickUpPoint.objects.get(id=pickup_point_id)
                pickup_data = PickUpPointSerializer(pickup)
                pickup = pickup_data.data
                pickup_pincode = pickup.get("pincode")
                pickup_location = pickup.get("contact_person_name") # Adjust field name if different
            except PickUpPoint.DoesNotExist:
                return {"status": "error", "message": f"Pickup point with ID {pickup_point_id} does not exist."}
            _request_json = self.makeJsonForApi(order, channel_id,pickup)
            # api_endpoint = self.create_specific_order if channel_id else self.create_custom_order     
            # Extract other details from the order_data
            delivery_pincode = order.get("customer_postal")
            # order_weight = 0.5  # Replace with the actual weight of the order if available
            cod = 0 if order.get("payment_type_name", "").lower() == "prepaid" else 1
            # result = self.check_serviceability(
            # pickup_pincode= pickup_pincode,
            # delivery_pincode=delivery_pincode,
            # weight=1.0,
            # cod=cod
            # )
            try:
                response = self.create_shipment(_request_json)
                # response = requests.post(api_endpoint, headers=self.headers, json=_request_json)
                # Process response
                print(response,"------------------1148")
                if response.get('status'):
                    response_data1 = response
                    response_data = response.get('data')
                    try:
                        UpdateInstance = Order_Table.objects.filter( company=company_id, id=order['id'])
                        order_status, created = OrderStatus.objects.get_or_create(
                            name='PICKUP PENDING'
                            # branch=branch_id,
                            # company=company_id
                        )
                        print(order_status,"------------------order_status")
                        # order_status, created = OrderStatus.objects.get_or_create(name='IN TRANSIT')
                        status_id = order_status.id
                        print(status_id,"-----------------------")
                        res = UpdateInstance.update(
                            order_wayBill=response_data.get('awb_number', ''),
                            order_ship_by=response_data.get('courier_name', ''),
                            # assigned_date_time=awb_data.get('assigned_date_time', {}).get('date', {}),
                            # freight_charges=awb_data.get('freight_charges', None),
                            awb_response=response_data1, 
                            # estimated_delivery_date=result.get('estimated_delivery_date', None),
                            shipment_id =response_data.get('shipment_id', ''), 
                            vendor_order_id=response_data.get('order_id', ''),
                            is_booked=1,
                            order_status = status_id,
                            shipment_vendor = shipment_vendor
                        )
                        print(res,"------------------res")
                        from django.forms.models import model_to_dict
                        updated_order = Order_Table.objects.get(id=order['id'])
                        updated_order.refresh_from_db()
                        print(model_to_dict(updated_order), "------------------updated order")
                        _ResponsesDict.append({"order": f"{order['id']}", "message": "Order Pickup request successfully"})
                        # Log the action
                        _logJson = {
                            'order': order['id'],
                            'order_status': status_id,
                            'action_by': user_id,  # Assuming you have access to the current user
                            'remark': 'Order Pickup request successfully',
                        }
                        # orderLogInsert(_logJson)
                        
                        orderLogInsert({
                                "order": order['id'],
                                "order_status": status_id,
                                "action_by": user_id,
                                "action": 'Order in PICKUP PENDING successfully',
                                "remark": 'Order in PICKUP PENDING successfully'
                            })
                        
                       
                        _OrderLogJson.append(_logJson)
                        print("AWB Response:", response_data1)
                    except requests.exceptions.RequestException as e:
                        _ResponsesDict.append({"order": f"{order['id']}", "message": str(e)})
                        print("Error fetching AWB:", e)
                    
                else:
                    _ResponsesDict.append({"order": f"{order['id']}", "message": response})
                    print(f"Request failed for order {order['id']}: {response}")
            
            except requests.exceptions.RequestException as e:
                _ResponsesDict.append({"order": f"{order['id']}", "message": str(e)})
                print(f"An error occurred for order {order['id']}:", e)
        # OrderLogModel
        return _ResponsesDict
    def track_single_shipment(self, awb_number):
        if not self.token:
            return {"status": False, "message": "Unauthorized: Please login first."}

        url = f"{self.BASE_URL}/shipments/track/{awb_number}"
        headers = {"Authorization": f"Bearer {self.token}"}

        response = requests.get(url, headers=headers)
        return response.json()

    def track_bulk_shipments(self, awb_numbers):
        if not self.token:
            return {"status": False, "message": "Unauthorized: Please login first."}

        url = f"{self.BASE_URL}/shipments/track/bulk"
        headers = {
            "content-type": "application/json",
            "Authorization": f"Bearer {self.token}"
        }
        payload = {"awb": awb_numbers}

        response = requests.post(url, json=payload, headers=headers)
        return response.json()

    def create_shipment(self, shipment_data):
        print(shipment_data,"-----------------123")
        if not self.token:
            return {"status": False, "message": "Unauthorized: Please login first."}

        url = f"{self.BASE_URL}/shipments"
        print("Token:", self.token)

        headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": f"Token {self.token}"  # Try changing Bearer to Token
             }

        response = requests.post(url, json=shipment_data, headers=headers)
        return response.json()

    def cancel_shipment(self, awb_number):
        if not self.token:
            return {"status": False, "message": "Unauthorized: Please login first."}

        url = f"{self.BASE_URL}/shipments/cancel/{awb_number}"
        headers = {"Authorization": f"Bearer {self.token}"}

        response = requests.post(url, headers=headers)
        return response.json()

    def get_ndr_list(self, awb_number, page_no=1, per_page=50):
        if not self.token:
            return {"status": False, "message": "Unauthorized: Please login first."}

        url = f"{self.BASE_URL}/ndr?awb_number={awb_number}&page_no={page_no}&per_page={per_page}"
        headers = {"Authorization": f"Bearer {self.token}"}

        response = requests.get(url, headers=headers)
        return response.json()

    def submit_ndr_action(self, actions):
        """
        Submit NDR actions to Nimbuspost.

        :param actions: list of action objects per Nimbuspost docs
        :return: tuple (body, status_code)
        """
        if not self.token:
            # return consistent tuple with 401 status
            return {"status": False, "message": "Unauthorized: Please login first."}, 401

        url = f"{self.BASE_URL}/ndr/action"
        headers = {
            "content-type": "application/json",
            "Authorization": f"Bearer {self.token}"
        }

        try:
            response = requests.post(url, json=actions, headers=headers, timeout=30)
        except requests.RequestException as exc:
            logger.exception("Nimbuspost submit_ndr_action request failed: %s", exc)
            return {"status": False, "message": f"Request error: {str(exc)}"}, 502

        # Try to parse JSON body; fall back to text if invalid JSON
        try:
            body = response.json()
        except ValueError:
            body = {"message": response.text or "No response body"}

        return body, response.status_code


# class NimbuspostView(View):
#     def post(self, request, *args, **kwargs):
#         action = request.POST.get("action")
#         email = request.POST.get("email")
#         password = request.POST.get("password")
#         awb_number = request.POST.get("awb_number")
#         bulk_awb_numbers = request.POST.getlist("bulk_awb_numbers")
#         shipment_data = request.POST.get("shipment_data")
#         ndr_actions = request.POST.get("ndr_actions")

#         api = NimbuspostAPI()

#         if action == "login":
#             return JsonResponse(api.login(email, password))
#         elif action == "track_single":
#             return JsonResponse(api.track_single_shipment(awb_number))
#         elif action == "track_bulk":
#             return JsonResponse(api.track_bulk_shipments(bulk_awb_numbers))
#         elif action == "create_shipment":
#             return JsonResponse(api.create_shipment(shipment_data))
#         elif action == "cancel_shipment":
#             return JsonResponse(api.cancel_shipment(awb_number))
#         elif action == "get_ndr_list":
#             return JsonResponse(api.get_ndr_list(awb_number))
#         elif action == "submit_ndr_action":
#             return JsonResponse(api.submit_ndr_action(ndr_actions))
#         else:
#             return JsonResponse({"status": False, "message": "Invalid action."})


class ZoopshipService:
    BASE_URL = "https://api.zoopship.com"
    LOGIN_URL = "/api/login-users/"
    CREATE_ORDER_URL = "/api/order-create/"
    TRACK_ORDER_URL = "/api/track-orders/track_by_waybill/"
    CANCEL_ORDER_URL = "/api/orders-cancel/"
    CREATE_sHIP_ORDER_URL = "/api/order-create/"
    def __init__(self, username: str, password: str):
        """
        Initialize ZoopshipService and auto-fetch token.
        """
        self.username = username
        self.password = password
        print("-------------------1325")
        self.token = self._get_token()

        if not self.token:
            raise Exception("Failed to authenticate with Zoopship API.")

        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"token {self.token}"
        }

    def _get_token(self) -> str:
        """
        Authenticate and retrieve Zoopship API token.
        """
        data = {"username": self.username, "password": self.password}
        try:
            response = requests.post(f"{self.BASE_URL}{self.LOGIN_URL}", json=data)
            response.raise_for_status()
            print(response.json(), "----- LOGIN RESPONSE -----")
            token = response.json().get("data").get("token")
            if not token:
                logger.error("Token not found in response.")
            return token
        except requests.exceptions.RequestException as e:
            logger.error(f"Token fetch error: {e}")
            return None

    def _post(self, endpoint, data=None):
        """
        Generic POST method with error handling.
        """
        url = f"{self.BASE_URL}{endpoint}"
        try:
            response = requests.post(url, headers=self.headers, json=data)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"POST failed: {url} - {e}")
            return {"error": str(e)}

    def _get(self, endpoint, params=None):
        """
        Generic GET method with error handling.
        """
        url = f"{self.BASE_URL}{endpoint}"
        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"GET failed: {url} - {e}")
            return {"error": str(e)}

    def create_order(self, order_data: dict):
        """
        Create a new order on Zoopship.
        """
        print(order_data, "----- Creating Order -----")
        return self._post(self.CREATE_sHIP_ORDER_URL, data=order_data)
    

    def track_order(self, tracking_number: str):
        """
        Track an existing order by waybill number.
        """
        payload = {"tracking_number": tracking_number}
        return self._get(self.TRACK_ORDER_URL, params=payload)

    def cancel_order(self, order_ids: list, reason="Cancelled"):
        """
        Cancel orders by order IDs.
        """
        payload = {
            "order_ids": order_ids,
            "order_status_title": reason
        }
        return self._post(self.CANCEL_ORDER_URL, data=payload)
    @staticmethod
    def makeJsonForApi(order_data: dict, channel_id=None, pickup=None) -> dict:
        """
        Prepare the JSON payload for Zoopship order creation API.
        :param order_data: dict - Serialized order data with order_details
        :param channel_id: optional channel reference
        :param pickup: dict - Pickup point data (serialized)
        :return: dict - Prepared request JSON for Zoopship API
        """
        print(order_data, "----------------------- Building JSON for Zoopship")

        _itemsList = []
        product_height = 0
        product_length = 0
        product_weight = 0
        product_width = 0
        product_hsn = ""

        # ✅ Build product list and aggregate product metrics
        if order_data.get('order_details'):
            for _item in order_data['order_details']:
                try:
                    request = get_request()
                    user = request.user
                    data = getProduct(user.id, _item["product"])
                    serializer = ProductSerializer(data, many=True)
                    product_data = serializer.data[0]

                    product_length = max(product_length, product_data.get('product_size', 0))
                    product_height = max(product_height, product_data.get('product_height', 0))
                    product_width = max(product_width, product_data.get('product_width', 0))
                    product_weight += product_data.get('product_weight', 0)
                    product_hsn = product_data.get('product_hsn_number', '')

                    _itemsList.append({
                        "product_name": _item.get("product_name"),
                        "product_sku": _item.get("product_sku"),
                        "product_value": _item.get("product_price"),
                        "product_quantity": _item.get("product_qty"),
                    })
                except Exception as e:
                    print(f"Error building product item: {_item} — {e}")

        # ✅ Get customer state name
        try:
            state = Customer_State.objects.get(id=order_data.get('customer_state'))
            state_name = state.name
        except Customer_State.DoesNotExist:
            print("State not found for order:", order_data.get("order_id"))
            state_name = ""

        # ✅ Build final order JSON for Zoopship API
        _RequestJson = {
            "network_ip": order_data.get("network_ip", "127.0.0.1"),
            "customer_name": order_data.get("customer_name"),
            "customer_phone": order_data.get("customer_phone"),
            "customer_address": order_data.get("customer_address"),
            "customer_postal": order_data.get("customer_postal"),
            "customer_city": order_data.get("customer_city"),
            "customer_state": state_name,
            "customer_country": order_data.get("customer_country", "India"),
            "total_amount": float(order_data.get("total_amount", 0)),
            "gross_amount": float(order_data.get("gross_amount", 0)),
            "discount": float(order_data.get("discount", 0)),
            "prepaid_amount": float(order_data.get("prepaid_amount", 0)),
            "order_remark": order_data.get("order_remark", ""),
            "repeat_order": int(order_data.get("repeat_order", 0)),
            "is_booked": int(order_data.get("is_booked", 0)),
            "payment_type": "prepaid" if order_data['payment_type_name'] == "Prepaid Payment" else "cod",
            "payment_status": order_data.get("payment_status"),
            "order_status": order_data.get("order_status"),
            "order_created_by": order_data.get("order_created_by"),
            "product_details": _itemsList
        }

        # ✅ Optional pickup data (if available)
        if pickup:
            _RequestJson.update({
                "pickup_contact_person": pickup.get("contact_person_name"),
                "pickup_contact_number": pickup.get("contact_number"),
                "pickup_address": pickup.get("complete_address"),
                "pickup_pincode": pickup.get("pincode"),
                "pickup_city": pickup.get("city"),
                "pickup_state": pickup.get("state"),
                "pickup_email": pickup.get("contact_email"),
            })

        print(_RequestJson, "----------------------- Final Zoopship Payload")
        return _RequestJson

    @staticmethod
    def extract_order_info(resp):
    # If main success is False → return False
        if not resp.get("success"):
            return {"success": False, "order_id": order_id, "awb_number": None}

        updated_orders = resp.get("data", {}).get("updated_orders", [])
        if not updated_orders:
            return {"success": False, "order_id": order_id, "awb_number": None}

        order = updated_orders[0]  # first order
        order_id = order.get("order_id")

        # Get AWB number from nested object
        shipping_data = order.get("shipping", {}).get("data", [])
        if not shipping_data:
            return {"success": True, "order_id": order_id, "awb_number": None}

        raw_response = shipping_data[0].get("raw_response", {})
        awb_number = raw_response.get("data", {}).get("awb_number")

        return {
            "success": True,
            "order_id": order_id,
            "awb_number": awb_number
        }


        
    def schedule_order_zoopshipservice(
    self, order_list: list, branch_id: int, company_id: int, 
    channel_id, user_id, pickup_id, shipment_vendor
):
        """
        Schedule orders using Zoopship service.
        """

        OrdersData = Order_Table.objects.filter(company=company_id, id__in=order_list)
        OrdersDataSerializer = OrderTableSerializer(OrdersData, many=True)
        _OrderLogJson = []
        _ResponsesDict = []

        for order in OrdersDataSerializer.data:
            pickup_point_id = pickup_id
            if not pickup_point_id:
                return {"status": "error", "message": "Pickup point not provided in order data."}

            # --- Fetch Pickup Point Details ---
            try:
                pickup = PickUpPoint.objects.get(id=pickup_point_id)
                pickup_data = PickUpPointSerializer(pickup)
                pickup = pickup_data.data
                print(pickup, "-------------------Zoopship Pickup-------------------", shipment_vendor)

            except PickUpPoint.DoesNotExist:
                return {"status": "error", "message": f"Pickup point with ID {pickup_point_id} does not exist."}

            print(order, "---------------Zoopship Order---------------")

            # --- Prepare Request JSON for API ---
            _request_json = self.makeJsonForApi(order)
            print(_request_json, "------------------Zoopship JSON------------------")

            # --- Extract Details for Logging / Validation ---
            delivery_pincode = order.get("customer_postal")
            cod = 0 if order.get("payment_type_name", "").lower() == "prepaid" else 1

            try:
                # --- Call Zoopship API Instead of QuickShip ---
                response = self.create_order(_request_json)
                response_data1 = self.extract_order_info(response)
                UpdateInstance = Order_Table.objects.filter(branch=branch_id, company=company_id, id=order['id'])

                # response_data1 = response
                if not response_data1 or not response_data1.get('success'):
                    UpdateInstance.update(
                        awb_response=response,
                    )
                    _ResponsesDict.append({"order": f"{order['id']}", "message": "Empty or invalid response from API"})
                    continue

                if not response_data1.get("awb_number"):
                    UpdateInstance.update(
                        awb_response=response_data1,
                        is_booked=1,
                        shipment_vendor=shipment_vendor
                    )
                    _ResponsesDict.append({"order": f"{order['id']}", "message": response.get("message", "Unknown error")})
                    continue

                # --- Update Order Status ---
                order_status, created = OrderStatus.objects.get_or_create(name='IN TRANSIT')
                status_id = order_status.id
                UpdateInstance.update(
                    order_wayBill=response_data1.get('awb_number', ''),
                    vendor_order_id=response_data1.get('order_id', ''),
                    awb_response=response_data1,
                    is_booked=1,
                    order_status=status_id,
                    shipment_vendor=shipment_vendor
                )

                _ResponsesDict.append({"order": f"{order['id']}", "message": "Order IN PICKUP PENDING successfully"})

                # --- Insert Order Log ---
                orderLogInsert({
                    "order": order['id'],
                    "order_status": status_id,
                    "action_by": user_id,
                    "action": 'Order in PICKUP PENDING successfully',
                    "remark": 'Order in PICKUP PENDING successfully'
                })

            except requests.exceptions.RequestException as e:
                _ResponsesDict.append({"order": f"{order['id']}", "message": str(e)})
                print(f"An error occurred for order {order['id']} (Zoopship):", e)

        return _ResponsesDict








class EshopboxAPI:
    AUTH_URL = "https://auth.myeshopbox.com/api/v1/generateToken"
    ORDER_URL = "https://wms.eshopbox.com/api/order"
    SHIPMENT_URL = "https://wms.eshopbox.com/api/v1/shipping/order"
    RATE_URL = "https://{domain}/shipping/api/v1/calculate/rate"

    def __init__(self, client_id, client_secret, refresh_token):
        self.client_id = client_id
        self.client_secret = client_secret
        self.refresh_token = refresh_token
        self.token = self._get_token()

        if not self.token:
            raise Exception("Eshopbox Authentication Failed")

        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }

    # ---------------- AUTH ---------------- #

    def _get_token(self):
        payload = {
            "grant_type": "refresh_token",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": self.refresh_token
        }
        try:
            res = requests.post(self.AUTH_URL, json=payload, timeout=20)
            print(res.json(), "-----------------Eshopbox Token Response-------------------")
            data = res.json()
            return data.get("access_token")
        except Exception as e:
            logger.error(f"Eshopbox token error: {e}")
            return None

    # ---------------- MAPPER ---------------- #

    @staticmethod
    def makeJsonForApi(order_data, pickup, channel_id=None):
        items = []
        total_weight = 0
        max_l = max_b = max_h = 0
        formatted_date = eshopbox_date(order_data["created_at"])

        for item in order_data["order_details"]:
            weight = float(item.get("product_weight") or 1)
            length = float(item.get("product_length") or 1)
            breadth = float(item.get("product_breadth") or 1)
            height = float(item.get("product_height") or 1)

            total_weight += weight
            max_l = max(max_l, length)
            max_b = max(max_b, breadth)
            max_h = max(max_h, height)

            items.append({
                "itemID": str(item.get("product_sku") or "SKU001"),
                "productTitle": item.get("product_name") or "Product",
                "quantity": int(item.get("product_qty") or 1),
                "itemTotal": float(item.get("product_price") or 0),
                "hsn": str(item.get("product_hsn_number") or "0000"),
                "mrp": float(item.get("product_mrp") or 0),
                "discount": float(item.get("product_discount") or 0),
                "taxPercentage": float(item.get("product_tax") or 0),
                "itemLength": length,
                "itemBreadth": breadth,
                "itemHeight": height,
                "itemWeight": weight,
                "ean": str(item.get("ean") or "0"),
                "productImageUrl": item.get("image") or ""
            })

        payload = {
            "channelId": channel_id or "CREWORDER",
            "customerOrderId": str(order_data["order_id"]),
            "shipmentId": str(order_data["id"]),
            "orderDate": formatted_date,
            "isCOD": order_data.get("payment_type_name") != "Prepaid Payment",
            "invoiceTotal": float(order_data.get("total_amount") or 0),
            "shippingMode": "Eshopbox Standard",
            "balanceDue": float(order_data.get("cod_amount") or 0),

            "invoice": {
                "number": str(order_data["order_id"]),
                "date": formatted_date
            },

            "shippingAddress": {
                "customerName": order_data.get("customer_name") or "Customer",
                "addressLine1": order_data.get("customer_address") or "NA",
                "city": order_data.get("customer_city") or "NA",
                "state": order_data.get("customer_state_name") or "NA",
                "pincode": str(order_data.get("customer_postal") or "000000"),
                "country": "India",
                "contactPhone": order_data.get("customer_phone") or "9999999999",
                "email": order_data.get("customer_email") or "",
                "gstin": order_data.get("gstin") or ""
            },

            "billingIsShipping": True,
            "billingAddress": {
                "customerName": order_data.get("customer_name") or "Customer",
                "addressLine1": order_data.get("customer_address") or "NA",
                "city": order_data.get("customer_city") or "NA",
                "state": order_data.get("customer_state_name") or "NA",
                "pincode": str(order_data.get("customer_postal") or "000000"),
                "country": "India",
                "contactPhone": order_data.get("customer_phone") or "9999999999",
                "email": order_data.get("customer_email") or ""
            },

            "items": items,

            "shipmentDimension": {
                "length": max(max_l, 1),
                "breadth": max(max_b, 1),
                "height": max(max_h, 1),
                "weight": max(total_weight, 0.5)
            },

            "pickupLocation": {
                "locationCode": str(pickup.get("id") or "LOC001"),
                "locationName": pickup.get("pickup_location_name") or "Warehouse",
                "companyName": pickup.get("company") or "COMPANY",
                "contactPerson": pickup.get("contact_person_name") or "Manager",
                "contactNumber": pickup.get("contact_number") or "9999999999",
                "addressLine1": pickup.get("complete_address") or "NA",
                "addressLine2": pickup.get("address_2") or "",
                "city": pickup.get("city") or "NA",
                "state": pickup.get("state") or "NA",
                "country": "India",
                "pincode": str(pickup.get("pincode") or "000000")
            },

            "package": {
                "type": "box",
                "code": "1",   # will be overwritten
                "description": "Creworder Shipment",
                "length": max(max_l, 1),
                "breadth": max(max_b, 1),
                "height": max(max_h, 1),
                "weight": max(total_weight*1000, 0.5)
            }
        }

        return sanitize_for_eshopbox(payload)

    # def makeJsonForApi(order_data, pickup, channel_id=None):
    #     items = []
    #     total_weight = 0
    #     max_l = max_b = max_h = 0
    #     formatted_date = eshopbox_date(order_data["created_at"])

    #     for item in order_data["order_details"]:
    #         weight = float(item.get("product_weight", 200))
    #         length = float(item.get("product_length", 10))
    #         breadth = float(item.get("product_breadth", 10))
    #         height = float(item.get("product_height", 10))

    #         total_weight += weight
    #         max_l = max(max_l, length)
    #         max_b = max(max_b, breadth)
    #         max_h = max(max_h, height)

    #         items.append({
    #             "itemID": item["product_sku"],
    #             "productTitle": item["product_name"],
    #             "quantity": item["product_qty"],
    #             "itemTotal": item["product_price"],
    #             "hsn": str(item.get("product_hsn_number", "0000")),
    #             "mrp": item.get("product_mrp", 0),
    #             "discount": item.get("product_discount", 0),
    #             "taxPercentage": item.get("product_tax", 0),
    #             "itemLength": length,
    #             "itemBreadth": breadth,
    #             "itemHeight": height,
    #             "itemWeight": weight,
    #             "ean": item.get("ean", "0"),
    #             "productImageUrl": item.get("image", "")
    #         })

    #     payload = {
    #         "channelId": channel_id if channel_id else "CREWORDER",
    #         "customerOrderId": order_data["order_id"],
    #         "shipmentId": order_data["id"],
    #         "orderDate": formatted_date,
    #         "isCOD": True if order_data["payment_type_name"] != "Prepaid Payment" else False,
    #         "invoiceTotal": order_data["total_amount"],
    #         "shippingMode": "Eshopbox Standard",
    #         "balanceDue": order_data["cod_amount"],

    #         "invoice": {
    #             "number": order_data["order_id"],
    #             "date": formatted_date
    #         },

    #         "shippingAddress": {
    #             "customerName": order_data["customer_name"],
    #             "addressLine1": order_data["customer_address"],
    #             "city": order_data["customer_city"],
    #             "state": order_data["customer_state_name"],
    #             "pincode": str(order_data["customer_postal"]),
    #             "country": "India",
    #             "contactPhone": order_data["customer_phone"],
    #             "email": order_data["customer_email"],
    #             "gstin": order_data.get("gstin", "")
    #         },

    #         "billingIsShipping": True,
    #         "billingAddress": {
    #             "customerName": order_data["customer_name"],
    #             "addressLine1": order_data["customer_address"],
    #             "city": order_data["customer_city"],
    #             "state": order_data["customer_state_name"],
    #             "pincode": str(order_data["customer_postal"]),
    #             "country": "India",
    #             "contactPhone": order_data["customer_phone"],
    #             "email": order_data["customer_email"]
    #         },

    #         "items": items,

    #         # ONLY HERE dimensions are allowed
    #         # "shipmentDimension": {
    #         #     "length": str(max_l),
    #         #     "breadth": str(max_b),
    #         #     "height": str(max_h),
    #         #     "weight": str(total_weight)
    #         # },
    #         "shipmentLength": str(max_l),
    #         "shipmentBreadth": str(max_b),
    #         "shipmentHeight": str(max_h),
    #         "shipmentWeight": str(total_weight),

    #         "pickupLocation": {
    #             "locationCode": pickup["id"],
    #             "locationName": pickup["pickup_location_name"],
    #             "companyName": pickup["company"],
    #             "contactPerson": pickup["contact_person_name"],
    #             "contactNumber": pickup["contact_number"],
    #             "addressLine1": pickup["complete_address"],
    #             "addressLine2": pickup.get("address_2", ""),
    #             "city": pickup["city"],
    #             "state": pickup["state"],
    #             "country": "India",
    #             "pincode": str(pickup["pincode"]),
    #             #"gstin": pickup.get("gstin", "")
    #         },

    #         "package": {
    #             "type": "box",
    #             "code": f"PKG-{order_data['id']}",
    #             "description": "Creworder Shipment",
    #             "length": max_l,
    #             "breadth": max_b,
    #             "height": max_h,
    #             "weight": total_weight
    #         },

    #         # Always safe to send (even empty)
    #         #"ewaybillNumber": "0"
    #     }

    #     return payload

    # ---------------- CREATE ORDER ---------------- #

    def schedule_order(self, order_list, company_id, user_id, pickup_id, shipment_vendor,channel_id):
        print(channel_id, "-----------------eschopbox channel_id-------------------")
        OrdersData = Order_Table.objects.filter(company=company_id, id__in=order_list)
        OrdersDataSerializer = OrderTableSerializer(OrdersData, many=True)

        responses = []

        pickup = PickUpPoint.objects.get(id=pickup_id)
        pickup_data = PickUpPointSerializer(pickup).data

        for order in OrdersDataSerializer.data:
            try:
                print("-----------------eschopbox order-------------------", order,pickup_data)
                print(self.SHIPMENT_URL, "-----------------eschopbox SHIPMENT_URL-------------------")
                payload = self.makeJsonForApi(order, pickup_data,channel_id)
                print(payload,"-----------------eschopbox payload-------------------")
                res = requests.post(self.SHIPMENT_URL, json=payload, headers=self.headers)
                print(res,"-----------------eschopbox response-------------------")
                print(res.json(),"-----------------eschopbox response json-------------------")
                data = res.json()
      

                if res.status_code == 200:
                    order_status, _ = OrderStatus.objects.get_or_create(name="PICKUP PENDING")

                    Order_Table.objects.filter(id=order["id"]).update(
                        order_wayBill=data.get("trackingId"),
                        courier_name=data.get("courierName"),
                        awb_response=data,
                        shipment_id=data.get("id"),
                        vendor_order_id=data.get("trackingId"),
                        is_booked=1,
                        order_status=order_status.id,
                        shipment_vendor=shipment_vendor
                    )

                    orderLogInsert({
                        "order": order["id"],
                        "order_status": order_status.id,
                        "action_by": user_id,
                        "action": "Order sent to Eshopbox",
                        "remark": "Shipment created successfully"
                    })

                    responses.append({"order": order["id"], "message": "Success"})

                else:
                    responses.append({"order": order["id"], "message": data})

            except Exception as e:
                responses.append({"order": order["id"], "message": str(e)})

        return responses

    # ---------------- TRACK ---------------- #

    def track_shipment(self, tracking_id):
        url = f"https://wms.eshopbox.com/api/shipment/{tracking_id}"
        res = requests.get(url, headers=self.headers)
        return res.json()

    # ---------------- RATE CALCULATOR ---------------- #

    def calculate_rate(self, domain, pickup_pin, drop_pin, weight, length, width, height, payment_method, cod_amount):
        url = self.RATE_URL.format(domain=domain)
        payload = {
            "journeyType": "forward",
            "pickupPincode": pickup_pin,
            "dropPincode": drop_pin,
            "orderWeight": weight,
            "length": length,
            "width": width,
            "height": height,
            "paymentMethod": payment_method,
            "codAmountToBeCollected": cod_amount,
            "doorstepQc": False
        }
        res = requests.post(url, json=payload, headers=self.headers)
        return res.json()
    
    def track_bulk_shipments(self, tracking_ids: list):
        """
        tracking_ids = ["1223", "44567"]
        """
        ids = ",".join(tracking_ids)
        url = f"https://wms.eshopbox.com/api/v1/shipping/trackingDetails?trackingIds={ids}"

        res = requests.get(url, headers=self.headers, timeout=30)
        return res.json()
    
    def cancel_shipment(self, tracking_id):
        url = "https://wms.eshopbox.com/api/v1/shipping/cancel"
        payload = {"trackingId": tracking_id}

        res = requests.post(url, json=payload, headers=self.headers, timeout=30)
        return res.json()
    def create_return_shipment(self, order_data, pickup):
        """
        Creates reverse pickup (return shipment) in Eshopbox
        order_data = serialized Order_Table
        pickup = customer pickup (address where courier will collect return)
        """

        items = []
        total_weight = 0
        max_l = max_b = max_h = 0

        for item in order_data["order_details"]:
            weight = float(item.get("weight", 100))
            length = float(item.get("length", 10))
            breadth = float(item.get("width", 10))
            height = float(item.get("height", 10))

            total_weight += weight
            max_l = max(max_l, length)
            max_b = max(max_b, breadth)
            max_h = max(max_h, height)

            items.append({
                "itemID": item["product_sku"],     # SKU
                "productTitle": item["product_name"],
                "quantity": item["product_qty"],
                "itemTotal": item["product_price"],
                "hsn": item.get("product_hsn", ""),
                "mrp": item.get("product_mrp", 0),
                "discount": item.get("product_discount", 0),
                "taxPercentage": item.get("product_tax", 0),
                "returnReason": item.get("return_reason", "Customer Return"),
                "ean": item.get("ean", ""),
                "length": length,
                "breadth": breadth,
                "height": height,
                "weight": weight,
                "qcDetails": item.get("qcDetails", {})
            })
        print(total_weight, "-----------------Total Weight-------------------",total_weight*1000)
        payload = {
            "channelId": "CREWORDER",
            "customerOrderId": order_data["order_id"],
            "shipmentId": f"RTN-{order_data['id']}",
            "orderDate": order_data["created_at"],
            "isCOD": True if order_data["payment_type_name"] != "Prepaid Payment" else False,
            "invoiceTotal": order_data["total_amount"],
            "shippingMode": "Standard",

            "invoice": {
                "number": order_data["order_id"],
                "date": order_data["created_at"]
            },

            # Where courier will DELIVER return (your warehouse)
            "shippingAddress": {
                "locationCode": pickup["id"],
                "locationName": pickup["pickup_location_name"],
                "companyName": pickup["company_name"],
                "contactPerson": pickup["contact_person_name"],
                "contactNumber": pickup["contact_number"],
                "addressLine1": pickup["complete_address"],
                "addressLine2": pickup.get("address_2", ""),
                "city": pickup["city"],
                "state": pickup["state"],
                "pincode": pickup["pincode"],
                "country": "India",
                "gstin": pickup.get("gstin", "")
            },

            "items": items,

            "returnDimension": {
                "length": max_l,
                "breadth": max_b,
                "height": max_h,
                "weight": total_weight*1000  # in grams
            },

            # Where courier will PICKUP return (customer)
            "pickupLocation": {
                "customerName": order_data["customer_name"],
                "addressLine1": order_data["customer_address"],
                "city": order_data["customer_city"],
                "state": order_data["customer_state_name"],
                "pincode": order_data["customer_postal"],
                "country": "India",
                "contactPhone": order_data["customer_phone"],
                "email": order_data["customer_email"]
            }
        }

        url = "https://wms.eshopbox.com/api/v1/shipping/return"
        res = requests.post(url, json=payload, headers=self.headers, timeout=30)
        return res.json()
