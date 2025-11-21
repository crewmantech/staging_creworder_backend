from django.urls import path
from .views import CreateNotification, GetNotifications, MarkNotificationRead, RecentChatUserAPIView, getChatDetail,createChat,chat_count,GetGroups,CreateGroup,getUserListChat,UserListView1,getUserListChatAdmin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
router = DefaultRouter()
urlpatterns = [
    path('', include(router.urls)),
    path('getChatDetail/', getChatDetail.as_view(), name='get_chat_detail'),
    path('createChat/', createChat.as_view(), name='create_chat'),
    path('getChatCount/', chat_count.as_view(), name='chat_count'),
    path('getChatgroups/', GetGroups.as_view(), name='chat_groups'),
    path('createGroup/', CreateGroup.as_view(), name='create_group'),
    path('getUserListChat/', getUserListChat.as_view(), name='get_user_list'),
    path('getUserListChatAdmin/', getUserListChatAdmin.as_view(), name='get_user_list_admin'),
    path("notifications/", GetNotifications.as_view(), name="get_notifications"),
    path("mark-notification/", MarkNotificationRead.as_view(), name="send_notification"),
    path("create-notification/", CreateNotification.as_view(), name="create-notification"),
    path("chat-users/", UserListView1.as_view(), name="chat-user-list"),
    path("recent-chat-users/", RecentChatUserAPIView.as_view(), name="recent-chat-users"),

    #  path('notifications/mark_as_read/<int:notification_id>/', mark_as_read, name='mark_as_read'),
]
