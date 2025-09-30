from django.shortcuts import render
from .serializers import APISandboxSerializer, EmailCredentialsSerializer, MenuSerializer, SMSCredentialsSerializer,SubMenuSerializer,SettingMenuSerializer,PixelCodeModelSerializer,BannerModelSerializer, SuperAdminCompanySerializer,ThemeSettingSerializer
from rest_framework.views import APIView
from rest_framework import viewsets, status
from .models import EmailCredentials, SMSCredentials, SandboxCredentials, MenuModel,SubMenusModel,SettingsMenu,PixelCodeModel,BennerModel, SuperAdminCompany,ThemeSettingModel
from django.db.models import Q
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny, DjangoObjectPermissions

class MenuViewSet(viewsets.ModelViewSet):
    queryset = MenuModel.objects.all()
    serializer_class = MenuSerializer
    pagination_class = None 


class SubMenuViewSet(viewsets.ModelViewSet):
    queryset = SubMenusModel.objects.all()
    serializer_class = SubMenuSerializer
    pagination_class = None

from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.decorators import action
from django.db.models import Q
from rest_framework.exceptions import PermissionDenied

class SettingMenuViewSet(viewsets.ModelViewSet):
    queryset = SettingsMenu.objects.all()
    serializer_class = SettingMenuSerializer
    pagination_class = None

    def get_queryset(self):
        user_type = self.request.user.profile.user_type

        if user_type == 'superadmin':
            return SettingsMenu.objects.filter(Q(for_user='superadmin') | Q(for_user='both'), status=1)

        all_menus = SettingsMenu.objects.filter(
            Q(for_user=user_type) | Q(for_user='both'),
            status=1
        )

        menu_ids = []
        for menu in all_menus:
            menu_name_key = menu.name.replace(' ', '_').lower()
            menu_permission = f"superadmin_assets.show_settingsmenu_{menu_name_key}"
            if self.request.user.has_perm(menu_permission):
                menu_ids.append(menu.id)

        return SettingsMenu.objects.filter(id__in=menu_ids)

    def get_object(self):
        obj = SettingsMenu.objects.get(pk=self.kwargs['pk'])  # Unfiltered lookup
        user_type = self.request.user.profile.user_type

        if user_type == 'superadmin':
            return obj

        # For others, check access
        menu_name_key = obj.name.replace(' ', '_').lower()
        menu_permission = f"superadmin_assets.show_settingsmenu_{menu_name_key}"

        if (
            obj.status == 1 and
            (obj.for_user == user_type or obj.for_user == 'both') and
            self.request.user.has_perm(menu_permission)
        ):
            return obj

        raise PermissionDenied("You do not have permission to view this menu.")

    @action(detail=False, methods=['get'])
    def all_menus(self, request):
        """Returns all menu items regardless of user type or status."""
        all_menus = SettingsMenu.objects.all()
        serializer = self.get_serializer(all_menus, many=True)
        return Response(serializer.data)


class PixelCodeView(viewsets.ModelViewSet):
    queryset = PixelCodeModel.objects.all()
    serializer_class = PixelCodeModelSerializer
    pagination_class = None

class BannerView(viewsets.ModelViewSet):
    serializer_class = BannerModelSerializer
    pagination_class = None

    def get_queryset(self):
        user = self.request.user
        # Check if user has a profile and user_type attribute
        if hasattr(user, "profile") and hasattr(user.profile, "user_type"):
            user_type = user.profile.user_type
            if user_type in ["agent", "admin"]:
                queryset = BennerModel.objects.filter(for_user__in=[user_type, "both"])
                return queryset

        return BennerModel.objects.all() 

class ThemeSetting(viewsets.ModelViewSet):
    queryset = ThemeSettingModel.objects.all()
    serializer_class = ThemeSettingSerializer
    pagination_class = None


class APISandboxViewSet(viewsets.ModelViewSet):
    queryset = SandboxCredentials.objects.all()
    serializer_class = APISandboxSerializer


class SMSCredentialsViewSet(viewsets.ModelViewSet):
    queryset = SMSCredentials.objects.all()
    serializer_class = SMSCredentialsSerializer


class SuperAdminCompanyViewSet(viewsets.ModelViewSet):
    queryset = SuperAdminCompany.objects.all()
    serializer_class = SuperAdminCompanySerializer
    permission_classes = [IsAuthenticated]


class EmailCredentialsViewSet(viewsets.ModelViewSet):
    queryset = EmailCredentials.objects.all()
    serializer_class = EmailCredentialsSerializer