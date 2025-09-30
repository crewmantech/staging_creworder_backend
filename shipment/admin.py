from django.contrib import admin
from .models import ShipmentModel ,ShipmentVendor
from .models import CourierServiceModel
admin.site.register(CourierServiceModel)
admin.site.register(ShipmentModel)
admin.site.register(ShipmentVendor)

