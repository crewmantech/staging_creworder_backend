from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication

from accounts.models import Employees
from .models import AgentAuthenticationNew, AgentReport, AgentAuthentication, AgentUserMapping, EmailTemplate
from .serializers import AgentAuthenticationNewSerializer, AgentAuthenticationSerializer, AgentReportSerializer, EmailTemplateSerializer
from services.email.email_service import send_email
from django.core.mail import EmailMessage,get_connection
from django.template.loader import render_to_string
from django.conf import settings
from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import viewsets, serializers  
from django.db.models import Q
class EmailTemplateViewSet(ModelViewSet):
    queryset = EmailTemplate.objects.all()
    serializer_class = EmailTemplateSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Limit the queryset to templates associated with the user's company and branch.
        """
        user = self.request.user
        
        return EmailTemplate.objects.filter(company=user.profile.company, branch=user.profile.branch)

    def perform_create(self, serializer):
        """
        Automatically set company and branch based on the authenticated user during creation.
        """
        user = self.request.user
        serializer.save(company=user.profile.company, branch=user.profile.branch)

    def perform_update(self, serializer):
        """
        Ensure company and branch are set properly during updates.
        """
        user = self.request.user
        serializer.save(company=user.profile.company, branch=user.profile.branch)



class SendEmailAPI(APIView):
    def post(self, request, *args, **kwargs):
        email_data = request.data
        subject = email_data.get("subject", "")
        recipient_list = email_data.get("recipient_list", [])
        email_type = email_data.get("email_type", None)
        
        # Check if a file has been uploaded
        # if 'template_file' not in request.FILES:
        #     return Response({"success": False, "message": "No template file uploaded."}, status=status.HTTP_400_BAD_REQUEST)
        
        # # Get the uploaded file
        # template_file = request.FILES['template_file']
        
        # # Validate file type (only allow HTML or plain text files)
        # if not template_file.name.endswith(('.html', '.txt')):
        #     return Response({"success": False, "message": "Invalid file format. Only .html and .txt files are allowed."}, status=status.HTTP_400_BAD_REQUEST)
        
        # Read the template file content
        # try:
        #     template_content = template_file.read().decode('utf-8')
        # except Exception as e:
        #     return Response({"success": False, "message": f"Error reading file: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)
        
        # Process the dynamic content from the template file
        try:
            # You can pass additional context to the render_to_string function if needed
            # For now, we use the content as is
            message = "test"
            template = "emails/welcome_email.html"  # Your HTML email template
            context = {
                'full_name': "inquiry.full_name",
                'company_name': "inquiry.company_name",
                'username': "username.lower()",
                'password': "inquiry.password",
                'login_url': "https://creworder.com/login",  # Update with your login URL
            }
            html_message = render_to_string(template, context)
            # if email_type == 'html':
            #     message = render_to_string(template_content)  # Render as HTML if needed
        except Exception as e:
            return Response({"success": False, "message": f"Error rendering template: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)

        # Send the email using the send_email function
        
        result = send_email(subject, message, recipient_list, email_type)
        status_code = status.HTTP_200_OK if result["success"] else status.HTTP_400_BAD_REQUEST

        return Response(result, status=status_code)
    




# class SendEmailAPI(APIView):
#     def post(self, request, *args, **kwargs):
#         email_data = request.data
#         try:
#             # Extract data
#             subject = email_data.get("subject", "")
#             message = email_data.get("message", "")
#             recipient_list = email_data.get("recipient_list", [])
#             template = email_data.get("template", None)
#             context = email_data.get("context", {})
#             email_host = "smtp.hostinger.com"
#             email_port = 465  # Use correct port for SSL
#             email_use_ssl = True  # Use SSL for port 465
#             # email_host_user = "noreply@creworder.com"
#             # email_host_password = "COnoreply@1"
#             email_host_user = "order@creworder.com"
#             email_host_password = "COorder@1"
#             if not subject or not recipient_list:
#                 return Response(
#                     {"success": False, "message": "Subject and recipient_list are required fields."},
#                     status=status.HTTP_400_BAD_REQUEST,
#                 )

#             # Render template if provided
#             if template:
#                 try:
#                     message = render_to_string(template, context)
#                 except Exception as e:
#                     return Response(
#                         {"success": False, "message": f"Error rendering template: {str(e)}"},
#                         status=status.HTTP_400_BAD_REQUEST,
#                     )

#             # Dynamic email connection with SSL
#             connection = get_connection(
#                 host=email_host,
#                 port=email_port,
#                 username=email_host_user,
#                 password=email_host_password,
#                 use_ssl=email_use_ssl,
#             )

#             # Create and send the email
#             email = EmailMessage(
#                 subject=subject,
#                 body=message,
#                 from_email=email_host_user,
#                 to=recipient_list,
#                 connection=connection,
#             )
#             email.content_subtype = "html" if template else "plain"
#             email.send(fail_silently=False)

#             return Response(
#                 {"success": True, "message": "Email sent successfully."},
#                 status=status.HTTP_200_OK,
#             )
#         except Exception as e:
#             return Response(
#                 {"success": False, "message": str(e)},
#                 status=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             )


# class SendEmailAPI(APIView):
#     def post(self, request, *args, **kwargs):
#         email_data = request.data
#         subject = email_data.get("subject", "")
#         message = email_data.get("template", "")
#         recipient_list = email_data.get("recipient_list", [])
#         email_type = email_data.get("email_type", None)
#         message = render_to_string(message)
#         # Call the send_email utility function
#         result = send_email(subject, message, recipient_list,email_type)
#         status_code = status.HTTP_200_OK if result["success"] else status.HTTP_400_BAD_REQUEST

#         return Response(result, status=status_code)




class AgentAuthenticationViewSet(viewsets.ModelViewSet):
    serializer_class = AgentAuthenticationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filter AgentAuthentication objects by the user's company."""
        user = self.request.user
        company = getattr(user.profile, "company", None)  # Get the user's company safely
        if company:
            return AgentAuthentication.objects.filter(company=company)
        return AgentAuthentication.objects.none()

    def perform_create(self, serializer):
        """Ensure the company is set when creating an AgentAuthentication."""
        user = self.request.user
        company = getattr(user.profile, "company", None)  # Safely get the company
        serializer.save(company=company)



class AgentReportViewSet(viewsets.ModelViewSet):
    serializer_class = AgentReportSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filter AgentAuthentication objects by the user's company."""
        user = self.request.user
        company = getattr(user.profile, "company", None)  # Get the user's company safely
        if company:
            return AgentReport.objects.filter(company=company)
        return AgentReport.objects.none()

    def perform_create(self, serializer):
        """Ensure the company is set when creating an AgentAuthentication."""
        user = self.request.user
        company = getattr(user.profile, "company", None)  # Safely get the company
        serializer.save(company=company)


class AgentAuthenticationNewViewSet(ModelViewSet):
    serializer_class = AgentAuthenticationNewSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filter AgentAuthentication objects by the user's company."""
        user = self.request.user
        company = getattr(user.profile, "company", None)  # Get the user's company safely
        if company:
            return AgentAuthenticationNew.objects.filter(company=company)
        return AgentAuthenticationNew.objects.none()
    
    def perform_create(self, serializer):
        """
        Automatically set company and branch based on the authenticated user during creation.
        """
        user = self.request.user
        serializer.save(company=user.profile.company)


class AvailableUsersForAgentView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        branch_id = request.query_params.get("branch_id")

        if not branch_id:
            return Response({"error": "branch_id is required"}, status=400)

        # all employees of this branch
        employees = Employees.objects.filter(branch_id=branch_id)

        # users already assigned to some entity
        assigned_user_ids = AgentUserMapping.objects.values_list("user_id", flat=True)

        # filter users not in mapping table
        available = employees.exclude(user_id__in=assigned_user_ids)

        data = [
            {
                "id": emp.user.id,
                "username": emp.user.username,
                "email": emp.user.email,
                "contact_no": str(emp.contact_no),
                "employee_id": emp.employee_id,
                "user_type": emp.user_type
            }
            for emp in available
        ]

        return Response({"users": data})