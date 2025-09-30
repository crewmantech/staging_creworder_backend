from rest_framework import serializers
from .models import Follow_Up,Notepad

class FollowUpSerializer(serializers.ModelSerializer):
    follow_status_name = serializers.CharField(source='follow_status.name', read_only=True)

    class Meta:
        model = Follow_Up
        fields = '__all__'  # Includes all original fields
        extra_fields = ['follow_status_name']  # Add this for clarity, optional

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['follow_status_name'] = instance.follow_status.name if instance.follow_status else None
        return representation


class NotepadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notepad
        fields = '__all__'