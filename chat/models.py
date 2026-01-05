from django.db import models
from django.contrib.auth.models import User
from django.db.models import Q
from middleware.request_middleware import get_request
# Create your models here.

class BaseModel(models.Model):
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="%(app_label)s_%(class)s_created_by")
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    def save(self, *args, **kwargs):
        request = get_request()
        if request and request.user.is_authenticated:
            if not self.pk:
                self.created_by = request.user
            self.updated_by = request.user
        super().save(*args, **kwargs)

    class Meta:
        abstract = True

class ChatSession(BaseModel):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=50, default='creworder', unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        db_table = 'chat_session_table'

    def __str__(self):
        return str(self.id)
class Group(BaseModel):
    class GroupStatus(models.IntegerChoices):
        INACTIVE = 0, 'Inactive'
        ACTIVE = 1, 'Active'

    id = models.AutoField(primary_key=True)
    group_name = models.CharField(max_length=50)
    group_status = models.IntegerField(choices=GroupStatus.choices, default=GroupStatus.INACTIVE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'group_chat_table'

    def __str__(self):
        return str(self.group_name)

class Chat(BaseModel):
    class ChatStatus(models.IntegerChoices):
        UNREAD = 0, 'Unread'  
        READ = 1, 'Read' 

    id = models.AutoField(primary_key=True)
    type = models.CharField(
        max_length=10,
        choices=[('private', 'Private'), ('group', 'Group')],
        default='private'
    )
    text = models.CharField(max_length=1000)
    message_type = models.CharField(
        max_length=10,
        choices=[('media', 'Media'), ('text', 'Text')],
        default='text'
    )    

    # For private chat
    from_user = models.ForeignKey(User, related_name='sent_chats', on_delete=models.CASCADE)
    to_user = models.ForeignKey(User, related_name='received_chats', on_delete=models.CASCADE, null=True, blank=True)

    # For group chat
    group = models.ForeignKey(Group, related_name='group_chats', on_delete=models.CASCADE, null=True, blank=True)

    # Chat session (optional for threading/grouping)
    chat_session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, default=1)

    chat_status = models.IntegerField(choices=ChatStatus.choices, default=ChatStatus.UNREAD)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'chat_detail_table'

    def __str__(self):
        return f"{self.from_user} -> {self.to_user or self.group}: {self.text[:20]}"

   


class GroupDetails(BaseModel):
    class GroupMemberType(models.IntegerChoices):
        ADMIN = 0, 'Admin'
        USER = 1, 'User'

    id = models.AutoField(primary_key=True)
    group = models.ForeignKey(Group, related_name='memberships', on_delete=models.CASCADE)
    member = models.ForeignKey(User, related_name='group_memberships', on_delete=models.CASCADE)
    member_status = models.IntegerField(choices=GroupMemberType.choices, default=GroupMemberType.USER)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'group_details_table'

    def __str__(self):
        return str(self.member)


# notifications/models.py

class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notifications")
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    url = models.TextField(null=True, blank=True)

    notification_type = models.CharField(
        max_length=50,
        choices=[
            ("followup_reminder", "Follow-up Reminder"),
            ("chat_message", "Chat Message"),
            ("group_chat", "Group Chat"),
            ("new_group", "New Group"),
        ]
    )

    followup = models.ForeignKey(
        "follow_up.Follow_Up",
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "followup", "notification_type"],
                condition=Q(followup__isnull=False),
                name="unique_followup_notification"
            )
        ]

    def __str__(self):
        return f"Notification for {self.user.username}"
