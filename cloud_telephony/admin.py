from django.contrib import admin

# Register your models here.
from .models import CallLog, CloudTelephonyChannel,CloudTelephonyChannelAssign,UserMailSetup,CloudTelephonyVendor,CallActivity
admin.site.register(CloudTelephonyVendor)
admin.site.register(CloudTelephonyChannel)
admin.site.register(CloudTelephonyChannelAssign)
admin.site.register(UserMailSetup)
admin.site.register(CallLog)
admin.site.register(CallActivity)