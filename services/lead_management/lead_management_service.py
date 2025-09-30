from lead_management.models import LeadModel
from lead_management.serializers import LeadSerializer
from accounts.models import Employees
from accounts.serializers import UserProfileSerializer
from django.core.exceptions import ObjectDoesNotExist


def createLead(data,user_id):
    if isinstance(data, list):
        serializer = LeadSerializer(data=data, many=True)
    else:
        serializer = LeadSerializer(data=data)

    if serializer.is_valid():
        serializer.save()

        return serializer
    else:
        return serializer                        

def updateLead(id,data):
    try:
        updatedData = LeadModel.objects.get(id=id)
        serializer = LeadSerializer(updatedData, data=data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return serializer.instance
        else:
            raise ValueError(serializer.errors)
    except ObjectDoesNotExist:
        return None
    
def deleteLead(pk):
    try:
        data = LeadModel.objects.get(id=pk)
        data.delete()
        return True
    except ObjectDoesNotExist:
        return False

def getLead(user_id,pk):
    userData = Employees.objects.filter(user_id=user_id).first()
    serializer = UserProfileSerializer(userData)
    serialized_data = serializer.data
    if pk is not None:
        leadTableData = LeadModel.objects.filter(
            branch=serialized_data["branch"], company=serialized_data["company"],id=pk
        )
    else:
        leadTableData = LeadModel.objects.filter(
            branch=serialized_data["branch"], company=serialized_data["company"]
        )
    return leadTableData