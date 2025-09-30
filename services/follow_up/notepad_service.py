
from follow_up.models import Notepad
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone
from datetime import timedelta
def createOrUpdateNotepad(auth_id, note):
    try:
        notepad = Notepad.objects.get(authID=auth_id)
        notepad.note = note
        notepad.save()
        return notepad, True
    except ObjectDoesNotExist:
        notepad = Notepad.objects.create(authID_id=auth_id, note=note)
        return notepad, False
    
def getNotepadByAuthid(auth_id):
    try:
        # time_threshold = timezone.now() - timedelta(hours=24)
        # notepad = Notepad.objects.filter(authID=auth_id,created_at__gte = time_threshold)
        return Notepad.objects.filter(authID=auth_id).first()
        return notepad
    except ObjectDoesNotExist:
        return None