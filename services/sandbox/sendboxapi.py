import requests
from django.conf import settings
from rest_framework.response import Response

from superadmin_assets.models import SandboxCredentials

class SandboxAPIService:
    def __init__(self, api_key=None, api_secret=None, api_host=None):
        active_credential = SandboxCredentials.objects.filter(is_active=True).first()

        # If no credentials are provided in the constructor, use the active credentials or fallback to settings
        self.api_key = api_key or (active_credential.api_key if active_credential else settings.SANDBOX_API_KEY)
        self.api_secret = api_secret or (active_credential.api_secret if active_credential else settings.SANDBOX_API_SECRET)
        self.base_url = api_host or (active_credential.api_host if active_credential else settings.SANDBOX_HOST)
        # self.api_key = api_key or settings.SANDBOX_API_KEY
        # self.api_secret = api_secret or settings.SANDBOX_API_SECRET
        # self.base_url = settings.SANDBOX_HOST
        self.token = None  # Add this line to store the token
        endpoint = "/authenticate"
        auth_data, auth_status_code = self._make_request("post", endpoint,type="authorization")
        if auth_status_code == 200:
            # Store the token if authentication is successful
            self.token = auth_data.get('access_token')
    def authenticate(self):
        """Authenticate and get the token"""
        endpoint = "/authenticate"
        auth_data, auth_status_code = self._make_request("post", endpoint,type="authorization")
        if auth_status_code == 200:
            # Store the token if authentication is successful
            self.token = auth_data.get('access_token')  # Assuming 'token' is the field in the response
        return auth_data, auth_status_code

    def _get_api_headers(self):
        """Headers for API requests after obtaining the token"""
        if not self.token:
            raise ValueError("Token not found. Please authenticate first.")
        return {
            "Authorization": self.token,  # Use the token here
            "x-api-key": self.api_key,
            # "x-api-secret": self.api_secret,
            "x-api-version": "2",
            "Content-Type": "application/json",
            "x-accept-cache": "true"
            
        }
    def _get_headers(self):
        return {
             # Use the token here
            "x-api-key": self.api_key,
            "x-api-secret": self.api_secret,
            "x-api-version": "2",
            "Content-Type": "application/json",
            "x-accept-cache": "true"
        }
    # def _get_api_headers(self):
    #     """Headers for API requests after obtaining the token"""
    #     if not self.token:
    #         raise ValueError("Token not found. Please authenticate first.")
        
    #     return {
    #         "Authorization": f"Bearer {self.token}",  # JWT token or access token
    #         "x-api-key": self.api_key,                 # Public API key
    #         "x-api-version": "1",                      # API version
    #         "Content-Type": "application/json",        # Content type
    #         "x-accept-cache": "true"                   # Optional cache headers
    #     }

    def _make_request(self, method, endpoint, data=None,type=None):
        """Helper method to make HTTP requests"""
        url = f"{self.base_url}{endpoint}"
        if type is None:
            headers = self._get_api_headers()  # Get API headers with token
        else:
            headers = self._get_headers() # Get API headers with
        try:
            # Handle different HTTP methods (GET, POST, PUT, DELETE)
            if method.lower() == "get":
                response = requests.get(url, headers=headers, params=data)
            elif method.lower() == "post":
                response = requests.post(url, headers=headers, json=data)
            elif method.lower() == "put":
                response = requests.put(url, headers=headers, json=data)
            elif method.lower() == "delete":
                response = requests.delete(url, headers=headers, data=data)
            else:
                raise ValueError("Invalid HTTP method")
            # Check if the response status code is 2xx (success)
            if response.status_code >= 200 and response.status_code < 300:
                return response.json(), response.status_code
            else:
                return {"error": f"API call failed with status code {response.status_code}"}, response.status_code

        except requests.RequestException as e:
            # Handle network or connection errors
            return {"error": f"Request failed: {str(e)}"}, 500

    # Authentication API
    # def authenticate(self):
    #     """Authenticate and get token"""
    #     endpoint = "/authenticate"
    #     response_data, status_code = self._make_request("post", endpoint)
    #     if status_code == 200:
    #         self.token = response_data.get("token")  # Store the token
    #     return response_data, status_code

    def refresh_token(self, refresh_token):
        """Refresh JWT token"""
        
        endpoint = "/api/auth/token/refresh/"
        data = {"refresh": refresh_token}
        return self._make_request("post", endpoint, data)

    # KYC APIs
    def aadhaar_verification(self, aadhaar_number):
        """Verify Aadhaar number"""
        endpoint = f"/kyc/aadhaar/{aadhaar_number}"
        return self._make_request("get", endpoint)
    
    def aadhaar_verify_otp(self, otp, reference_id):
        """Verify OTP and retrieve Aadhaar details"""
        endpoint = f"/kyc/aadhaar/okyc/otp/verify"
        data = {
            "@entity": "in.co.sandbox.kyc.aadhaar.okyc.request",
            "reference_id": reference_id,
            "otp": otp
        }
        response = self._make_request("post", endpoint, data=data)
        return response
    def aadhaar_generate_otp(self, aadhaar_number):
        """Generate OTP for Aadhaar verification"""
        endpoint = f"/kyc/aadhaar/okyc/otp"
        data = {
            "aadhaar_number": aadhaar_number,
            "reason":"For user kyc",
            "@entity": "in.co.sandbox.kyc.aadhaar.okyc.otp.request",
             "consent": "Y"
        }

        response = self._make_request("post", endpoint, data=data)
        return response
        # if response.get('status') == 'success':
        #     return {
        #         "status": "success",
        #         "otp": response.get('otp')
        #     }
        # else:
        #     return {
        #         "status": "error",
        #         "message": response.get("message", "Failed to generate OTP")
        #     }
    def bank_ifsc_verification(self, ifsc_code):
        """Verify IFSC code"""
        endpoint = f"/bank/ifsc/{ifsc_code}"
        return self._make_request("get", endpoint)

    def bank_account_verification_penny_drop(self, account_number):
        """Verify bank account using Penny-Drop method"""
        endpoint = f"/bank/account-verification/penny-drop/{account_number}"
        return self._make_request("get", endpoint)

    def bank_account_verification_penny_less(self, account_number):
        """Verify bank account using Penny-Less method"""
        endpoint = f"/bank/account-verification/penny-less/{account_number}"
        return self._make_request("get", endpoint)

    # MCA APIs
    # def pan_verification(self, pan_number):
    #     """Verify PAN number"""
    #     endpoint = f"/mca/pan/{pan_number}"
    #     return self._make_request("get", endpoint)

    def search_tan(self, tan_number):
        """Search for TAN number"""
        endpoint = f"/mca/search-tan/{tan_number}"
        return self._make_request("get", endpoint)

    def search_gstin(self, gstin):
        """Search for GSTIN number"""
        endpoint = f"/gst/compliance/public/gstin/search"
        return self._make_request("post", endpoint, data={"gstin": gstin})

    # Income Tax APIs
    def income_tax_form16(self, user_data):
        """Get Form 16 data"""
        endpoint = "/income-tax/form-16"
        return self._make_request("post", endpoint, data = user_data)

    def tax_pl_report(self, securities_data):
        """Get Tax P&L Report"""
        endpoint = "/tax-pl"
        return self._make_request("post", endpoint, data=securities_data)

    # GST APIs
    def gst_search_gstin(self, gstin):
        """Search GSTIN in GST Public API"""
        endpoint = "/gst/public/gstin/search"
        return self._make_request("post", endpoint, data = {"gstin": gstin})

    def track_gst_returns(self, gstin):
        """Track GST Returns"""
        endpoint = "/gst/public/gstin/track"
        return self._make_request("post", endpoint, data = {"gstin": gstin})

    # TDS APIs
    def verify_pan_details(self, pan_number):
        """Verify PAN Details in TDS Compliance Check"""
        endpoint = f"/tds/verify-pan/{pan_number}"
        return self._make_request("get", endpoint)

    def tds_calculator(self, payment_type, amount):
        """Calculate TDS for Non-Salary or Salary payments"""
        endpoint = "/tds/calculator"
        data = {"payment_type": payment_type, "amount": amount}
        return self._make_request("post", endpoint, data=data)
    
    def search_gst_by_pan(self,pan_number,gst_state_code):
        endpoint = "/gst/compliance/public/pan/search?state_code="+gst_state_code
        data = {"pan": pan_number}
        return self._make_request("post", endpoint, data=data)
    
    def pan_verification(self,pan_number, name_as_per_pan, date_of_birth):
        """Verify PAN number"""
        endpoint = "/kyc/pan/verify"
        data = {
            "@entity": "in.co.sandbox.kyc.pan_verification.request",
            "pan": pan_number,
            "name_as_per_pan": name_as_per_pan,
            "date_of_birth": date_of_birth,
            "consent": "Y",
            "reason": "For onboarding customers"
        }
        response = self._make_request("post", endpoint, data=data)
        return response