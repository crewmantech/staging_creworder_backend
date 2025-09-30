from rest_framework.permissions import BasePermission
from django.core.exceptions import PermissionDenied

class OrderPermissions(BasePermission):
    """
    Custom permission to check multiple required permissions for a given action.
    """
    permission_map = {
        'POST': ['superadmin_assets.show_submenusmodel_create_order', 'superadmin_assets.add_submenusmodel'],  # Example: Need both permissions
        # 'GET': ['superadmin_assets.show_submenusmodel_all_order', 'superadmin_assets.view_submenusmodel'],
        'DELETE': ['superadmin_assets.show_submenusmodel_all_order', 'superadmin_assets.delete_submenusmodel'],
        'PUT': ['superadmin_assets.show_submenusmodel_all_order', 'superadmin_assets.change_submenusmodel'],
        # Example: Need both permissions
    }

    def has_permission(self, request, view):
        required_permissions = self.permission_map.get(request.method)
        if required_permissions:
            if not all(request.user.has_perm(perm) for perm in required_permissions):
                return False  # Deny if the user lacks any permission
        return True

class CategoryPermissions(BasePermission):
    """
    Custom permission to check multiple required permissions for a given action.
    """
    permission_map = {
        'POST': ['superadmin_assets.show_submenusmodel_add_category', 'superadmin_assets.add_submenusmodel'],  # Example: Need both permissions
        'GET': ['superadmin_assets.show_submenusmodel_category_list', 'superadmin_assets.view_submenusmodel'],
        'DELETE': ['superadmin_assets.show_submenusmodel_category_list', 'superadmin_assets.delete_submenusmodel'],
        'PUT': ['superadmin_assets.show_submenusmodel_category_list', 'superadmin_assets.change_submenusmodel'],
         # Example: Need both permissions
    }

    def has_permission(self, request, view):
        required_permissions = self.permission_map.get(request.method)
        if required_permissions:
            if not all(request.user.has_perm(perm) for perm in required_permissions):
                return False  # Deny if the user lacks any permission
        return True
    


class ShipmentPermissions(BasePermission):
    """
    Custom permission to check multiple required permissions for a given action.
    """
    permission_map = {
        'POST': ['superadmin_assets.show_menumodel_shipment', 'superadmin_assets.add_submenusmodel'],  # Example: Need both permissions
        'GET': ['superadmin_assets.show_menumodel_shipment', 'superadmin_assets.view_submenusmodel'],
        'DELETE': ['superadmin_assets.show_menumodel_shipment', 'superadmin_assets.delete_submenusmodel'],
        'PUT': ['superadmin_assets.show_menumodel_shipment', 'superadmin_assets.change_submenusmodel']  # Example: Need both permissions
    }

    def has_permission(self, request, view):
        required_permissions = self.permission_map.get(request.method)
        if required_permissions:
            if not all(request.user.has_perm(perm) for perm in required_permissions):
                return False  # Deny if the user lacks any permission
        return True
    

class OrderStatusPermission(BasePermission):
    """
    Custom permission to check if the user has 'view_OrderDetail_order_status_tracking' permission.
    """
    def has_permission(self, request, view):
        # Ensure user is authenticated
        if not request.user.is_authenticated:
            return False
        
        # Check if user_type is 'agent' and has the required permission
        return request.user.profile.user_type  == "agent" and request.user.has_perm('orders.view_OrderDetail_order_status_tracking')
