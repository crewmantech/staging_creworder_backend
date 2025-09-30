from django.contrib import admin
from django.contrib import admin
from .models import SubMenusModel,MenuModel,SettingsMenu,SandboxCredentials,SMSCredentials,EmailCredentials
admin.site.register(MenuModel)
admin.site.register(SubMenusModel)
admin.site.register(SettingsMenu)
admin.site.register(SandboxCredentials)
admin.site.register(SMSCredentials)
admin.site.register(EmailCredentials)