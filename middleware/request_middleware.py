import threading

_request_local = threading.local()

class RequestMiddleware:
    """
    Middleware to store the request object globally using thread-local storage.
    This allows access to the request object anywhere in the application.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Store the request in thread-local storage
        _request_local.request = request
        response = self.get_response(request)
        return response

def get_request():
    """
    Returns the current request object from thread-local storage.
    If no request is stored, returns None.
    """
    return getattr(_request_local, "request", None)



import re
import json
from django.utils.deprecation import MiddlewareMixin

class MaskNumberMiddleware(MiddlewareMixin):
    MASK_PATTERN = r'\+?\d{10,15}'  # Matches phone numbers (10-15 digits, optional '+')
    EXCLUDED_KEYS = {"order_wayBill", "awb_code"}
    def mask_number(self, number):
        """Masks the middle part of a number while keeping country code visible."""
        if number.startswith("+"):
            return number[:4] + "******" + number[-1:]
        return number[:4] + "******" + number[-1:]

    def mask_numbers_in_data(self, data):
        """Recursively searches for numbers to mask in JSON response."""
        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, str) and re.fullmatch(self.MASK_PATTERN, value):
                    if key not in self.EXCLUDED_KEYS:  # Skip masking for excluded keys
                            
                            data[key] = self.mask_number(value)
                else:
                    data[key] = self.mask_numbers_in_data(value)
        elif isinstance(data, list):
            return [self.mask_numbers_in_data(item) for item in data]
        return data

    def process_response(self, request, response):
        """Modifies the response before sending it to the user."""
        if not request.user.is_authenticated:
            return response
        if request.user.profile.user_type == 'agent':
            if request.user.has_perm('accounts.view_number_masking_others'):
                # Ensure the response is JSON
                if response.has_header('Content-Type') and 'application/json' in response['Content-Type']:
                    try:
                        # Decode response content
                        content = response.content.decode('utf-8')  # Ensure proper decoding
                        json_data = json.loads(content)  # Convert to JSON
                        masked_content = self.mask_numbers_in_data(json_data)  # Mask numbers
                        response.content = json.dumps(masked_content)  # Convert back to JSON
                        response['Content-Length'] = str(len(response.content))  # Fix content length
                    except (json.JSONDecodeError, UnicodeDecodeError):
                        pass  # Ignore if response is not JSON or has encoding issues

        return response



# class MaskNumberMiddleware(MiddlewareMixin):
#     MASK_PATTERN = r'\+?\d{10,15}'  # Matches phone numbers (10-15 digits, optional '+')
#     EXCLUDED_KEYS = {"order_wayBill", "awb_code"}  # Keys that should NOT be masked

#     def mask_number(self, number):
#         """Masks the middle part of a phone number while keeping country code visible."""
#         if number.startswith("+"):
#             return number[:4] + "****" + number[-4:]
#         return number[:3] + "****" + number[-3:]

#     def mask_numbers_in_data(self, data, parent_key=None):
#         """Recursively searches for numbers to mask in JSON response, skipping excluded keys."""
#         if isinstance(data, dict):
#             return {key: self.mask_numbers_in_data(value, key) for key, value in data.items()}
#         elif isinstance(data, list):
#             return [self.mask_numbers_in_data(item, parent_key) for item in data]
#         elif isinstance(data, str) and re.fullmatch(self.MASK_PATTERN, data):
#             if parent_key not in self.EXCLUDED_KEYS:  # Skip masking for excluded keys
#                 return self.mask_number(data)
#         return data

#     def process_response(self, request, response):
#         """Modifies the response before sending it to the user."""
#         if not request.user.is_authenticated:
#             return response  # Skip processing if the user is not authenticated.

#         if not request.user.has_perm('app.view_full_number'):
#             # Ensure the response is JSON
#             if response.has_header('Content-Type') and 'application/json' in response['Content-Type']:
#                 try:
#                     content = response.content.decode('utf-8')  # Decode response
#                     json_data = json.loads(content)  # Convert to JSON
#                     masked_content = self.mask_numbers_in_data(json_data)  # Mask numbers
#                     response.content = json.dumps(masked_content)  # Convert back to JSON
#                     response['Content-Length'] = str(len(response.content))  # Fix content length
#                 except (json.JSONDecodeError, UnicodeDecodeError):
#                     pass  # Ignore if response is not JSON or has encoding issues

#         return response
