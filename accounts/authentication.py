from rest_framework.authentication import TokenAuthentication
from rest_framework.exceptions import AuthenticationFailed

from accounts.models import ExpiringToken
from datetime import timedelta
from django.utils import timezone

# class CustomTokenAuthentication(TokenAuthentication):
#     def authenticate_credentials(self, key):
#         user, token = super().authenticate_credentials(key)
        
#         # Check if the user is active
#         if user.profile.status != 1:
#             raise AuthenticationFailed("This account is disabled. Please contact support.")
        
#         if not hasattr(user.profile, 'company') or user.profile.company is None:
#             pass
#         elif user.profile.company and user.profile.company.status !=1 and user.profile.user_type != 'superadmin':  # Assuming `company` is a related model
#             raise AuthenticationFailed("Your company is disabled, Please contact support.")
#         return user, token


class CustomTokenAuthentication(TokenAuthentication):
    model = ExpiringToken

    def authenticate_credentials(self, key):
        try:
            token = self.model.objects.select_related('user').get(key=key)
        except self.model.DoesNotExist:
            raise AuthenticationFailed('Invalid token.')

        if not token.user.is_active:
            raise AuthenticationFailed('User inactive or deleted.')

        if timezone.now() - token.last_used > timedelta(minutes=45):
            token.delete()
            raise AuthenticationFailed('Token expired due to inactivity.')

        token.last_used = timezone.now()
        token.save(update_fields=['last_used'])

        return (token.user, token)