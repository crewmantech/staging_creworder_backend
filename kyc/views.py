from datetime import datetime, timedelta
import random
import re
from venv import logger
from django.template.loader import render_to_string
import requests
from staging_creworder_backend import settings
from kyc.models import KYC, GSTState, OTPModel
from kyc.serializers import GSTStateSerializer, KYCSerializer, OTPSerializer
from services.email.email_service import send_email
from services.sandbox.sendboxapi import SandboxAPIService
from rest_framework import status,viewsets
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser
import csv
import io
from rest_framework.permissions import IsAuthenticated

from superadmin_assets.models import SMSCredentials

class AadhaarVerificationView(APIView):
    """Verify Aadhaar number"""

    def post(self, request):
        aadhaar_number = request.data.get("aadhaar_number")
        if not aadhaar_number:
            return Response({"error": "Aadhaar number is required"}, status=status.HTTP_400_BAD_REQUEST)

        api_service = SandboxAPIService()
        data, status_code = api_service.aadhaar_verification(aadhaar_number)
        return Response(data, status=status_code)


class BankIFSCVerificationView(APIView):
    """Verify IFSC Code"""

    def post(self, request):
        ifsc_code = request.data.get("ifsc_code")
        if not ifsc_code:
            return Response({"error": "IFSC Code is required"}, status=status.HTTP_400_BAD_REQUEST)

        api_service = SandboxAPIService()
        data, status_code = api_service.bank_ifsc_verification(ifsc_code)
        return Response(data, status=status_code)


class BankAccountVerificationPennyDropView(APIView):
    """Verify Bank Account (Penny Drop)"""

    def post(self, request):
        account_number = request.data.get("account_number")
        if not account_number:
            return Response({"error": "Account number is required"}, status=status.HTTP_400_BAD_REQUEST)

        api_service = SandboxAPIService()
        data, status_code = api_service.bank_account_verification_penny_drop(account_number)
        return Response(data, status=status_code)


class BankAccountVerificationPennyLessView(APIView):
    """Verify Bank Account (Penny Less)"""

    def post(self, request):
        account_number = request.data.get("account_number")
        if not account_number:
            return Response({"error": "Account number is required"}, status=status.HTTP_400_BAD_REQUEST)

        api_service = SandboxAPIService()
        data, status_code = api_service.bank_account_verification_penny_less(account_number)
        return Response(data, status=status_code)


class PANVerificationView(APIView):
    """Verify PAN Number"""

    def post(self, request):
        pan_number = request.data.get("pan_number")
        name_as_per_pan = request.data.get("name_as_per_pan")
        date_of_birth = request.data.get("date_of_birth")
        if not pan_number and not re.match(r'^[A-Z]{5}[0-9]{4}[A-Z]{1}$', pan_number):
            return Response({"error": "PAN number is required"}, status=status.HTTP_400_BAD_REQUEST)
        if not name_as_per_pan:
            return Response({"error": "Name As Per PAN is required"}, status=status.HTTP_400_BAD_REQUEST)
        if not date_of_birth:
            return Response({"error": "date of birth is required"}, status=status.HTTP_400_BAD_REQUEST)
        api_service = SandboxAPIService()
        data, status_code = api_service.pan_verification(pan_number,name_as_per_pan, date_of_birth)
        res=data.get('data',{})
        pan_status = data.get("data", {}).get("status")
        name_match = data.get("data", {}).get("name_as_per_pan_match")
        dob_match = data.get("data", {}).get("date_of_birth_match")

        # Check if all conditions are valid
        if pan_status == "valid" and name_match and dob_match:
            return Response({"success": True, "message": "PAN verification successful","data":res}, status=status.HTTP_200_OK)
        else:
            return Response({"success": False, "message": "PAN verification failed"}, status=status.HTTP_400_BAD_REQUEST)
        return Response(data, status=status_code)


class SearchTANView(APIView):
    """Search TAN Number"""

    def post(self, request):
        tan_number = request.data.get("tan_number")
        if not tan_number:
            return Response({"error": "TAN number is required"}, status=status.HTTP_400_BAD_REQUEST)

        api_service = SandboxAPIService()
        data, status_code = api_service.search_tan(tan_number)
        return Response(data, status=status_code)


class SearchGSTINView(APIView):
    """Search GSTIN Number"""

    def post(self, request):
        gstin = request.data.get("gstin")
        if not gstin:
            return Response({"error": "GSTIN is required"}, status=status.HTTP_400_BAD_REQUEST)

        api_service = SandboxAPIService()
        data, status_code = api_service.search_gstin(gstin)
        return Response(data, status=status_code)


class IncomeTaxForm16View(APIView):
    """Retrieve Income Tax Form 16"""

    def post(self, request):
        user_data = request.data
        api_service = SandboxAPIService()
        data, status_code = api_service.income_tax_form16(user_data)
        return Response(data, status=status_code)


class TaxPLReportView(APIView):
    """Retrieve Tax P&L Report"""

    def post(self, request):
        securities_data = request.data
        api_service = SandboxAPIService()
        data, status_code = api_service.tax_pl_report(securities_data)
        return Response(data, status=status_code)


class GSTSearchGSTINView(APIView):
    """Search GSTIN (Public GST API)"""

    def post(self, request):
        gstin = request.data.get("gstin")
        if not gstin:
            return Response({"error": "GSTIN is required"}, status=status.HTTP_400_BAD_REQUEST)

        api_service = SandboxAPIService()
        data, status_code = api_service.gst_search_gstin(gstin)
        return Response(data, status=status_code)


class TrackGSTReturnsView(APIView):
    """Track GST Returns"""

    def post(self, request):
        gstin = request.data.get("gstin")
        if not gstin:
            return Response({"error": "GSTIN is required"}, status=status.HTTP_400_BAD_REQUEST)

        api_service = SandboxAPIService()
        data, status_code = api_service.track_gst_returns(gstin)
        return Response(data, status=status_code)


class VerifyPANDetailsView(APIView):
    """Verify PAN Details in TDS Compliance"""

    def post(self, request):
        pan_number = request.data.get("pan_number")
        if not pan_number:
            return Response({"error": "PAN number is required"}, status=status.HTTP_400_BAD_REQUEST)

        api_service = SandboxAPIService()
        data, status_code = api_service.verify_pan_details(pan_number)
        return Response(data, status=status_code)


class TDSCalculatorView(APIView):
    """Calculate TDS for Salary or Non-Salary Payments"""

    def post(self, request):
        payment_type = request.data.get("payment_type")
        amount = request.data.get("amount")

        if not payment_type or not amount:
            return Response({"error": "Both payment type and amount are required"}, status=status.HTTP_400_BAD_REQUEST)

        api_service = SandboxAPIService()
        data, status_code = api_service.tds_calculator(payment_type, amount)
        return Response(data, status=status_code)
    


class KYCViewSet(viewsets.ModelViewSet):
    queryset = KYC.objects.all()
    serializer_class = KYCSerializer

    def get_queryset(self):
        company_id = self.request.query_params.get('company_id', None)
        if company_id is not None:
            return KYC.objects.filter(company_id=company_id)
        return KYC.objects.all()

    @action(detail=False, methods=['put'])
    def update_kyc(self, request):
        """Update text fields, file fields, and/or verification_status in a KYC entry based on company_id."""
        company_id = request.data.get('company_id')  # Get company ID from request

        if not company_id:
            return Response({'error': 'Company ID is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            kyc = KYC.objects.get(company_id=company_id)  # Fetch KYC using company_id
        except KYC.DoesNotExist:
            return Response({'error': 'KYC entry not found for this company'}, status=status.HTTP_404_NOT_FOUND)

        updated_data = {}
        updated_files = {}

        # ✅ Update verification_status if provided
        verification_status = request.data.get('verification_status')
        if verification_status:
            if verification_status not in ['PENDING', 'COMPLETED', 'REJECTED']:
                return Response({'error': 'Invalid status'}, status=status.HTTP_400_BAD_REQUEST)
            kyc.verification_status = verification_status
            updated_data['verification_status'] = verification_status

        # ✅ Update text fields dynamically
        allowed_text_fields = [
            'select_kyc_type', 'pan_card_number', 'coi_number',
            'document_type', 'document_id', 'document_name',
            'gst_number', 'tan_number','status','e_kyc',"step_1","step_2","step_3","adhar_number","pan_card_name","pan_dob",'adhar_number',"gst_state_code"
        ]
        for field in allowed_text_fields:
            if field in request.data:
                setattr(kyc, field, request.data[field])
                updated_data[field] = request.data[field]

        # ✅ Update file fields dynamically
        allowed_file_fields = [
            'pan_card', 'upload_adhar', 'partnership_deed',
            'coi_image', 'rent_agriment', 'electricity_bill',"gst_certificate","upload_digital_sign"
        ]
        for field in allowed_file_fields:
            if field in request.FILES:
                setattr(kyc, field, request.FILES[field])
                updated_files[field] = request.FILES[field].name

        # ✅ Save only if updates were made
        if updated_data or updated_files:
            kyc.save()
            return Response({
                'status': 'KYC updated successfully',
                'updated_fields': updated_data,
                'updated_files': updated_files
            }, status=status.HTTP_200_OK)

        return Response({'error': 'No valid fields provided for update'}, status=status.HTTP_400_BAD_REQUEST)
    def list(self, request, *args, **kwargs):
        """Retrieve all KYC records with filtering support"""
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            "status": "success",
            "count": queryset.count(),
            "kyc_records": serializer.data
        }, status=status.HTTP_200_OK)


class AadhaarOTPVerificationView(APIView):
    """Generate and Verify Aadhaar OTP"""

    def post(self, request):
        action = request.data.get("action")
        aadhaar_number = request.data.get("aadhaar_number")
        otp = request.data.get("otp")
        reference_id = request.data.get("reference_id")
        # Check for missing parameters
        # if not aadhaar_number:
        #     return Response({"error": "Aadhaar Number is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        if action == "generate_otp":
            # If action is to generate OTP
            return self.generate_otp(aadhaar_number)
        
        elif action == "verify_otp":
            # If action is to verify OTP
            if not otp:
                return Response({"error": "OTP is required for verification"}, status=status.HTTP_400_BAD_REQUEST)
            return self.verify_otp(otp,reference_id)
        
        else:
            return Response({"error": "Invalid action. Use 'generate_otp' or 'verify_otp'"}, status=status.HTTP_400_BAD_REQUEST)

    def generate_otp(self, aadhaar_number):
        """Generate OTP for Aadhaar verification"""
        api_service = SandboxAPIService()
        data, status_code = api_service.aadhaar_generate_otp(aadhaar_number)

        return Response(data, status=status_code)

    def verify_otp(self, otp,reference_id):
        """Verify OTP and retrieve Aadhaar details"""
        api_service = SandboxAPIService()
        data, status_code = api_service.aadhaar_verify_otp( otp,reference_id)

        return Response(data, status=status_code)
    

class GSTAndPANVerificationView(APIView):
    """Search GST by PAN and verify PAN number"""

    def post(self, request):
        pan_number = request.data.get("pan_number")
        # gst_number = request.data.get("gst_number")
        gst_state_code = request.data.get("gst_state_code")

        if not pan_number:
            return Response({"error": "PAN number is required"}, status=status.HTTP_400_BAD_REQUEST)
        if not gst_state_code:
            return Response({"error": "GST state code is required"}, status=status.HTTP_400_BAD_REQUEST)

        api_service = SandboxAPIService()

        # Search GST by PAN
        gst_data, gst_status_code = api_service.search_gst_by_pan(pan_number, gst_state_code)
        # gst_data, gst_status_code = api_service.search_gstin(gst_number)

        try:
            # gstin_1 = gst_data1.get('data', [{}])[0].get('gstin')
            # gstin_2 = gst_data.get('data', {}).get('data', {}).get('gstin')
            return Response({"status": "success", "message": "GSTINs match", "gst_data": gst_data}, status=status.HTTP_200_OK)

            # if not gstin_1 or not gstin_2:
            #     return Response({"error": "Invalid or missing GSTIN data"}, status=status.HTTP_400_BAD_REQUEST)

            # if gstin_1 == gstin_2:
                # return Response({"status": "success", "message": "GSTINs match", "gstin": gstin_1}, status=status.HTTP_200_OK)
            # else:
                # return Response({"status": "error", "message": "GSTINs do not match"}, status=status.HTTP_400_BAD_REQUEST)

        except (KeyError, IndexError, TypeError) as e:
            return Response({"error": f"Data parsing error: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        

class GSTStateViewSet(viewsets.ModelViewSet):
    queryset = GSTState.objects.all()
    serializer_class = GSTStateSerializer

    # Handle adding GST state with JSON payload
    def create(self, request, *args, **kwargs):
        state_name = request.data.get('state_name')
        state_code = request.data.get('state_code')

        if not state_name or not state_code:
            return Response({'error': 'State name and state code are required'}, status=status.HTTP_400_BAD_REQUEST)

        # Check if state with the same code already exists
        if GSTState.objects.filter(state_code=state_code).exists():
            return Response({"error": "State with this state_code already exists"}, status=status.HTTP_400_BAD_REQUEST)

        # Create new state entry
        new_state = GSTState.objects.create(state_name=state_name, state_code=state_code)
        return Response({
            "status": "success",
            "message": "GST State added successfully",
            "data": {
                "state_name": new_state.state_name,
                "state_code": new_state.state_code
            }
        }, status=status.HTTP_201_CREATED)

    # Custom action for handling CSV file upload
    @action(detail=False, methods=['post'], parser_classes=[MultiPartParser])
    def upload_csv(self, request):
        if 'csv_file' not in request.FILES:
            return Response({"error": "No file provided."}, status=status.HTTP_400_BAD_REQUEST)

        csv_file = request.FILES['csv_file']
        if not csv_file.name.endswith('.csv'):
            return Response({"error": "Only CSV files are allowed"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            csv_data = csv.reader(io.StringIO(csv_file.read().decode('utf-8')))
            header = next(csv_data)  # Skip the header row
            added_states = []

            for row in csv_data:
                if len(row) < 2:
                    continue  # Skip rows with insufficient data

                state_name, state_code = row
                # Check if the state with the same code already exists
                if GSTState.objects.filter(state_code=state_code).exists():
                    continue  # Skip if state with this state_code exists

                # Add the new state to the database
                new_state = GSTState.objects.create(state_name=state_name, state_code=state_code)
                added_states.append({
                    "state_name": new_state.state_name,
                    "state_code": new_state.state_code
                })

            if added_states:
                return Response({
                    "status": "success",
                    "message": f"{len(added_states)} GST States added successfully",
                    "data": added_states
                }, status=status.HTTP_201_CREATED)
            else:
                return Response({
                    "error": "No new states were added. Either they already exist or the CSV was empty."
                }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        


def send_otp_to_number(number, otp, purpose="verify", custom_message=None,name='User'):
    active_sms_credential = SMSCredentials.objects.filter(is_active=True).first()
    sms_api_key = active_sms_credential.sms_api_key if active_sms_credential else settings.SMS_API_KEY
    sms_sender_id = active_sms_credential.sms_sender_id if active_sms_credential else settings.SMS_SENDER_ID
    api_host = active_sms_credential.api_host if active_sms_credential else "http://46.4.104.219/vb/apikey.php"

    # Determine the message
    if purpose == "verify":
        message = f"Dear {name}, Your OTP to verify mobile in CrewOrder is: {otp}. OTP will be valid for 5 minutes. -Team CrewOrder"
    elif purpose == "order_notify" and custom_message:
        message = custom_message
    else:
        message = f"Dear {name}, Your OTP to verify mobile in CrewOrder is: {otp}. OTP will be valid for 5 minutes. -Team CrewOrder"
    print(message,"-----------------------------444")

    # Construct the API URL
    url = f"{api_host}?apikey={sms_api_key}&senderid={sms_sender_id}&number={number}&message={message}"
    # url = f"http://46.4.104.219/vb/apikey.php?apikey={settings.SMS_API_KEY}&senderid={settings.SMS_SENDER_ID}&number={number}&message={message}"
    try:
        response = requests.get(url)
        return response.status_code == 200
    except requests.exceptions.RequestException as e:
        print(f"Error sending OTP: {e}")
        return False
    


def send_otp_to_email(email, otp,name='User'):
    try:
        subject = 'Your OTP Code'
        message = f'Your OTP code is {otp}. It will expire in 5 minutes.'
        try:
            subject = "Creworder Otp"
            template = "emails/otp_mail.html"  # Your HTML email template
            context = {
                'otp_code': otp,
                'name':name
                 # Update with your login URL
            }
            html_message = render_to_string(template, context)
            recipient_list = [email]
            res =send_email(subject, html_message, recipient_list)
            logger.info(f"Email sent successfully to {email}")
        except Exception as email_error:
            logger.error(f"Error sending email to {email}: {email_error}")
        return True
    except Exception:
        return False
from django.utils import timezone
class OTPViewSet(viewsets.ModelViewSet):
    queryset = OTPModel.objects.all()
    serializer_class = OTPSerializer

    # OTP Sending (Email or Phone)
    def create(self, request, *args, **kwargs):
        contact_info = request.data.get('contact_info') or request.data.get('phone_number')
        
        if not contact_info:
            return Response({"error": "Contact information (email or phone) is required"},
                            status=status.HTTP_400_BAD_REQUEST)
        if '@' not in contact_info:
            contact_info = str(contact_info)[-10:]
        otp_instance = OTPModel.create_otp(contact_info)

        # Send OTP
        success = send_otp_to_email(contact_info, otp_instance.otp) if '@' in contact_info else send_otp_to_number(contact_info, otp_instance.otp)

        if success:
            return Response({"message": "OTP sent successfully"})
        return Response({"error": "Failed to send OTP"},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # OTP Verification
    @action(detail=False, methods=['POST'], url_path='verify')
    def verify_otp(self, request):
        contact_info = request.data.get('contact_info') or request.data.get('phone_number')
        otp = request.data.get('otp')
        
        if not contact_info or not otp:
            return Response({"error": "Contact information and OTP are required"},
                            status=status.HTTP_400_BAD_REQUEST)
        if '@' not in contact_info:
            contact_info = str(contact_info)[-10:]
        # Remove expired OTPs
        OTPModel.objects.filter(expiration_time__lt=timezone.now()).delete()

        try:
            filter_kwargs = {"otp": otp}
            if "@" in contact_info:
                filter_kwargs["email"] = contact_info
            else:
                filter_kwargs["phone_number"] = contact_info

            otp_instance = OTPModel.objects.get(**filter_kwargs)

            if otp_instance.is_expired():
                return Response({"error": "OTP expired"}, status=status.HTTP_400_BAD_REQUEST)

            otp_instance.delete()
            return Response({"message": "OTP verified successfully"})

        except OTPModel.DoesNotExist:
            return Response({"error": "Invalid OTP or contact information"},
                            status=status.HTTP_400_BAD_REQUEST)