from follow_up.models import Follow_Up
from follow_up.serializers import FollowUpSerializer
from django.core.exceptions import ObjectDoesNotExist


def createFollowUp(data):
    serializer = FollowUpSerializer(data=data)
    if serializer.is_valid():
        follow_up = serializer.save()
        return follow_up
    else:
        raise ValueError(serializer.errors)
    

def getFollowUpsbyuser(user_id=None):
    if user_id is not None:
        follow_ups = Follow_Up.objects.filter(follow_addedBy_id=user_id)
    else:
        follow_ups = Follow_Up.objects.all()
    return follow_ups

def deleteFollowUp(follow_up_id):
    try:
        follow_up = Follow_Up.objects.get(id=follow_up_id)
        follow_up.delete()
        return True
    except ObjectDoesNotExist:
        return False

def updateFollowUp(follow_up_id, data):
    try:
        follow_up = Follow_Up.objects.get(id=follow_up_id)
        serializer = FollowUpSerializer(follow_up, data=data, partial=True) 
        if serializer.is_valid():
            serializer.save()
            return serializer.instance
        else:
            raise ValueError(serializer.errors)
    except ObjectDoesNotExist:
        return None
