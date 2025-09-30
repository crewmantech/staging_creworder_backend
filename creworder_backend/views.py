from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from rest_framework.exceptions import AuthenticationFailed
from dj_rest_auth.views import LoginView
# from rest_framework.authtoken.models import Token
from accounts.models import ExpiringToken as Token
from rest_framework.response import Response
from accounts.models import AllowedIP, Branch, Company,User
from kyc.models import OTPModel
from emailsetup.models import AgentAuthentication
from django.db.models import Q
from django.shortcuts import render
from rest_framework import status
from kyc.views import send_otp_to_email,send_otp_to_number
from django.contrib.auth import authenticate

def welcome(request):
    return render(request, 'home.html')

class CustomLoginView(LoginView):
    def post(self, request, *args, **kwargs):
        # First, check if the user exists
        client_ip = request.data.get('ip')
        
        # Get username and password from request
        username = request.data.get('username')
        password = request.data.get('password')
        
        if not username or not password:
            return Response({
                "success": False,
                "message": "Username and password are required."
            }, status=status.HTTP_400_BAD_REQUEST)
            
        # Try to authenticate user first
        user = authenticate(username=username, password=password)
        
        if not user:
            return Response({
                "success": False,
                "message": "Invalid credentials."
            }, status=status.HTTP_401_UNAUTHORIZED)
            
        username = user.username
        
        # Check if the user's account is disabled
        if user.profile.status != 1:
            raise AuthenticationFailed("Your account is disabled.")
        
        # Check if the company is disabled (if the user belongs to a company)
        if not hasattr(user.profile, 'company') or user.profile.company is None:
            pass
        elif user.profile.company and user.profile.company.status !=1 and user.profile.user_type != 'superadmin':
            raise AuthenticationFailed("Your company is disabled, you cannot log in.")

        # Check if user is already logged in by checking for active token
        existing_token = Token.objects.filter(user=user).first()
        if user.profile.user_type == "agent":
            has_ip_permission = user.has_perm('accounts.login_allow_Ip_others')

            if has_ip_permission:  # If user does not have permission, enforce IP check
                allowed_ip = AllowedIP.objects.filter(
                    Q(branch=user.profile.branch) | Q(company=user.profile.company),
                    ip_address=client_ip
                ).exists()
                if not allowed_ip:
                    return Response({
                        "success": False,
                        "message": f"Access denied: IP {client_ip} is not allowed.Please contact to admin!"
                    }, status=status.HTTP_400_BAD_REQUEST)
        if existing_token:
            # If user is admin/super admin, send OTP for re-login
            if user.profile.user_type in ["superadmin", "admin"]:
                # Generate and send OTP
                mobile = user.profile.contact_no
                email = user.email
                mobile = str(mobile)[-10:]
                otp_instance = OTPModel.create_otp(mobile,username)

                # Send OTP
                email_success = send_otp_to_email(email, otp_instance.otp,name=user.first_name if user else 'User') if email else False
                sms_success = send_otp_to_number(mobile, otp_instance.otp, name=user.first_name if user else 'User') if mobile else False


                # Generate response message based on success/failure
                if email_success and sms_success:
                    message = "OTP sent successfully to both email and mobile."
                elif email_success:
                    message = "OTP sent successfully to email."
                elif sms_success:
                    message = "OTP sent successfully to mobile."
                else:
                    return Response({"success": False, "message": "Failed to send OTP. Please try again."},
                                    status=status.HTTP_400_BAD_REQUEST)

                return Response({
                    "success": True, 
                    "message": message, 
                    "data": {
                        "mobile": mobile, 
                        "email": username,
                        "is_already_logged_in": True
                    }
                }, status=status.HTTP_200_OK)
            

        # Check if user has two-way authentication enabled
        if user.profile.two_way_authentication and user.profile.user_type in ["superadmin", "admin"]:
            mobile = user.profile.contact_no
            email = user.email
            mobile = str(mobile)[-10:]
            otp_instance = OTPModel.create_otp(mobile,username)
            # Send OTP
            email_success = send_otp_to_email(email, otp_instance.otp,name=user.first_name if user else 'User') if email else False
            sms_success = send_otp_to_number(mobile, otp_instance.otp, name=user.first_name if user else 'User') if mobile else False


            # Generate response message based on success/failure
            if email_success and sms_success:
                message = "OTP sent successfully to both email and mobile."
            elif email_success:
                message = "OTP sent successfully to email."
            elif sms_success:
                message = "OTP sent successfully to mobile."
            else:
                return Response({"success": False, "message": "Failed to send OTP. Please try again."}, 
                                status=status.HTTP_400_BAD_REQUEST)

            return Response({"success": True, "message": message, "data": {"mobile": mobile, "email": username}}, 
                            status=status.HTTP_200_OK)
        
        if user.profile.user_type == "agent" and user.has_perm('accounts.allow_otp_login_others'):
            auth_data = AgentAuthentication.objects.filter(
                Q(branch=user.profile.branch) | Q(company=user.profile.company)
            ).first()

            if not auth_data:  # If no authentication data is found
                return Response({"success": False, "message": "Authentication data not found.Please contact to admin!"}, 
                                status=status.HTTP_400_BAD_REQUEST)

            # If auth_data exists, retrieve phone and email
            mobile = auth_data.phone
            email = auth_data.email
            mobile = str(mobile)[-10:]
            otp_instance = OTPModel.create_otp(mobile,username)
            # Send OTP
            email_success = send_otp_to_email(email, otp_instance.otp,name=user.first_name if user else 'User') if email else False
            sms_success = send_otp_to_number(mobile, otp_instance.otp, name=user.first_name if user else 'User') if mobile else False


            # Generate response message based on success/failure
            if email_success and sms_success:
                message = "OTP sent successfully to both email and mobile."
            elif email_success:
                message = "OTP sent successfully to email."
            elif sms_success:
                message = "OTP sent successfully to mobile."
            else:
                return Response({"success": False, "message": "Failed to send OTP. Please try again."}, 
                                status=status.HTTP_400_BAD_REQUEST)

            return Response({"success": True, "message": message, "data": {"mobile": mobile, "email": username}}, 
                            status=status.HTTP_200_OK)
       
        

        # For users who don't need OTP verification, generate token directly
        try:
            # Delete any existing token
            Token.objects.filter(user=user).delete()
            
            # Create new token
            token = Token.objects.create(user=user)
            
            return Response({
                "success": True,
                "message": "Login successful!",
                "key": token.key,
                    
                
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            # logger.error(f"Token generation error: {str(e)}")
            return Response({
                "success": False,
                "message": "Error generating authentication token."
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

from rest_framework.views import APIView
from django.contrib.auth import login

class VerifyOTPView(APIView):
    def post(self, request, *args, **kwargs):
        phone = request.data.get("mobile")
        email = request.data.get("email")
        otp = request.data.get("otp")

        if not all([phone, email, otp]):
            return Response({
                "success": False,
                "message": "Phone, email and OTP are required."
            }, status=status.HTTP_400_BAD_REQUEST)

        # Validate OTP
        otp_instance = OTPModel.objects.filter(phone_number=phone, otp=otp,username=email).first()
        if not otp_instance:
            return Response({
                "success": False,
                "message": "Invalid or expired OTP."
            }, status=status.HTTP_400_BAD_REQUEST)

        # Authenticate user
        user = User.objects.filter(username=email).first()
        if not user:
            return Response({
                "success": False,
                "message": "User not found."
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Delete any existing token
            Token.objects.filter(user=user).delete()
            otp_instance.delete()
            # Create new token
            token = Token.objects.create(user=user)
            
            return Response({
                "success": True,
                "message": "OTP verified, login successful!",
                "key": token.key,
                "user_id": user.id,
                "username": user.username,
                "email": user.email,
                "user_type": user.profile.user_type
                
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            # logger.error(f"Token generation error: {str(e)}")
            return Response({
                "success": False,
                "message": "Error generating authentication token."
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    

class LogoutView(APIView):
    from rest_framework.permissions import IsAuthenticated
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        token = Token.objects.filter(user=user).first()
        if token:
            token.delete()
            return Response({"success": True, "message": "Logout successful."})
        return Response({"success": False, "message": "Token not found."}, status=400)