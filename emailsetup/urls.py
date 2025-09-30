from django.urls import include, path
from rest_framework.routers import DefaultRouter
from .views import AgentAuthenticationViewSet, EmailTemplateViewSet, SendEmailAPI,AgentReportViewSet

router = DefaultRouter()
router.register(r'emailtemplate', EmailTemplateViewSet, basename='emailtemplate')
router.register(r'agent-auth', AgentAuthenticationViewSet, basename='agent-auth')
router.register(r'agent-report', AgentReportViewSet, basename='agent-report')
urlpatterns = router.urls
urlpatterns = [
    path("", include(router.urls)),
    path('send-email/', SendEmailAPI.as_view(), name='send_email')

]