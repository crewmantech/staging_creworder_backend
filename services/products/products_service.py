import os
import string
import random
from orders.models import Products
from accounts.models import Employees
from orders.serializers import ProductSerializer
from django.core.exceptions import ObjectDoesNotExist
from accounts.serializers import UserProfileSerializer


def createProduct(data, userid):
    productid = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
    "PR" + str(productid)
    userData = Employees.objects.filter(user_id=userid).first()
    serializer = UserProfileSerializer(userData)
    serialized_data = serializer.data
    data["branch"] = serialized_data["branch"]
    data["company"] = serialized_data["company"]
    data["user"] = userid
    data["product_id"] = "PR" + str(productid)
    serializer = ProductSerializer(data=data)
    if serializer.is_valid():
        savedata = serializer.save()
        return savedata
    else:
        raise ValueError(serializer.errors)


def updateProduct(id, data):
    try:
        updatedData = Products.objects.get(id=id)
        serializer = ProductSerializer(updatedData, data=data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return serializer.instance
        else:
            raise ValueError(serializer.errors)
    except ObjectDoesNotExist:
        return None


def deleteProduct(id):
    try:
        data = Products.objects.get(id=id)
        data.delete()
        return True
    except ObjectDoesNotExist:
        return False


def getProduct(user_id, id=None):
    try:
        tableData = ""
        if user_id is not None:
            userData = Employees.objects.filter(user_id=user_id).first()
            serializer = UserProfileSerializer(userData)
            serialized_data = serializer.data
            if id:
                tableData = Products.objects.filter(
                    branch=serialized_data["branch"],
                    company=serialized_data["company"],
                    id=id,
                )
            else:
                tableData = Products.objects.filter(
                    branch=serialized_data["branch"], company=serialized_data["company"]
                )
        return tableData
    except ObjectDoesNotExist:
        return False
    except Exception as e:
        print(f"Error in getProduct: {str(e)}")  # Log error for debugging
        return False
