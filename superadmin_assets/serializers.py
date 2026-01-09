from rest_framework import serializers

# from accounts.models import SupportTicket
from .models import EmailCredentials, SMSCredentials,SupportTickets, SandboxCredentials, MenuModel,SubMenusModel,SettingsMenu,PixelCodeModel,BennerModel, SupportQuestion,ThemeSettingModel,SuperAdminCompany
from phonenumber_field.serializerfields import PhoneNumberField
from rest_framework.serializers import ModelSerializer
from django.contrib.auth.models import User

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

class SupportQuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupportQuestion
        fields = [
            'id',            # 🔹 auto-generated DB id
            'question_id',   # 🔹 string id (QST-0001)
            'question',
            'priority',
            'is_active',
            'created_at'
        ]


class SupportTicketCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupportTickets
        fields = [
            'question',
            'description',
            'issue_image'
        ]

    def create(self, validated_data):
        request = self.context['request']
        return SupportTickets.objects.create(
            company=request.user.company,
            **validated_data
        )


class SupportTicketListSerializer(serializers.ModelSerializer):
    question = SupportQuestionSerializer(read_only=True)
    assigned_to = serializers.StringRelatedField()

    class Meta:
        model = SupportTickets
        fields = [
            'ticket_id',
            'question',
            'status',
            'assigned_to',
            'created_at'
        ]


class SupportTicketDetailSerializer(serializers.ModelSerializer):
    question = SupportQuestionSerializer(read_only=True)
    assigned_to = serializers.StringRelatedField()

    class Meta:
        model = SupportTickets
        fields = '__all__'


class AssignTicketSerializer(serializers.Serializer):
    assigned_to = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all()
    )


class TicketSolutionSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupportTickets
        fields = [
            'solution_description',
            'solution_image'
        ]

