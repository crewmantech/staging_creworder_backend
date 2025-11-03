from . import views
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import DealCategoryModelViewSet, LeadBulkUploadView, LeadSourceModelViewSet, LeadStatusModelViewSet, LeadViewSet, LeadformViewSet, LeadsViewSet, PipelineViewSet, UserCategoryAssignmentViewSet

router = DefaultRouter()
router.register(r'lead_sources', LeadSourceModelViewSet)
router.register(r'lead_status', LeadStatusModelViewSet)
router.register(r'deal-category', DealCategoryModelViewSet)
router.register(r'leads', LeadViewSet)
router.register(r'all-leads', LeadsViewSet, basename='all-leads')
router.register(r'user-category-assignments', UserCategoryAssignmentViewSet)
router.register(r'pipelines', PipelineViewSet)
router.register(r'lead-form', LeadformViewSet, basename='lead-form')
urlpatterns = [
    path('lead/', views.LeadCreateAPIView.as_view(), name='lead-list'),
    path('lead/<str:pk>', views.LeadCreateAPIView.as_view(), name='lead-lists'),
    path('lead/create/', views.LeadCreateAPIView.as_view(), name='lead-create'),
     path('lead/bulk-upload/', LeadBulkUploadView.as_view(), name='upload_bulk_leads'),
     path('lead-by-lead-id/', LeadDetailByLeadIDView.as_view(), name='lead-by-lead-id'),
    path('', include(router.urls)),
]