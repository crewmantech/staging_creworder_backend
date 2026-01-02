from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AssetTypeViewSet, AssetViewSet, AssetAssignmentViewSet, AssetLogViewSet

router = DefaultRouter()
router.register(r"asset-types", AssetTypeViewSet, basename="asset-types")
router.register(r"assets", AssetViewSet, basename="assets")
router.register(r"asset-assignments", AssetAssignmentViewSet, basename="asset-assignments")
router.register(r"asset-logs", AssetLogViewSet, basename="asset-logs")

urlpatterns = [
    path("", include(router.urls)),
]