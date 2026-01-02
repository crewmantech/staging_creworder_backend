from rest_framework import serializers
from accounts.models import User, Company
from .models import AssetType, Asset, AssetAssignment, AssetLog


class AssetTypeSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source="company.name", read_only=True)
    branch_name = serializers.CharField(source="branch.name", read_only=True)

    class Meta:
        model = AssetType
        fields = [
            "id",
            "company", "company_name",
            "branch", "branch_name",
            "name", "description",
            "requires_serial", "active",
            "created_at", "updated_at"
        ]
        read_only_fields = [
            "id",
            "company",      # 🔒 locked
            "created_at",
            "updated_at"
        ]



# ---------------- ASSET ----------------
class AssetSerializer(serializers.ModelSerializer):
    asset_type_name = serializers.CharField(source="asset_type.name", read_only=True)
    company_name = serializers.CharField(source="company.name", read_only=True)
    branch_name = serializers.CharField(source="branch.name", read_only=True)
    current_assignment = serializers.SerializerMethodField()

    class Meta:
        model = Asset
        fields = [
            "id", "asset_type", "asset_type_name",
            "company", "company_name",
            "branch", "branch_name",
            "name", "serial_number", "model_number",
            "purchase_date", "warranty_end_date",
            "status", "notes", "is_active",
            "created_at", "updated_at",
            "current_assignment"
        ]
        read_only_fields = [
            "id",
            "company",              # 🔒 locked
            "status",               # optional but recommended
            "created_at",
            "updated_at",
            "current_assignment"
        ]

    def get_current_assignment(self, obj):
        assign = obj.assignments.filter(active=True).first()
        if not assign:
            return None
        return {
            "assignment_id": assign.id,
            "employee": assign.employee.id,
            "employee_name": assign.employee.username,
            "assigned_on": assign.assigned_on,
            "expected_return_date": assign.expected_return_date,
        }


# ---------------- ASSET ASSIGNMENT ----------------
class AssetAssignmentSerializer(serializers.ModelSerializer):
    asset_detail = serializers.CharField(source="asset.name", read_only=True)
    employee_name = serializers.CharField(source="employee.username", read_only=True)
    company_name = serializers.CharField(source="company.company_id", read_only=True)
    branch_name = serializers.CharField(source="branch.name", read_only=True)

    class Meta:
        model = AssetAssignment
        fields = [
            "id",
            "asset", "asset_detail",
            "employee", "employee_name",
            "company", "company_name",
            "branch", "branch_name",
            "assigned_by", "assigned_on",
            "expected_return_date", "returned_on",
            "return_condition", "active", "notes"
        ]
        read_only_fields = [
            "id",
            "company",        # 🔒 locked
            "branch",         # 🔒 backend-controlled
            "assigned_by",
            "assigned_on",
            "returned_on",
            "active"
        ]


# ---------------- ASSET LOG ----------------
class AssetLogSerializer(serializers.ModelSerializer):
    asset_name = serializers.CharField(source="asset.name", read_only=True)
    by_user_name = serializers.CharField(source="by_user.username", read_only=True)
    branch_name = serializers.CharField(source="branch.name", read_only=True)
    company_name = serializers.CharField(source="company.name", read_only=True)

    class Meta:
        model = AssetLog
        fields = [
            "id",
            "asset", "asset_name",
            "event",
            "by_user", "by_user_name",
            "company", "company_name",
            "branch", "branch_name",
            "timestamp", "metadata"
        ]
        read_only_fields = fields   # 🔒 FULLY READ-ONLY
