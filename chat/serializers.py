from rest_framework import serializers
from .models import Chat,ChatSession,Group,GroupDetails, Notification
class ChatSerializer(serializers.ModelSerializer):
    class Meta:
        model = Chat
        fields = '__all__'

class ChatSesstionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatSession
        fields = '__all__'

class ChatGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = '__all__'

class ChatGroupDetailsSerializer(serializers.ModelSerializer):
    class Meta:
        model = GroupDetails
        fields = '__all__'  # or specify the fields you want to include


class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = '__all__'
class GroupDetailsSerializer(serializers.ModelSerializer):
    class Meta:
        model = GroupDetails
        fields = '__all__'

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = '__all__'