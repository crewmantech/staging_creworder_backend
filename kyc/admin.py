from django.contrib import admin
from .models import KYC
from .models import GSTState
from .models import OTPModel


admin.site.register(KYC)
admin.site.register(GSTState)
admin.site.register(OTPModel)
