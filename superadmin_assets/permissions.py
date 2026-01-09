from rest_framework.permissions import BasePermission


class IsSuperAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.profile.user_type == 'superadmin'

class IsAssignedOrSuperAdmin(BasePermission):
    def has_object_permission(self, request, view, obj):
        return (
            request.user.profile.user_type == 'superadmin' or
            obj.assigned_to == request.user
        )
