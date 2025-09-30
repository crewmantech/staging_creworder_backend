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

import requests
import hashlib
class CloudConnectService:
    BASE_URL = "https://crm5.cloud-connect.in/CCC_api/v1.4"

    def __init__(self, token, tenant_id):
        self.token = token
        self.tenant_id = tenant_id

    def _post_request(self, endpoint, data):
        url = f"{self.BASE_URL}/{endpoint}"
        headers = {"Content-Type": "application/json"}
        response = requests.post(url, json=data, headers=headers)
        return response.json()

    # === Call Functions ===

    def originate_call(self, agent_username, agent_password, customer_phone, campaign_name):
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

    def manual_call_originate(self, agent_id, agent_session_id, customer_phone, camp_id):
        data = {
            "action": "Call",
            "agent_id": agent_id,
            "agent_session_id": agent_session_id,
            "customer_phone": customer_phone,
            "camp_id": camp_id,
            "tenant_id": self.tenant_id
        }
        return self._post_request("clickToCallManual", data)

    def hangup_call(self, ref_id):
        data = {
            "action": "Hangup",
            "ref_id": ref_id,
            "token": self.token,
            "tenant_id": self.tenant_id
        }
        return self._post_request("clickToCall", data)

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

    def get_recording_details(self, call_id):
        data = {
            "call_id": call_id,
            "token": self.token,
            "tenant_id": self.tenant_id
        }
        print(data,"--------------------------cloudconect")
        return self._post_request("getRecording", data)

    # === Job Number Management ===

    def insert_job_number(self, job_id, numbers, agent_id=None):
        data = {
            "job_id": job_id,
            "numbers": numbers,
            "token": self.token,
            "tenant_id": self.tenant_id
        }
        if agent_id:
            data["agent_id"] = agent_id
        return self._post_request("insertJobNumber", data)

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
            "token": self.token,
            "tenant_id": self.tenant_id
        }
        return self._post_request("deleteJobNumber", data)

    # === Session & Callback ===

    def get_session_id(self, agent_id):
        data = {
            "agent_id": agent_id,
            "token": self.token,
            "tenant_id": self.tenant_id
        }
        return self._post_request("getSessionId", data)

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
    
    def agent_current_status(self):
        data={
            "token": self.token,
            "tenant_id": self.tenant_id
        }
        return self._post_request("getAgentCurrentStatus", data)
    
    

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