from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ( AppointmentLayoutAPIView, AppointmentLayoutDetailAPIView, AppointmentViewSet, FollowUpExportAPIView, GetPhoneByReferenceAPIView, GetPhoneByReferenceAllAPIView, NotepadCreateOrUpdate,
                    NotepadDetail,
                    FollowUpView)
router = DefaultRouter()
router.register(r'follow-up',FollowUpView,basename='follow-up')
router.register(r"appointments", AppointmentViewSet, basename="appointments")
urlpatterns = [
    path('', include(router.urls)),
    path('createNotepad/', NotepadCreateOrUpdate.as_view(), name='createNotepad'),
    path('getNotepad/<int:auth_id>/', NotepadDetail.as_view(), name='notepad_detail'),  
    path('followups/export/', FollowUpExportAPIView.as_view(), name='followup-export'),
    path(
        "get-phone-by-reference/",
        GetPhoneByReferenceAPIView.as_view(),
        name="get-phone-by-reference",
    ),
    path('get-phone-by-all-reference',GetPhoneByReferenceAllAPIView.as_view(),name="get-phone-by-all-reference"),
    path("appointment-layout/", AppointmentLayoutAPIView.as_view()),
    path("appointment-layout/<str:pk>/", AppointmentLayoutDetailAPIView.as_view()),
]