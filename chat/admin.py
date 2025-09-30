from django.contrib import admin
from .models import Chat,ChatSession,GroupDetails,Group

admin.site.register(Chat)
admin.site.register(ChatSession)
admin.site.register(Group)
admin.site.register(GroupDetails)
# Register your models here.
