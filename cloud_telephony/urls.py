from django.urls import path, include
from rest_framework.routers import DefaultRouter
# from .views import (
#     CreateCloudTelephoneyChannel,
#     CloudTelephoneyChannelDelete,
#     CloudTelephoneyChannelUpdate,
#     CloudTelephoneyChannelList,
#     CloudtelephoneyChannelAssignForUser,
#     CloudTelephoneyChannelAssignUpdate,
#     CloudTelephoneyChannelAssignDelete,
#     UserMailSetupView
# )
from .views import (
    CallServiceViewSet,
    CloudTelephonyVendorViewSet, 
    CloudTelephonyChannelViewSet, 
    CloudTelephonyChannelAssignViewSet,
    GetNumberAPIView, 
    UserMailSetupViewSet
)
router = DefaultRouter()
router.register(r'telephony-vendors', CloudTelephonyVendorViewSet, basename='vendor')
router.register(r'telephony-channels', CloudTelephonyChannelViewSet, basename='channel')
router.register(r'telephony-channel-assigns', CloudTelephonyChannelAssignViewSet, basename='channel-assign')
router.register(r'telephony-user-mail-setup', UserMailSetupViewSet, basename='mail-setup')
router.register(r'callservice',CallServiceViewSet,basename='for-call')
# router.register(r'user-mail-setup',UserMailSetupView,basename='user-mail-setup')
urlpatterns = [
    path("", include(router.urls)),
     path('callservice/get-number/', GetNumberAPIView.as_view(), name='get-number'),
    # path(
    #     "createCloudTelephoneyChannel/",
    #     CreateCloudTelephoneyChannel.as_view(),
    #     name="create_cloud_telephoney_channel",
    # ),
    # path(
    #     "deleteCloudTelephoneyChannel/<int:id>/",
    #     CloudTelephoneyChannelDelete.as_view(),
    #     name="delete_cloud_telephoney_channel",
    # ),
    # path(
    #     "updateCloudTelephoneyChannel/<int:id>/",
    #     CloudTelephoneyChannelUpdate.as_view(),
    #     name="update_cloud_telephoney_channel",
    # ),
    # path(
    #     "getCloudTelephoneyChannel/",
    #     CloudTelephoneyChannelList.as_view(),
    #     name="get_cloud_telephoney_channel",
    # ),
    # path(
    #     "assignCloudTelephoneyChannel/",
    #     CloudtelephoneyChannelAssignForUser.as_view(),
    #     name="assgin_telephoney_channel",
    # ),
    # path(
    #     "updateAssignCloudTelephoneyChannel/<int:id>/",
    #     CloudTelephoneyChannelAssignUpdate.as_view(),
    #     name="update_cloud_telephoney_assign",
    # ),
    # path(
    #     "deleteAssignCloudTelephoneyChannel/<int:id>/",
    #     CloudTelephoneyChannelAssignDelete.as_view(),
    #     name="delete_cloud_telephoney_channel",
    # ),
]