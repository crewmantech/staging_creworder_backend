from django.contrib import admin
from .models import Chat,ChatSession,GroupDetails,Group,Notification

admin.site.register(Chat)
admin.site.register(ChatSession)
admin.site.register(Group)
admin.site.register(GroupDetails)
admin.site.register(Notification)
# Register your models here.
