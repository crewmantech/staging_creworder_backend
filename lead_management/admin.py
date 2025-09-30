from django.contrib import admin
from .models import LeadModel ,Lead,LeadSourceModel
admin.site.register(LeadModel)
admin.site.register(Lead)
admin.site.register(LeadSourceModel)