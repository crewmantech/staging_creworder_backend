import pdb
from rest_framework.permissions import BasePermission,SAFE_METHODS
from guardian.shortcuts import get_objects_for_user


class CanChangeCompanyStatusPermission(BasePermission):
    def has_object_permission(self, request, view, obj):
        pdb.set_trace()
        return request.user.has_perm('accounts.can_change_company_status')
    
class CanLeaveApproveAndDisapprove(BasePermission):
    def has_object_permission(self, request, view, obj):
        return request.user.has_perm('accounts.can_approve_disapprove_leaves')



class IsAdminOrSuperAdmin(BasePermission):
    """
    Custom permission to allow only admin or superadmin to create, update, or delete departments.
    """
    def has_permission(self, request, view):
        # Check if user is authenticated
        if not request.user.is_authenticated:
            return False
        
        # Check for user type (admin or superadmin)
        if request.user.profile.user_type == 'superadmin' or request.user.profile.user_type == 'admin':
            return True
        return False
    
class IsSuperAdmin(BasePermission):
    """
    Custom permission to allow only superadmins to access the create and bulk_upload actions.
    """
    def has_permission(self, request, view):
        # Check if the user is a superuser
        if not request.user.is_authenticated:
            return False
        # Check for user type (admin or superadmin)
        if request.user.profile.user_type == 'superadmin':
            return True
        return False
    



class CanCreateOrDeletePaymentStatus(BasePermission):
    """
    Only allow users with specific permissions to create or delete PaymentStatus.
    """
    def has_permission(self, request, view):
        # Restrict creation permission
        if view.action == 'create':
            return request.user.has_perm('orders.add_payment_status')
        
        # Restrict delete permission
        if view.action == 'destroy':
            return request.user.has_perm('orders.delete_payment_status')

        # Allow other actions (e.g., list, retrieve, update) by default
        return True
    


class CanCreateAndDeleteCustomerState(BasePermission):
    """
    Allow creation, bulk upload, and deletion only for users with the 'add_customer_state' and 'delete_customer_state' permissions.
    """
    def has_permission(self, request, view):
        if view.action in ['create', 'bulk_upload']:
            return request.user.has_perm('orders.add_customer_state')  # Replace 'app' with your app name

        if view.action == 'destroy':  # For delete action
            return request.user.has_perm('orders.delete_customer_state')  # Replace 'app' with your app name

        return True
    

class IsAuthenticatedOrReadOnly(BasePermission):
    """
    Custom permission to allow read-only access for unauthenticated users
    and full access for authenticated users.
    """

    def has_permission(self, request, view):
        # Allow read-only methods (SAFE_METHODS: GET, HEAD, OPTIONS) for anyone
        if request.method in SAFE_METHODS:
            return True
        
        # Allow write methods only for authenticated users
        return request.user and request.user.is_authenticated
    

class CanEditOwnCompanyPermission(BasePermission):
    def has_object_permission(self, request, view, obj):
        return request.user.has_perm("accounts.can_edit_own_company") or obj.created_by == request.user
    


class CanManageOwnCompanyPermission(BasePermission):
    def has_object_permission(self, request, view, obj):
        return request.user.has_perm("accounts.can_manage_own_company") or obj.created_by == request.user


from rest_framework.permissions import BasePermission

class HasPermission(BasePermission):
    def __init__(self, permission):
        self.permission = permission

    def has_permission(self, request, view):
        # Implement your logic to check if the user has the specific permission
        return request.user.has_perm( self.permission)  # Your permission logic
