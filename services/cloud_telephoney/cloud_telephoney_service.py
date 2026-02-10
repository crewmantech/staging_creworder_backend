# import os
# from cloud_telephony.models import CloudTelephonyChannel, CloudTelephonyChannelAssign
# from cloud_telephony.serializers import (
#     CloudTelephonyChannelSerializer,
#     CloudTelephonyChannelAssignSerializer,
# )
# from django.core.exceptions import ObjectDoesNotExist
# from accounts.models import Employees
# from accounts.serializers import UserProfileSerializer
# import pdb


# def createCloudTelephoneyChannel(data, userid):
#     userData = Employees.objects.filter(user_id=userid).first()
#     serializer = UserProfileSerializer(userData)
#     serialized_data = serializer.data
#     mutable_data = data.copy()
#     mutable_data['branch'] = serialized_data["branch"]
#     mutable_data['company'] = serialized_data["company"]
#     mutable_data['user'] = userid
#     serializer = CloudTelephonyChannelSerializer(data=mutable_data)
#     if serializer.is_valid():
#         cloud_telephony_channel = serializer.save()
#         return cloud_telephony_channel
#     else:
#         raise ValueError(serializer.errors)


# def deleteCloudTelephoneyChannel(id):
#     try:
#         createdData = CloudTelephonyChannel.objects.get(id=id)
#         createdData.delete()
#         return True
#     except ObjectDoesNotExist:
#         return False


# def updateCloudTelephoneyChannel(id, data):
#     try:
#         updatedData = CloudTelephonyChannel.objects.get(id=id)
#         serializer = CloudTelephonyChannelSerializer(
#             updatedData, data=data, partial=True
#         )
#         if serializer.is_valid():
#             serializer.save()
#             return serializer.instance
#         else:
#             raise ValueError(serializer.errors)
#     except ObjectDoesNotExist:
#         return None


# def getCloudTelephoneyChannel(id=None):
#     CloudTelephonyChannelData = ""
#     if id is not None:
#         userData = Employees.objects.filter(user_id=id).first()
#         serializer = UserProfileSerializer(userData)
#         serialized_data = serializer.data
#         CloudTelephonyChannelData = CloudTelephonyChannel.objects.filter(
#             branch=serialized_data["branch"], company=serialized_data["company"]
#         )

#     return CloudTelephonyChannelData


# def createCloudTelephoneyChannelAssign(data, userid):
#     userData = Employees.objects.filter(user_id=userid).first()
#     if not userData:
#         raise ValueError("User not found")
#     serializer = UserProfileSerializer(userData)
#     serialized_data = serializer.data
#     data["branch"] = serialized_data["branch"]
#     data["company"] = serialized_data["company"]
#     data["user"] = userid
#     assignTableData = CloudTelephonyChannelAssign.objects.filter(
#         cloud_telephony_channel_table=data["cloud_telephony_channel_table"],
#         priority=data["priority"],
#     ).first()
#     if assignTableData:
#         return "Please change the priority for adding this channel, as this priority already exists."
#     serializer1 = CloudTelephonyChannelAssignSerializer(data=data)
#     if serializer1.is_valid():
#         cloud_telephony_channel = serializer1.save()
#         return cloud_telephony_channel
#     else:
#         raise ValueError(serializer.errors)

# def updateCloudTelephoneyChannelAssign(id, data):
#     try:
#         updatedData = CloudTelephonyChannelAssign.objects.get(id=id)
#         serializer = CloudTelephonyChannelAssignSerializer(
#             updatedData, data=data, partial=True
#         )
#         if serializer.is_valid():
#             serializer.save()
#             return serializer.instance
#         else:
#             raise ValueError(serializer.errors)
#     except ObjectDoesNotExist:
#         return None
    

# def deleteCloudTelephoneyChannelAssign(id):
#     try:
#         createdData = CloudTelephonyChannelAssign.objects.get(id=id)
#         createdData.delete()
#         return True
#     except ObjectDoesNotExist:
#         return False

from rest_framework.exceptions import ValidationError
import requests
import hashlib
from typing import Optional
from datetime import datetime, date

from cloud_telephony.models import CloudTelephonyChannelAssign
class CloudConnectService:
    BASE_URL = "https://crm5.cloud-connect.in/CCC_api/v1.4"

    def __init__(self, token: str, tenant_id: str):
        self.token = token
        self.tenant_id = tenant_id

    # =========================
    # INTERNAL REQUEST HANDLER
    # =========================
    def _post_request(self, endpoint: str, data: dict):
        url = f"{self.BASE_URL}/{endpoint}"
        headers = {"Content-Type": "application/json"}
        print("    ↳ SENDING REQUEST TO =", url)
        print("    ↳ PAYLOAD =", data)
        print("    ↳ HEADERS =", headers)
        response = requests.post(
            url,
            json=data,
            headers=headers,
            timeout=10
        )
        print(response.status_code, response.text, "-----------------response from cloudconnect------------------")
        try:
            result = response.json()
        except Exception:
            raise Exception("Invalid response from CloudConnect")

        # CloudConnect returns code as int or string
        if result.get("code") not in (200, "200"):
            raise Exception(result.get("status_message", "CloudConnect API Error"))

        return result

    # =========================
    # REAL-TIME SESSION (WEB)
    # =========================
    def create_session(self, agent_id: str,agent_username:str,agent_password:str,camp_id:str,other:str,campangin_name:str):
        """
        REQUIRED for WebRTC / iFrame based real-time calling
        """
        # data = {
        #     "agent_id": str(agent_id),
        #     "token": self.token,
        #     "tenant_id": self.tenant_id
        # } 
        data = {
            "agent_username": agent_username,
            "agent_password": agent_password,
            "loginType": "AUTO",
            "campaign_name": camp_id,
            "token": self.token,
            # "queue_id": camp_id,
            "tenant_id": self.tenant_id
        }
        print("    ↳ FINAL PAYLOAD =", data)

        return self._post_request("createSession", data)

    # (Optional / Legacy)
    def get_session_id(self, agent_id: str):
        """
        Legacy API (keep only if already used)
        """
        data = {
            "agent_id": str(agent_id),
            "token": self.token,
            "tenant_id": self.tenant_id
        }
        return self._post_request("getSessionId", data)

    # =========================
    # CALL ORIGINATION
    # =========================

    # ❌ Legacy (Not for WebRTC)
    def originate_call(self, agent_username, agent_password, customer_phone, campaign_name):
        """
        Legacy panel-based calling (NOT recommended for Next.js portal)
        """
        data = {
            "action": "Call",
            "agent_username": agent_username,
            "agent_password": hashlib.md5(agent_password.encode()).hexdigest(),
            "customer_phone": customer_phone,
            "campaign_name": campaign_name,
            "token": self.token,
            "tenant_id": self.tenant_id
        }
        return self._post_request("clickToCall", data)

    # ✅ MAIN REAL-TIME CALL METHOD
    def manual_call_originate(
        self,
        agent_id: str,
        agent_session_id: str,
        customer_phone: str,
        camp_id: str
    ):
        """
        REAL-TIME CALL (Browser → Customer)
        Requires active session + iframe
        """
        data = {
            "action": "Call",
            "agent_id": str(agent_id),
            "agent_session_id": str(agent_session_id),
            "customer_phone": str(customer_phone),
            "camp_id": str(camp_id),
            "tenant_id": self.tenant_id
        }
        return self._post_request("clickToCallManual", data)

    # =========================
    # CALL CONTROL
    # =========================
    def hangup_call(self, ref_id: str):
        data = {
            "action": "Hangup",
            "ref_id": ref_id,
            "token": self.token,
            "tenant_id": self.tenant_id
        }
        return self._post_request("clickToCall", data)

    # =========================
    # CALL LOGS & DETAILS
    # =========================
    def get_call_details(self, date, phone_number):
        if phone_number:
            data = {
                "date": date,
                "phone_number": phone_number,
                # "agent_id": agent_id,
                # "session_id": session_id,
                "token": self.token,
                "tenant_id": self.tenant_id
            }
        else:
            data = {
            "date": date,
            # "agent_id": agent_id,
            # "session_id": session_id,
            "token": self.token,
            "tenant_id": self.tenant_id
        }
        print(data,"-----------------178")
        return self._post_request("getCallHistory", data)

    def get_call_history(self, start_datetime, end_datetime):
        data = {
            "search_type": "DATETIME",
            "start_datetime": start_datetime,
            "end_datetime": end_datetime,
            "token": self.token,
            "tenant_id": self.tenant_id
        }
        return self._post_request("getCallHistory", data)

    def get_recording_details(self, call_id: str):
        data = {
            "call_id": call_id,
            "token": self.token,
            "tenant_id": self.tenant_id
        }
        return self._post_request("getRecording", data)

    # =========================
    # AUTO DIALER (JOB APIs)
    # =========================
    def insert_job_number(self, job_id, numbers, agent_id=None):
        data = {
            "job_id": job_id,
            "numbers": numbers,
            "token": self.token,
            "tenant_id": self.tenant_id
        }
        if agent_id:
            data["agent_id"] = agent_id
        return self._post_request("addJobNumber", data)

    def update_job_number(self, job_id, numbers, agent_id=None):
        data = {
            "job_id": job_id,
            "numbers": numbers,
            "token": self.token,
            "tenant_id": self.tenant_id
        }
        if agent_id:
            data["agent_id"] = agent_id
        return self._post_request("updateJobNumber", data)

    def delete_job_number(self, job_id, numbers):
        data = {
            "job_id": job_id,
            "numbers": numbers,
            "delete_type": "DELETESPECIFIC",
            "token": self.token,
            "tenant_id": self.tenant_id
        }
        return self._post_request("deleteJobNumber", data)

    # === Session & Callback ===

    # def get_session_id(self, agent_id):
    #     data = {
    #         "agent_id": agent_id,
    #         "token": self.token,
    #         "tenant_id": self.tenant_id
    #     }
    #     return self._post_request("getSessionId", data)

    def callback_subscribe(self, session_id):
        data = {
            "sessionid": session_id,
            "token": self.token,
            "tenant_id": self.tenant_id
        }
        return self._post_request("callbackSubscribe", data)

    def callback_unsubscribe(self, session_id):
        data = {
            "sessionid": session_id,
            "token": self.token,
            "tenant_id": self.tenant_id
        }
        return self._post_request("callbackUnSubscribe", data)
    
    def call_details(self,call_id):
        data={
            "call_id": call_id,
            "allow_customer_info": "true",
            "token": self.token,
            "tenant_id": self.tenant_id
        }
        return self._post_request("getCallDetails", data)
    
    def agent_current_status(self, agent_id=None, agent_uname=None, queue_id=None, status=None):
        data = {
            "token": self.token,
            "tenant_id": self.tenant_id
            
        }
        if agent_id:
            data["agent_id"] = str(agent_id)
        if agent_uname:
            data["agent_uname"] = agent_uname
        if queue_id:
            data["queue_id"] = queue_id
        if status:
            data["status"] = status

        return self._post_request("getAgentCurrentStatus", data)

    
    def create_caller_id_routing(self, customer_numbers, agent_id, did_id="ANY"):
        """
        Maps customer number(s) to a dedicated agent (Inbound routing)
        """
        if isinstance(customer_numbers, str):
            customer_numbers = [customer_numbers]

        data = {
            "token": self.token,
            "tenant_id": self.tenant_id,
            "cr_number": customer_numbers,
            "did_id": did_id,
            "cr_action_type": "AGENT",
            "cr_action_id": str(agent_id)
        }

        return self._post_request("createCallerIdRouting", data)
    def update_caller_id_routing(
    self,
    cr_id,
    customer_number,
    agent_id,
    did_id="ANY"
):
        data = {
            "cr_id": str(cr_id),
            "token": self.token,
            "tenant_id": self.tenant_id,
            "cr_number": customer_number,
            "did_id": did_id,
            "cr_action_type": "AGENT",
            "cr_action_id": str(agent_id)
        }

        return self._post_request("updateCallerIdRouting", data)
    def get_active_Call(self):
        
        data = {
           
                "token": self.token,
                "tenant_id": self.tenant_id
            }
        
        return self._post_request("getActiveCall", data)
    

    # def getAgentCurrentStatus(self,agent_id):
    #     data = {
    #         "agent_id": str(agent_id),
    #         "token": self.token,
    #         "tenant_id": self.tenant_id
    #     }
    #     return self._post_request("getAgentCurrentStatus", data)
class TataSmartfloService:
    BASE_URL = "https://api-smartflo.tatateleservices.com/v1"

    def __init__(self, api_key):
        self.headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }

    def initiate_click_to_call(self, agent_number, destination_number, caller_id, async_mode=1, call_timeout=None, custom_identifier=None, get_call_id=1):
        """
        Initiate Click-to-Call Request
        """
        url = f"{self.BASE_URL}/click_to_call"
        payload = {
            "agent_number": agent_number,
            "destination_number": destination_number,
            "caller_id": caller_id,
            "async": async_mode,
            "get_call_id": get_call_id
        }

        # Optional Parameters
        if call_timeout:
            payload["call_timeout"] = call_timeout
        if custom_identifier:
            payload["custom_identifier"] = custom_identifier

        try:
            response = requests.post(url, headers=self.headers, json=payload)
            response_data = response.json()

            if response.status_code == 200 and response_data.get("success"):
                return {"success": True, "data": response_data}
            else:
                return {"success": False, "error": response_data.get("message", "Unknown error occurred")}

        except requests.exceptions.RequestException as e:
            return {"success": False, "error": str(e)}
        
    def get_call_records(self, params):
        """
        Fetch call detail records with specified parameters.
        """
        url = f"{self.BASE_URL}/call/records"
        try:
            response = requests.get(url, headers=self.headers, params=params)
            response_data = response.json()

            if response.status_code == 200 and response_data.get("results"):
                return {"success": True, "data": response_data}
            else:
                return {"success": False, "error": response_data.get("message", "Unknown error occurred")}

        except requests.exceptions.RequestException as e:
            return {"success": False, "error": str(e)}

    def get_active_calls(self, agent_number,extension,did_number,call_id):
        """
        Fetch details of active calls with specified parameters.
        """
        params={
            "agent_number":agent_number,
            "extension":extension,
            "did_number":did_number,
            "call_id":call_id
        }
        url = f"{self.BASE_URL}/live_calls"
        try:
            response = requests.get(url, headers=self.headers, params=params)
            response_data = response.json()

            if response.status_code == 200:
                return {"success": True, "data": response_data}
            else:
                return {"success": False, "error": response_data.get("message", "Unknown error occurred")}

        except requests.exceptions.RequestException as e:
            return {"success": False, "error": str(e)}
        
    def get_all_recordings(self):
        """
        Fetch list of all recordings.
        """
        url = f"{self.BASE_URL}/recordings"
        try:
            response = requests.get(url, headers=self.headers)
            response_data = response.json()

            if response.status_code == 200:
                return {"success": True, "data": response_data}
            else:
                return {"success": False, "error": response_data.get("message", "Unknown error occurred")}

        except requests.exceptions.RequestException as e:
            return {"success": False, "error": str(e)}
        
        
class SansSoftwareService:
    BASE_URL = "https://bsl.sansoftwares.com"

    def __init__(self, process_id: str):
        """
        process_id is the 'process_id' you are sending in all Sanssoftwares API requests (e.g. '74').
        """
        self.process_id = process_id

    def _post_request(self, endpoint: str, data: dict):
        """
        Internal helper to make POST requests to Sanssoftwares.
        `endpoint` should be a relative path like 'api/getNumber'.
        """
        url = f"{self.BASE_URL}/{endpoint.lstrip('/')}"
        headers = {"Content-Type": "application/json"}
        response = requests.post(url, json=data, headers=headers)
        print(response.text,"----------542")
        # You can add error handling/logging here if needed
        return response.json()

    # ========== API Wrappers ==========

    def get_number(self, lead_id: str, process_id: Optional[str] = None):

        final_process_id = process_id or self.process_id
        print(final_process_id,"-----------self.process_id")
        data = {
            "Lead_ID": lead_id,
            "process_id": final_process_id,
        }

        return self._post_request("api/getNumber", data)

    def get_all_call_log_detail(
    self,
    phone_number: str,
    start_date_str,
    to_date_str,
    process_id: Optional[str] = None
):
   

        # ---- normalize start date ----
        if isinstance(start_date_str, date):
            start_date = start_date_str
        else:
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()

        # ---- normalize end date ----
        if isinstance(to_date_str, date):
            end_date = to_date_str
        else:
            end_date = datetime.strptime(to_date_str, "%Y-%m-%d").date()

        from_date = f"{start_date} 00:00:00"
        to_date = f"{end_date} 23:59:59"
        if phone_number:

            data = {
                "Phone_number": phone_number,
                "process_id": process_id or self.process_id,
                "from_date": from_date,
                "to_date": to_date,
            }
        else:
            data = {
                "process_id": process_id or self.process_id,
                "from_date": from_date,
                "to_date": to_date,
            }
        print(data, "-----------342")

        return self._post_request("api/getAllCallLogDetail", data)

    def get_lead_recording(self, phone_number: str, start_date_str: str,to_date_str: str, process_id: Optional[str] = None):
        """
        Fetch lead recording for a single date.
        Converts 'YYYY-MM-DD' → full-day time range.
        """
        # Parse incoming date
        selected_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        selected_date = datetime.strptime(to_date_str, "%Y-%m-%d").date()
        from_date = f"{selected_date} 00:00:00"
        to_date = f"{selected_date} 23:59:59"

        data = {
            "Phone_number": phone_number,
            "process_id": process_id or self.process_id,
            "from_date": from_date,
            "to_date": to_date,
        }

        return self._post_request("api/getLeadrecording", data)

    def click_to_call(self, agent_name: str, dialed_number: str):
        """
        Wraps:
            POST https://bsl.sansoftwares.com/caller/Api/ClicktoCallDial
            Body: { "agent_name": "...", "dialed_number": "..." }
        """
        data = {
            "agent_name": agent_name,
            "dialed_number": dialed_number,
        }
        print(data,"-------------------436")
        res = self._post_request("caller/Api/ClicktoCallDial", data)
        print(res,"-----------self._post_request")
        return res
    
    
def get_phone_number_by_call_id(user, call_id):
    if not call_id:
        raise ValidationError("call_id is required.")

    try:
        channel_assign = CloudTelephonyChannelAssign.objects.get(user_id=user.id,is_active=True)
        channel = channel_assign.cloud_telephony_channel
    except CloudTelephonyChannelAssign.DoesNotExist:
        raise ValidationError("No channel assigned to this user.")

    cloud_vendor = channel.cloudtelephony_vendor.name.lower()
    print(cloud_vendor,"-----------------cloudvendor")
    # -------- CLOUD CONNECT --------
    if cloud_vendor == "cloud connect":
        if not channel.token or not channel.tenent_id:
            raise ValidationError("token and tenant_id required for CloudConnect.")

        service = CloudConnectService(channel.token, channel.tenent_id)
        response = service.call_details(call_id)

        if response.get("code") != 200:
            raise ValidationError({
                "vendor": "cloud_connect",
                "vendor_code": response.get("code"),
                "vendor_message": response.get("status_message", "Unknown error")
            })

        # ✅ phone_number ONLY here
        return response["result"]["phone_number"]

    # -------- SANSSOFTWARES --------
    elif cloud_vendor == "sansoftwares":
        process_id = channel.tenent_id
        if not process_id:
            raise ValidationError("process_id required for Sanssoftwares.")

        service = SansSoftwareService(process_id=process_id)
        response = service.get_number(call_id)
        print(response,"-----------------sansoftwaresresponse")
        result = response.get("result", [])

        if not result or "Phone_number" not in result[0]:
            raise ValidationError({
                "vendor": "sansoftwares",
                "vendor_message": "Phone number not found in response"
            })

        return result[0]["Phone_number"]

    else:
        raise ValidationError(f"{cloud_vendor} is not supported.")
    
