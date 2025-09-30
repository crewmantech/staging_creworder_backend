from rest_framework import serializers
from .models import EmailCredentials, SMSCredentials, SandboxCredentials, MenuModel,SubMenusModel,SettingsMenu,PixelCodeModel,BennerModel,ThemeSettingModel,SuperAdminCompany
from phonenumber_field.serializerfields import PhoneNumberField
from rest_framework.serializers import ModelSerializer

class SubMenuSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubMenusModel
        fields = '__all__'


class MenuSerializer(serializers.ModelSerializer):
    sub_menu_list = serializers.SerializerMethodField()
    class Meta:
        model = MenuModel
        fields = '__all__'

    def get_sub_menu_list(self, menu):
        sub_menus = SubMenusModel.objects.filter(menu_id=menu.id)
        return SubMenuSerializer(sub_menus, many=True).data


class SettingMenuSerializer(serializers.ModelSerializer):
    class Meta:
        model = SettingsMenu
        fields = '__all__'

class PixelCodeModelSerializer(serializers.ModelSerializer):
    class Meta:
        model=PixelCodeModel
        fields='__all__'

class BannerModelSerializer(serializers.ModelSerializer):
    class Meta:
        model=BennerModel
        fields='__all__'

class ThemeSettingSerializer(serializers.ModelSerializer):
    class Meta:
        model=ThemeSettingModel
        fields='__all__'
        


class APISandboxSerializer(serializers.ModelSerializer):
    class Meta:
        model = SandboxCredentials
        fields = '__all__'


class SMSCredentialsSerializer(serializers.ModelSerializer):
    class Meta:
        model = SMSCredentials
        fields = '__all__'




class SuperAdminCompanySerializer(ModelSerializer):
    class Meta:
        model = SuperAdminCompany
        fields = '__all__'
        read_only_fields = ['id', 'company_id', 'created_at', 'updated_at']


class EmailCredentialsSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmailCredentials
        fields = '__all__'