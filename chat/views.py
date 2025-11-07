from django.utils import timezone
from datetime import timedelta
import sys
from django.db.models import Max
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Chat, Group, Notification
from .serializers import (
    ChatSerializer,
    ChatGroupSerializer,
    GroupSerializer,
    GroupDetailsSerializer,
    NotificationSerializer,
)
from accounts.serializers import UserSerializer
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Chat, ChatSession, Group, GroupDetails, User
from rest_framework.permissions import IsAuthenticated
from rest_framework.generics import ListAPIView
from accounts.models import Department, ExpiringToken as Token
from django.db.models import Q

class getChatDetail(APIView):
    serializer_class = ChatSerializer
    permission_classes = [IsAuthenticated]

    # =======================================================================
    #                Retrieve Chat Details
    # =======================================================================

    

    def get(self, request):
        from_user = request.query_params.get("from_user")
        to_user = request.query_params.get("to_user")
        group_id = request.query_params.get("group_id")

        # Validate required params
        if group_id is None:
            if not from_user:
                return Response({"Success": False, "Message": "Please pass from_user"},
                                status=status.HTTP_400_BAD_REQUEST)
            if not to_user:
                return Response({"Success": False, "Message": "Please pass to_user"},
                                status=status.HTTP_400_BAD_REQUEST)

        # Get Chat Session
        if group_id:
            chatSessionId = ChatSession.objects.filter(name=f"{group_id}").first()
        else:
            chatSessionId = (
                ChatSession.objects.filter(name=f"{from_user}_{to_user}").first()
                or ChatSession.objects.filter(name=f"{to_user}_{from_user}").first()
            )

        if chatSessionId is None:
            return Response({"Success": False, "Message": "Data not exist.!"},
                            status=status.HTTP_400_BAD_REQUEST)

        # Filter chats of only last 24 hours
        time_threshold = timezone.now() - timedelta(hours=24)

        # Mark messages from other person as read
        Chat.objects.filter(from_user=to_user, chat_session=chatSessionId).update(chat_status=Chat.ChatStatus.READ)

        # Fetch chat data & ONLY SHOW users where profile.status = 1
        chatData = Chat.objects.filter(
            chat_session=chatSessionId,
            created_at__gte=time_threshold
        ).filter(
            Q(from_user__profile__status=1) | Q(to_user__profile__status=1)
        ).order_by("-created_at")

        serializer = ChatSerializer(chatData, many=True)
        return Response({"Success": True, "data": serializer.data}, status=status.HTTP_200_OK)

import json
from asgiref.sync import async_to_sync
class createChat(APIView):
    serializer_class = ChatSerializer
    permission_classes = [IsAuthenticated]

    # =======================================================================
    #                Create New Chat Message
    # =======================================================================

    def post(self, request):
        from_user = request.data.get("from_user")
        to_user = request.data.get("to_user")
        chat_type = request.data.get("chat_type")
        session = None
        if chat_type is None:
            session = (
                Chat.objects.filter(from_user=from_user, to_user=to_user).first()
                or Chat.objects.filter(from_user=to_user, to_user=from_user).first()
            )
        if session:
            session_id = session.chat_session_id
        else:
            if chat_type == "group_chat":
                session = ChatSession.objects.filter(name=f"{to_user}").first()
            else:
                session = (
                    ChatSession.objects.filter(name=f"{from_user}_{to_user}").first()
                    or ChatSession.objects.filter(name=f"{to_user}_{from_user}").first()
                )

            if session:
                session_id = session.id
            else:
                if chat_type == "group_chat":
                    new_session = ChatSession.objects.create(name=f"{to_user}")
                else:
                    new_session = ChatSession.objects.create(
                        name=f"{from_user}_{to_user}"
                    )
                session_id = new_session.id

        serializer = ChatSerializer(data={**request.data, "chat_session": session_id})
        if serializer.is_valid():
            chat_message = serializer.save()

            # Create a notification for the recipient
            notification_message = f'New message from {chat_message.from_user.username}'
            notification_data = {
                'user': chat_message.to_user.id,
                'message': notification_message,
                "url":"/chat/?user_id="+str(from_user),
                'notification_type': 'chat_message'
            }
            notification_serializer = NotificationSerializer(data=notification_data)
            if notification_serializer.is_valid():
                notification = notification_serializer.save()

                # Send WebSocket notification
                # channel_layer = get_channel_layer()
                # a= async_to_sync(channel_layer.group_send)(
                #     f"notifications_{chat_message.to_user.id}",
                #     {
                #         "type": "send_notification",
                #         "message": notification.message,
                #     },
                # )
                return Response(
                    {"Success": True, "ChatData": serializer.data, "SessionID": session_id},
                    status=status.HTTP_201_CREATED,
                )
            else:
                return Response(
                    {"Success": False, "Errors": notification_serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            return Response(
                {"Success": False, "Errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

class chat_count(APIView):
    permission_classes = [IsAuthenticated]

    # =======================================================================
    #                Count Unread Messages
    # =======================================================================

   

    def get(self, request):
        from_user = request.query_params.get("from_user")
        to_user = request.query_params.get("to_user")
        session = (
            Chat.objects.filter(from_user=from_user, to_user=to_user).first()
            or Chat.objects.filter(from_user=to_user, to_user=from_user).first()
        )
        if session:
            session_id = session.chat_session_id
            chat_count = Chat.objects.filter(
                to_user=to_user, chat_session_id=session_id, chat_status=1
            ).count()
            return Response(
                {"Success": True, "chat_count": chat_count, "SessionID": session_id},
                status=status.HTTP_201_CREATED,
            )
        else:
            return Response(
                {"Success": False, "Errors": "Session not able"},
                status=status.HTTP_400_BAD_REQUEST,
            )


class getUserListChat(APIView):
    permission_classes = [IsAuthenticated]

    # =======================================================================
    #                Retrieve User List for Chat
    # =======================================================================

    

    def get(self, request):
        user_id = request.query_params.get("user_id")

        if not user_id:
            return Response(
                {"Success": False, "Errors": "User ID is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Get unique users the requester has chatted with
        unique_to_users = (
            Chat.objects.filter(from_user=user_id)
            .values_list("to_user", flat=True)
            .distinct()
        )

        # ✅ Only show users whose profile.status = 1
        users = User.objects.filter(
            id__in=unique_to_users,
            profile__status=1
        )

        user_serializer = UserSerializer(users, many=True)

        return Response(
            {"Success": True, "results": user_serializer.data},
            status=status.HTTP_200_OK,
        )


class GetGroups(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user_id = request.query_params.get("user_id")
        if not user_id:
            return Response(
                {"Success": False, "Errors": "user_id is required"},
                status=status.HTTP_200_OK,
            )

        group_details = (
            GroupDetails.objects.filter(member_id=user_id)
            .select_related("group")
            .prefetch_related("member")
        )

        if group_details.exists():
            data = []
            unique_groups = group_details.values("group_id").distinct()
            for group in unique_groups:
                group_id = group["group_id"]
                group_info = Group.objects.get(id=group_id)
                member_count = GroupDetails.objects.filter(group_id=group_id).count()
                members_details = GroupDetails.objects.filter(group_id=group_id).select_related("member")

                members = []
                for detail in members_details:
                    members.append(
                        {
                            "member_id": detail.member.id,
                            "member_name": detail.member.username,
                            "group_id": detail.group_id,
                            "member_status": detail.member_status,
                        }
                    )

                data.append(
                    {
                        "group_id": group_info.id,
                        "group_name": group_info.group_name,
                        "member_count": member_count,
                        "members": members,
                    }
                )

            return Response({"Success": True, "Groups": data}, status=status.HTTP_200_OK)

        return Response(
            {"Success": False, "Errors": f"No groups found for user_id {user_id}"},
            status=status.HTTP_200_OK,
        )


class CreateGroup(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        group_name = request.data.get("group_name")
        members_data = request.data.get("members", [])

        if not group_name:
            return Response(
                {"Success": False, "Errors": "group_name is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Create Group
        group_serializer = GroupSerializer(data={"group_name": group_name})
        if group_serializer.is_valid():
            group = group_serializer.save()
        else:
            return Response(
                {"Success": False, "Errors": group_serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Add members to GroupDetails
        for member_data in members_data:
            member_serializer = GroupDetailsSerializer(
                data={
                    "group": group.id,
                    "member": member_data.get("group_member_id"),
                    "member_status": member_data.get(
                        "group_member_status", GroupDetails.GroupMemberType.USER
                    ),
                }
            )
            if member_serializer.is_valid():
                member_serializer.save()
            else:
                return Response(
                    {"Success": False, "Errors": member_serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        return Response(
            {"Success": True, "Group": group_serializer.data},
            status=status.HTTP_201_CREATED,
        )



class GetNotifications(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        notifications = Notification.objects.filter(user=user, is_read=False).order_by("-created_at")
        serializer_data = [{"id": n.id, "message": n.message, "notification_type": n.notification_type,"url":n.url} for n in notifications]
        
        return Response({"Success": True, "notifications": serializer_data}, status=status.HTTP_200_OK)


class MarkNotificationRead(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        notification_id = request.data.get("notification_id")
        try:
            notification = Notification.objects.get(id=notification_id, user=request.user)
            notification.is_read = True
            notification.save()
            return Response({"Success": True, "Message": "Notification marked as read"}, status=status.HTTP_200_OK)
        except Notification.DoesNotExist:
            return Response({"Success": False, "Message": "Notification not found"}, status=status.HTTP_400_BAD_REQUEST)

class CreateNotification(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            user_id = request.data.get("user_id")
            message = request.data.get("message")
            notification_type = request.data.get("notification_type")

            # Validate inputs
            if not user_id or not message or not notification_type:
                return Response(
                    {"Success": False, "message": "Missing required fields"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Fetch the user instance
            user = User.objects.filter(id=user_id).first()

            if not user:
                return Response(
                    {"Success": False, "message": "User not found"},
                    status=status.HTTP_404_NOT_FOUND,
                )

            # Create a new notification
            notification = Notification.objects.create(
                user=user,
                message=message,
                notification_type=notification_type,
            )

            return Response(
                {"Success": True, "message": "Notification created successfully"},
                status=status.HTTP_201_CREATED,
            )

        except Exception as e:
            return Response(
                {"Success": False, "message": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
# @api_view(['POST'])
# def mark_as_read(request, notification_id):
#     try:
#         notification = Notification.objects.get(id=notification_id, user=request.user)
#         notification.read = True
#         notification.save()
#         return Response({"message": "Notification marked as read"}, status=200)
#     except Notification.DoesNotExist:
        # return Response({"error": "Notification not found"}, status=404)






# from rest_framework.authtoken.models import Token
class UserListView1(ListAPIView):
    """API to list users based on role-based filtering"""
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        queryset = User.objects.none()  # Default empty queryset

        try:
            if hasattr(user, 'profile'):  # Ensure user has a profile
                if user.profile.user_type == "superadmin":
                    company_id = self.request.query_params.get("company_id")
                    if company_id:
                        queryset = User.objects.filter(profile__company_id=company_id,profile__status=1)
                    else:
                        queryset = User.objects.filter(profile__company=None,profile__status=1)

                elif user.profile.user_type == "admin":
                    company = user.profile.company
                    queryset = User.objects.filter(profile__company=company,profile__status=1)

                elif user.profile.user_type == "agent" and  user.has_perm("accounts.chat_user_permission_others"):
                    branch = user.profile.branch
                    queryset = User.objects.filter(profile__branch=branch,profile__status=1)
                    company = getattr(user.profile, "company", None)
                    branch = getattr(user.profile, "branch", None)
                    department = getattr(user.profile, "department", None)

                    base_queryset = User.objects.filter(
                        profile__company=company,
                        profile__status=1,
                    )

                    # Check department-related permissions
                    user_permissions = user.get_all_permissions()
                    department_permissions = [
                        perm for perm in user_permissions if perm.startswith("department")
                    ]

                    allowed_departments = []

                    # If user can view all departments
                    if any("can_view_all" in perm for perm in department_permissions):
                        queryset = base_queryset

                    # If user can view only their own department
                    elif any("can_view_own" in perm for perm in department_permissions):
                        queryset = base_queryset.filter(profile__department=department)

                    # If user has specific department view permissions
                    else:
                          # adjust to your app name
                        for perm in department_permissions:
                            if "can_view" in perm and "can_view_all" not in perm and "can_view_own" not in perm:
                                # Extract department name from permission (if stored like "Can view Sales Department")
                                try:
                                    department_name = perm.split("department_can_view_")[-1].replace("_", " ").strip()
                                    dept = Department.objects.filter(name__iexact=department_name).first()
                                    if dept:
                                        allowed_departments.append(dept.id)
                                except Exception:
                                    continue

                        queryset = base_queryset.filter(profile__department_id__in=allowed_departments)

                    # # For agent with chat_user_permission_others
                    # if user_type == "agent" and user.has_perm("accounts.chat_user_permission_others"):
                    #     queryset = queryset.filter(profile__branch=branch)

        except Exception as e:
            print(f"Error in get_queryset: {e}")

        return queryset

    def list(self, request, *args, **kwargs):
        """Custom response handling"""
        queryset = self.get_queryset().exclude(id=request.user.id)  # Exclude the requesting user
        serializer = self.get_serializer(queryset, many=True)
        data = serializer.data

        user_ids = [user['id'] for user in data]
        tokens = Token.objects.filter(user_id__in=user_ids).values_list('user_id', flat=True)

        for user in data:
            user['online'] = user['id'] in tokens  # Add online status

        return Response({"status": "success", "results": data}, status=status.HTTP_200_OK)
