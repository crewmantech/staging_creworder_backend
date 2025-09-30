from rest_framework import serializers

from orders.models import Products
from .models import DealCategoryModel, lead_form, Lead, LeadModel, LeadSourceModel, LeadStatusModel, Pipeline, UserCategoryAssignment
from django.contrib.auth.models import User

class LeadSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeadModel
        fields = '__all__'


class LeadSourceModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeadSourceModel
        fields = ['id', 'name', 'branch', 'company', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']


class LeadNewSerializer(serializers.ModelSerializer):
    product_name = serializers.SerializerMethodField()
    assign_user_name = serializers.SerializerMethodField()
    status_name = serializers.SerializerMethodField()
    class Meta:
        model = Lead
        fields = '__all__'  # includes product and assign_user (as IDs)
        extra_fields = ['product_name', 'assign_user_name','status_name']

    def get_product_name(self, obj):
        return obj.product.product_name if obj.product else None
    def get_status_name(self, obj):
        return obj.status.name if obj.status else None
    
    def get_assign_user_name(self, obj):
        return obj.assign_user.get_full_name() if obj.assign_user else None

    def create(self, validated_data):
        # pipeline = validated_data.get('lead_source').pipeline_set.first()
        # if pipeline and pipeline.round_robin:
        #     assigned_user = pipeline.assigned_users.first()  # Replace with actual round-robin logic
        #     validated_data['assign_user'] = assigned_user
        return super().create(validated_data)
    
class LeadStatusModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeadStatusModel
        fields = ['id', 'name', 'branch', 'company', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']

class DealCategoryModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = DealCategoryModel
        fields = ['id', 'name', 'branch', 'company', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']

class UserCategoryAssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserCategoryAssignment
        fields = '__all__'


class PipelineSerializer(serializers.ModelSerializer):
    assigned_users = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), many=True)

    class Meta:
        model = Pipeline
        fields =  '__all__'


class DynamicRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = lead_form
        fields = ['id', 'fields','form_name', 'pipeline', 'created_at']