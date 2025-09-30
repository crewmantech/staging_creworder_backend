from rest_framework.permissions import BasePermission

class CanUpdateStatusRemarkOrFullUpdate(BasePermission):
    """
    Custom permission to allow users to update only status and remark 
    unless they have full update permission.
    """
    def has_object_permission(self, request, view, obj):
        # Check if the user has full update permission
        if request.user.has_perm('lead_management.change_lead'):
            return True
        # Check if the user has permission to update status and remark only
        if request.method in ['PATCH', 'PUT']:
            # Ensure the fields being updated are limited to 'status' and 'remark'
            if request.user.has_perm('lead_management.update_lead_status_remark'):
                allowed_fields = {'status', 'remark'}
                requested_fields = set(request.data.keys())
                return requested_fields.issubset(allowed_fields)

        return False
