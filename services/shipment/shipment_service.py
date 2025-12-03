import json
import requests
from accounts.models import Employees
from shipment.models import ShipmentModel
from shipment.serializers import ShipmentSerializer
from django.core.exceptions import ObjectDoesNotExist
from accounts.serializers import UserProfileSerializer,PickUpPointSerializer
from accounts.models import PickUpPoint
import logging
from utils.custom_logger import setup_logging
import pdb
import sys
import traceback
import logging
logger = logging.getLogger(__name__)
setup_logging(log_file='logs/shipment_service.log', log_level=logging.WARNING)

def getShipRocketToken(email, password):
    try:
        url = "https://apiv2.shiprocket.in/v1/external/auth/login"
        payload = json.dumps({
            "email": email,
            "password": password
        })
        headers = {
            'Content-Type': 'application/json'
        }
        response = requests.post(url, headers=headers, data=payload)
        if response.status_code == 200:
            return response.json().get('token')
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching shiproket Token: {str(e)}")
        logger.error(traceback.format_exc())
        return None

    except Exception as e:
        logger.error(f"Error fetching shiproket Token: {str(e)}")
        logger.error(traceback.format_exc())
        return None

def createShipment(data, userid):
    userData = Employees.objects.filter(user_id=userid).first()
    serializer = UserProfileSerializer(userData)
    serialized_data = serializer.data
    mutable_data = data.copy()
    mutable_data["branch"] = serialized_data["branch"]
    mutable_data["company"] = serialized_data["company"]
    serializer = ShipmentSerializer(data=mutable_data)
    if serializer.is_valid():
        savedata = serializer.save()
        return savedata
    else:
        raise ValueError(serializer.errors)
    
def getShipment(user_id, id=None):
    try:
        tableData = ""
        if user_id is not None:
            userData = Employees.objects.filter(user_id=user_id).first()
            serializer = UserProfileSerializer(userData)
            serialized_data = serializer.data

            if id:
                tableData = ShipmentModel.objects.filter(
                    company=serialized_data["company"],
                    id=id,
                )
            else:
                tableData = ShipmentModel.objects.filter(
                    company=serialized_data["company"]
                )

        return tableData
    except ObjectDoesNotExist:
        return False
    

def deleteShipment(id):
    try:
        data = ShipmentModel.objects.get(id=id)
        data.delete()
        return True
    except ObjectDoesNotExist:
        return False

def updateShipment(id, data):
    try:
        updatedData = ShipmentModel.objects.get(id=id)
        serializer = ShipmentSerializer(updatedData, data=data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return serializer.instance
        else:
            raise ValueError(serializer.errors)
    except ObjectDoesNotExist:
        return None
    
def checkServiceability(branch_id,company_id,pincode):
    trackdata = ShipmentModel.objects.filter(branch=branch_id,company=company_id,status=1)
    pickUppointData = PickUpPoint.objects.filter(company=company_id,status=1)
    pickUpSerializerData = PickUpPointSerializer(pickUppointData, many=True)
    serializer = ShipmentSerializer(trackdata, many=True)
    serialized_data = serializer.data
    eddshortestTime=365
    EddList=[]
    for pickUpPinCode in pickUpSerializerData.data:
        EddDataShowDict={}
        for data in serialized_data:
            token=None
            EddDataShowDict['provider_name']=data['shipment_vendor']['name'].lower()
            EddDataShowDict['name']=data['name']
            EddDataShowDict['shipment_id']=data['id']
            EddDataShowDict['pickup_point']=pickUpPinCode['pincode']
            EddDataShowDict['pickup_city']=pickUpPinCode['city']
            EddDataShowDict['pickup_id']=pickUpPinCode['id']
            if data['shipment_vendor']['name'].lower() =='shiprocket':
                if data['credential_username']!='' or data['credential_username']!=None:
                    token=getShipRocketToken(data['credential_username'],data['credential_password'])
                url = "https://apiv2.shiprocket.in/v1/external/courier/serviceability/"
                payload = json.dumps({
                "pickup_postcode": f"{pickUpPinCode['pincode']}",
                "delivery_postcode": f"{pincode}",
                "weight": 0.5,
                "cod": 1
                })
                headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {token}'
                }
                response = requests.request("GET", url, headers=headers, data=payload)
                a=0
                shortestDayData={}
                if response.json()['status']==200:
                    for apiData in response.json()['data']['available_courier_companies']:
                        if int(eddshortestTime)>int(apiData['estimated_delivery_days']):
                            eddshortestTime=int(apiData['estimated_delivery_days'])
                            shortestDayData['courier_name']=apiData['courier_name']
                            shortestDayData['EDD']=apiData['estimated_delivery_days']
                    EddDataShowDict['eddtime']=eddshortestTime
                    EddList.append(EddDataShowDict)
                    eddshortestTime=365
            else:
                pass
    return EddList

