from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
router = DefaultRouter()
router.register(r'models', views.AllModelsViewSet, basename='models')
router.register(r'manage-permisson', views.PermissionSetupViewSet, basename='permission-setup')
router.register(r'dynamic-tabs', views.DynamicTabsViewSet, basename='dynamic-tabs')
urlpatterns = [
    path('', include(router.urls)),
    path("user-dashboard-tiles/",views.GetUserDashboardtiles.as_view(),name="user-dashboard-tiles"),
    path("user-dashboard-tiles1/",views.GetUserDashboardtiles1.as_view(),name="user-dashboard-tiles1"),
    path("user-dashboard-team-order-list/",views.TeamOrderListForDashboard.as_view(),name="user-dashboard-team-order-list"),
    path("top-shelling-product-list/",views.TopShellingProduct.as_view(),name="top-shelling-product-list"),
    path("top-selling-product-list1/",views.TopShellingProduct1.as_view(),name="top-shelling-product-list1"),
    path("schedule-order-dashboard-chart/",views.ScheduleOrderForDashboard.as_view(),name="schedule-order-dashboard-chart"),
    path("top-buying-state/",views.StateWiseSalesTracker.as_view(),name="top-buying-state"),
    path("invoice-dashboard-data/",views.InvoiceDataForDashboard.as_view(),name="invoice-dashboard-data"),
    path("sales-forecast-dashboard-data/",views.SalesForecastDashboard.as_view(),name="sales-forecast-dashboard-data"),
    path("order-status-summary/",views.OrderStatusSummary.as_view(),name="order-status-summary")
]