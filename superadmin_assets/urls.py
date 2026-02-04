from rest_framework.routers import DefaultRouter

# from accounts.views import SupportTicketViewSet
from .views import APISandboxViewSet,SupportTicketViewSet, EmailCredentialsViewSet, MenuViewSet, SMSCredentialsViewSet,SubMenuViewSet,SettingMenuViewSet,PixelCodeView,BannerView, SupportQuestionViewSet,ThemeSetting,SuperAdminCompanyViewSet,LanguageViewSet
from django.urls import path, include

router = DefaultRouter()
router.register(r'menu', MenuViewSet)
router.register(r'submenu', SubMenuViewSet)
router.register(r'setting_menu', SettingMenuViewSet, basename='settingmenu')
router.register(r'pixel-code',PixelCodeView,basename='pixel-code')
router.register(r'languages', LanguageViewSet, basename='languages')
router.register(r'banner',BannerView,basename='banner')
router.register(r'theme-setting',ThemeSetting,basename='theam-setting')
router.register(r'sandbox-credentials', APISandboxViewSet)
router.register(r'sms-credentials', SMSCredentialsViewSet)
router.register(r'superadmincompany', SuperAdminCompanyViewSet)  
router.register(r'email-credentials', EmailCredentialsViewSet)
router.register(r'support/questions', SupportQuestionViewSet, basename='support-questions')
router.register(r'support/tickets', SupportTicketViewSet, basename='support-tickets')
urlpatterns = [
    path('', include(router.urls)),
]

