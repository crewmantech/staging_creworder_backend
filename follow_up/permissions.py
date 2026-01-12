from rest_framework.permissions import BasePermission


class AppointmentStatusPermission(BasePermission):
    """
    Permission mapping based on action
    """

    def has_permission(self, request, view):
        user = request.user

        if not user or not user.is_authenticated:
            return False

        permission_map = {
            'list': 'follow_up.view_appointmentstatus',
            'retrieve': 'follow_up.view_appointmentstatus',
            'create': 'follow_up.add_appointmentstatus',
            'update': 'follow_up.change_appointmentstatus',
            'partial_update': 'follow_up.change_appointmentstatus',
            'destroy': 'follow_up.delete_appointmentstatus',
        }

        required_permission = permission_map.get(view.action)

        if required_permission:
            return user.has_perm(required_permission)

        return False
