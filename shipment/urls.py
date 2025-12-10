from . import views
from django.urls import path, include
from rest_framework.views import APIView
from rest_framework.routers import DefaultRouter
from .views import CourierServiceView, OrderOperationsViewSet, NDRViewSet, OrderCancellationViewSet, PickupLocationViewSet,ScheduleOrders, ShipmentVendorViewSet, ShipmentViewSet,ShiprocketChannelViewSet,GeneratePickupAPI, TrackOrderAPI, TrackOrderViewSet, WalletBalanceAPI,NDRActionAPIView,NDRListAPIView,NDRDetailAPIView
router = DefaultRouter()
router.register(r'courier-service', CourierServiceView)
router.register(r'schedule-orders',ScheduleOrders)
router.register(r'shiprocket-channel', ShiprocketChannelViewSet, basename='unique-shiprocket-channel')
router.register(r'generate-pickup', GeneratePickupAPI, basename='generate-pickup')
router.register(r'cancel-order', OrderCancellationViewSet, basename='cancel-order')
router.register(r'shiprocket', TrackOrderViewSet, basename='shiprocket-trackorder')
router.register(r'manifests', OrderOperationsViewSet, basename='manifest')
router.register(r'shipments-details', ShipmentViewSet, basename='shipment-detills')
router.register(r'shipment-vendors', ShipmentVendorViewSet,basename='shipment-vendor')
urlpatterns = [
    path('', include(router.urls)),
    path("shipment-channel/", views.ShipmentView.as_view(), name="create-shipment"),
    path("shipment-channel/<int:pk>", views.ShipmentView.as_view(), name="details-shipment"),
    path('track-order/<str:pk>/', TrackOrderAPI.as_view({'get': 'retrieve'}), name='track-order'),
    path('wallet-balance/', WalletBalanceAPI.as_view({'get': 'list'}), name='wallet-balance'),
    path('ndr/', NDRViewSet.as_view({'get': 'list', 'post': 'create'}), name='ndr-list'),
    path('ndr/<str:pk>/', NDRViewSet.as_view({'get': 'retrieve'}), name='ndr-detail'),
    path('pickup/locations/', PickupLocationViewSet.as_view({'get': 'list'}), name='pickup-location-list'),
    path('pickup/location/', PickupLocationViewSet.as_view({'post': 'create'}), name='pickup-location-create'),
    path("ndr/action/", NDRActionAPIView.as_view(), name="ndr-action"),
    path("ndr/", NDRListAPIView.as_view(), name="ndr-list"),
    path("ndr/<str:awb>/", NDRDetailAPIView.as_view(), name="ndr-detail"),
]
