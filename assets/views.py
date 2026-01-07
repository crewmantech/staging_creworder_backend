from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from accounts.models import Company
from accounts.views import StandardResultsSetPagination

from .models import AssetType, Asset, AssetAssignment, AssetLog
from .serializers import AssetTypeSerializer, AssetSerializer, AssetAssignmentSerializer, AssetLogSerializer
from rest_framework.response import Response
import logging
logger = logging.getLogger("assets")


# ====================================================
# AssetType
# ====================================================
class AssetTypeViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    serializer_class = AssetTypeSerializer

    def _get_company(self):
        user = self.request.user

        # 1️⃣ Try from query params (GET)
        company_id = self.request.query_params.get("company")

        # 2️⃣ Try from request body (POST / PUT / PATCH)
        if not company_id:
            company_id = self.request.data.get("company")

        # 3️⃣ If company_id provided, fetch manually
        if company_id:
            company = Company.objects.filter(id=company_id).first()
            if not company:
                raise ValidationError({"company": "Invalid company id"})
            return company

        # 4️⃣ Fallback to user's company
        if hasattr(user, "profile") and user.profile.company:
            return user.profile.company

        raise ValidationError({"company": "Company is required"})
    
    def get_queryset(self):
        company = self._get_company()
        branch_id = self.request.query_params.get("branch")

        qs = (
            AssetType.objects
            .select_related("company", "branch")
            .filter(company=company)
        )

        if branch_id:
            qs = qs.filter(branch_id=branch_id)

        return qs
    
    def perform_create(self, serializer):
        company = self._get_company()
        branch = self.request.data.get("branch") or None

        serializer.save(
            company=company,
            branch_id=branch
        )



# ====================================================
# Asset
# ====================================================
class AssetViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    serializer_class = AssetSerializer

    def _get_company(self):
        user = self.request.user

        # 1️⃣ Try from query params (GET)
        company_id = self.request.query_params.get("company")

        # 2️⃣ Try from request body (POST / PUT / PATCH)
        if not company_id:
            company_id = self.request.data.get("company")

        # 3️⃣ If company_id provided, resolve manually (NO get_object_or_404)
        if company_id:
            company = Company.objects.filter(id=company_id).first()
            if not company:
                raise ValidationError({"company": "Invalid company id"})
            return company

        # 4️⃣ Fallback to user's company
        if hasattr(user, "profile") and user.profile.company:
            return user.profile.company

        raise ValidationError({"company": "Company is required"})
    
    def get_queryset(self):
        company = self._get_company()
        branch_id = self.request.query_params.get("branch")

        qs = Asset.objects.select_related(
            "asset_type", "company", "branch"
        ).filter(company=company)

        if branch_id:
            qs = qs.filter(branch_id=branch_id)

        return qs
    
    

    def perform_create(self, serializer):
        user = self.request.user
        company = self._get_company()
        branch = self.request.data.get("branch") or None

        asset = serializer.save(
            company=company,
            branch_id=branch
        )

        AssetLog.objects.create(
            asset=asset,
            event="created",
            by_user=user,
            metadata={"asset_id": asset.id}
        )


# ====================================================
# AssetAssignment
# ====================================================
class AssetAssignmentViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    serializer_class = AssetAssignmentSerializer

    # -------------------------------
    # Company Resolver
    # -------------------------------
    def _get_company(self):
        user = self.request.user

        company_id = (
            self.request.query_params.get("company")
            or self.request.data.get("company")
        )

        if company_id:
            company = Company.objects.filter(id=company_id).first()
            if not company:
                raise ValidationError({"company": "Invalid company id"})
            return company

        if hasattr(user, "profile") and user.profile.company:
            return user.profile.company

        raise ValidationError({"company": "Company is required"})

    def get_queryset(self):
        user = self.request.user
        profile = getattr(user, "profile", None)

        company = self._get_company()
        branch_id = self.request.query_params.get("branch")

        qs = AssetAssignment.objects.select_related(
            "asset", "employee", "company", "branch"
        )

        # ---------------------------
        # SUPERADMIN
        # ---------------------------
        if profile and profile.user_type == "superadmin":
            if company:
                qs = qs.filter(company=company)
            if branch_id:
                qs = qs.filter(branch_id=branch_id)
            return qs

        # ---------------------------
        # ADMIN
        # ---------------------------
        if profile and profile.user_type == "admin":
            qs = qs.filter(company=profile.company)

            if branch_id:
                qs = qs.filter(branch_id=branch_id)

            return qs

        # ---------------------------
        # AGENT (DEFAULT USER)
        # ---------------------------
        qs = qs.filter(employee=user)

        if branch_id:
            qs = qs.filter(branch_id=branch_id)

        return qs


    # -----------------------------------------------
    # Assign Asset
    # -----------------------------------------------
    @action(detail=False, methods=["post"], url_path="assign")
    def assign(self, request):
        user = request.user
        company = self._get_company()

        asset_id = request.data.get("asset")
        employee_id = request.data.get("employee")
        expected_return = request.data.get("expected_return_date")
        notes = request.data.get("notes", "")
        

        if not asset_id or not employee_id:
            return Response(
                {"detail": "asset and employee are required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            with transaction.atomic():
                asset = Asset.objects.select_for_update().get(pk=asset_id)

                # 🔒 Ensure asset belongs to same company
                if asset.company_id != company.id:
                    return Response(
                        {"detail": "Asset does not belong to this company"},
                        status=status.HTTP_403_FORBIDDEN
                    )

                if asset.status != "available":
                    return Response(
                        {"detail": "Asset not available"},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                AssetAssignment.objects.filter(asset=asset, active=True).update(
                    active=False,
                    returned_on=timezone.now().date()
                )

                assignment = AssetAssignment.objects.create(
                    asset=asset,
                    employee_id=employee_id,
                    assigned_by=user,
                    expected_return_date=expected_return,
                    notes=notes,
                    active=True,
                    company=company,
                    branch=asset.branch
                )

                asset.status = "assigned"
                asset.save()

                AssetLog.objects.create(
                    asset=asset,
                    event="assigned",
                    by_user=user,
                    metadata={"assignment_id": assignment.id}
                )

            return Response(
                AssetAssignmentSerializer(assignment).data,
                status=status.HTTP_201_CREATED
            )

        except Asset.DoesNotExist:
            return Response(
                {"detail": "Asset not found"},
                status=status.HTTP_404_NOT_FOUND
            )
    # -----------------------------------------------
    # Return Asset
    # -----------------------------------------------
    @action(detail=True, methods=["post"], url_path="return")
    def return_asset(self, request, pk=None):
        assignment = self.get_object()

        if not assignment.active:
            return Response(
                {"detail": "Already returned"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Normalize condition (case-insensitive)
        condition = (request.data.get("return_condition") or "").strip().lower()
        notes = request.data.get("notes", "")

        asset = assignment.asset
        user = request.user

        with transaction.atomic():

            # -----------------------------
            # ASSET STATUS MAPPING
            # -----------------------------
            if condition == "broken":
                asset.status = "broken"
            elif condition == "damaged":
                asset.status = "damaged"
            elif condition in ["not working", "not_working", "not-working"]:
                asset.status = "not working"
            else:
                asset.status = "available"

            asset.status = asset.status.lower()
            asset.save()

            # -----------------------------
            # STORE FULL HISTORY IN LOG
            # -----------------------------
            AssetLog.objects.create(
                asset=asset,
                event="returned",
                by_user=user,
                metadata={
                    "assigned_to": assignment.employee_id,
                    "company": assignment.company_id,
                    "branch": assignment.branch_id,
                    "assigned_on": str(assignment.assigned_on),
                    "returned_on": str(timezone.now().date()),
                    "return_condition": condition,
                    "notes": notes,
                }
            )

            # -----------------------------
            # DELETE ASSIGNMENT (IMPORTANT)
            # -----------------------------
            assignment.delete()

        return Response(
            {"detail": "Asset returned successfully"},
            status=status.HTTP_200_OK
        )


# ====================================================
# AssetLog (Read only)
# ====================================================
class AssetLogViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    serializer_class = AssetLogSerializer

    def get_queryset(self):
        user = self.request.user
        company = user.profile.company
        branch_id = self.request.query_params.get("branch")

        qs = AssetLog.objects.select_related(
            "asset", "by_user", "company", "branch"
        ).filter(company=company)

        if branch_id:
            qs = qs.filter(branch_id=branch_id)

        return qs
