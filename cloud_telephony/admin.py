from django.contrib import admin

# Register your models here.
from .models import CloudTelephonyChannel,CloudTelephonyChannelAssign,UserMailSetup,CloudTelephonyVendor
admin.site.register(CloudTelephonyVendor)
admin.site.register(CloudTelephonyChannel)
admin.site.register(CloudTelephonyChannelAssign)
admin.site.register(UserMailSetup)
