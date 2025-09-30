from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from .views import AcceptedOrdersReportAPIView, AllowStatusViewSet, ChangeOrderStatusAPIView, CreateRepeatOrderAPIView, CustomerStateViewSet, ExternalOrderCreateView, FilterOrdersCreatedView, FilterOrdersView1, FilteredOrderViewSet, MainOrderStatusAPIView, NotificationsConfigViewSet, OrderAggregationByStatusAPIView, OrderLogListView, OrderStatusAPIView,FilterOrdersView, OrderStatusWorkflowViewSet, OrderValueSettingViewSet, PaymentStatusViewSet, PaymentTypeViewSet,PincodeLocalityViewSet,BulkOrderUploadView, ProductOrderSummaryView1, RecurringOrdersAPIView, ReturnTypeViewSet, ScanOrderAPIView, UpdateOrderStatusAndPaymentStatusView,OrderMetricsAPIView,ProductOrderSummaryView,LableLayoutAPIView,LableInvoiceAPIView,CSVProductUploadView

router = DefaultRouter()
router.register(r'order_status',OrderStatusAPIView)
router.register(r'filter-orders',FilterOrdersView,basename='filter-orders')
router.register(r'filter-orders1',FilterOrdersView1,basename='filter-orders1')
router.register(r'sales-agent-order',FilterOrdersCreatedView,basename='sales-agent-order')
router.register(r'pincode-locality', PincodeLocalityViewSet, basename='pincode-locality')
router.register(r'payment-status', PaymentStatusViewSet, basename='payment-status')
router.register(r'customer-states', CustomerStateViewSet, basename='customer-state')
router.register(r'payment-type', PaymentTypeViewSet, basename='payment-type')
router.register(r'order-value-settings', OrderValueSettingViewSet)
router.register(r'order-status-workflow', OrderStatusWorkflowViewSet, basename='order-status-workflow')
router.register(r'allow-status', AllowStatusViewSet, basename='allow-status')
router.register(r'return-types', ReturnTypeViewSet)
router.register(r'notification_configs', NotificationsConfigViewSet)
urlpatterns = [
    path("", include(router.urls)),
    path("get-orders/", views.OrderListView.as_view(), name="OrderListView"),
    path("get-OrderFilters/", views.OrderFiltersView.as_view(), name="OrderFiltersView"),
    path('order-statuss/', MainOrderStatusAPIView.as_view(), name='get-order-status'),
    path("orders/", views.OrderAPIView.as_view(), name="order-list-create"),
    path("orders/<int:pk>/", views.OrderAPIView.as_view(), name="order-detail"),
    path('filtered-orders/', FilteredOrderViewSet.as_view({'get': 'list'}), name='filtered-orders'),
    path("category/", views.CategoryView.as_view(), name="category-create"),
    path("category/<int:pk>", views.CategoryView.as_view(), name="update-create"),
    path("product/", views.ProductView.as_view(), name="product-create"),
    path("getproduct/<int:pk>", views.ProductView.as_view(), name="product-create"),
    path("product/<int:pk>", views.ProductView.as_view(), name="product-update-delete"),
    path(
        "products/<int:pk>/",
        views.ProductDetailAPIView.as_view(),
        name="product-detail",
    ),
    path("products/", views.ProductListCreateAPIView.as_view(), name="product-detail"),
    path(
        "getCategory/<int:pk>",
        views.CategorytDetailAPIView.as_view(),
        name="category-detail",
    ),
    path(
        "getCategory/",
        views.CategoryListCreateAPIView.as_view(),
        name="category-detail",
    ),
    path("export-order/", views.orderExport.as_view(), name="export-order"),
    path("invoice-deatails/", views.invoiceDetails.as_view(), name="invoice-deatails"),
    path(
        "check-serviceability/",
        views.CheckServiceability.as_view(),
        name="check-serviceability",
    ),
    path(
        "user-performance/", views.GetUserPerformance.as_view(), name="user-performance"
    ),
    path('bulk-upload/', BulkOrderUploadView.as_view(), name='bulk_order_upload'),
    path('order-aggregation-by-status/', OrderAggregationByStatusAPIView.as_view(), name='order-aggregation-by-status'),
    path('status-update/<int:pk>', UpdateOrderStatusAndPaymentStatusView.as_view(), name='status-update'),
    path('order-log/<int:order_id>/', OrderLogListView.as_view(), name='order-logs'),
    path('team-order-list/', OrderMetricsAPIView.as_view(), name='order-list-team'),
    path('products/order-summary/', ProductOrderSummaryView.as_view(), name='product-order-summary'),
    path('products/order-summary1/', ProductOrderSummaryView1.as_view(), name='product-order-summary1'),
    path('scanorder/', ScanOrderAPIView.as_view(), name='scan-order'),


    path('lable-layout/', LableLayoutAPIView.as_view(), name='lable-layout'),

    path('lable-layout/<int:id>/', LableLayoutAPIView.as_view(), name='lablelayout-detail'),


    path('invoice-layout/', LableInvoiceAPIView.as_view(), name='lable-invoice'),

    path('invoice-layout/<int:id>/', LableInvoiceAPIView.as_view(), name='lableinvoice-detail'),
    path('bulk-upload-product/', CSVProductUploadView.as_view(), name='bulk_product_upload'),
    path('orders-change-status/', ChangeOrderStatusAPIView.as_view(), name='change-order-status'),
    path('external-create-order/', ExternalOrderCreateView.as_view(), name='external-create-order'),
    path('orders-repeat/<int:order_id>/', CreateRepeatOrderAPIView.as_view(), name='repeat-order'),
    path('recurring-orders/', RecurringOrdersAPIView.as_view(), name='recurring-orders'),
    path('orders-report/', AcceptedOrdersReportAPIView.as_view(), name='orders-report'),
    
]