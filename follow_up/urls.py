from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ( FollowUpExportAPIView, NotepadCreateOrUpdate,
                    NotepadDetail,
                    FollowUpView)
router = DefaultRouter()
router.register(r'follow-up',FollowUpView,basename='follow-up')
urlpatterns = [
    path('', include(router.urls)),
    path('createNotepad/', NotepadCreateOrUpdate.as_view(), name='createNotepad'),
    path('getNotepad/<int:auth_id>/', NotepadDetail.as_view(), name='notepad_detail'),  
    path('followups/export/', FollowUpExportAPIView.as_view(), name='followup-export')
]