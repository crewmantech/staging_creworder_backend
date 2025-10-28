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
        OrdersData = Order_Table.objects.filter(branch=branch_id,company=company_id,id__in=order_list)
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

    def action_ndr(self, awb: str, action: str, comments: str = None):
        """
        Perform an action on an NDR shipment.

        :param awb: The AWB (Air Waybill) number of the shipment.
        :param action: The action to perform (e.g., "reschedule_delivery", "cancel", etc.).
        :param comments: Optional comments for the action.
        :return: Response from the API.
        """
        # Construct the URL with the AWB
        url = f"{self.NDR_ACTION_URL}/{awb}/action"

        # Prepare the payload
        payload = {
            "action": action,
            "comments": comments if comments else "",  # Include comments if provided
        }

        try:
            # Make the POST request
            response = requests.post(url, headers=self.headers, json=payload)
            # response.raise_for_status()  # Raise an error for bad status codes
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Error performing action on NDR shipment: {e}")
            return {"status": "error", "message": str(e)}
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

        OrdersData = Order_Table.objects.filter(branch=branch_id,company=company_id,id__in=order_list)
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
                UpdateInstance = Order_Table.objects.filter(branch=branch_id, company=company_id, id=order['id'])
                print(response, "-----------------------------871")
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
        OrdersData = Order_Table.objects.filter(branch=branch_id,company=company_id,id__in=order_list)
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
                if response.get('status'):
                    response_data1 = response
                    response_data = response.get('data')
                    try:
                        UpdateInstance = Order_Table.objects.filter(branch=branch_id, company=company_id, id=order['id'])
                        order_status, created = OrderStatus.objects.get_or_create(
                            name='PICKUP PENDING'
                            # branch=branch_id,
                            # company=company_id
                        )
                        # order_status, created = OrderStatus.objects.get_or_create(name='IN TRANSIT')
                        status_id = order_status.id
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
        if not self.token:
            return {"status": False, "message": "Unauthorized: Please login first."}

        url = f"{self.BASE_URL}/ndr/action"
        headers = {
            "content-type": "application/json",
            "Authorization": f"Bearer {self.token}"
        }

        response = requests.post(url, json=actions, headers=headers)
        return response.json()


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


