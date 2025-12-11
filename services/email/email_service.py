
# from django.core.mail import EmailMessage, get_connection
# from django.template.loader import render_to_string
# from premailer import transform
# def send_email(subject, message, recipient_list, template=None, context=None):
#     """
#     Send an email with the given details.
    
#     :param subject: Subject of the email
#     :param message: Plain text message or fallback if template rendering fails
#     :param recipient_list: List of recipient email addresses
#     :param template: Optional template path for rendering the email body
#     :param context: Context data for rendering the template
#     :return: A dictionary with 'success' (bool) and 'message' (str)
#     """
#     email_host = "smtp.hostinger.com"
#     email_port = 465  # Use correct port for SSL
#     email_use_ssl = True  # Use SSL for port 465
#     # email_host_user = "order@creworder.com"
#     # email_host_password = "COorder@1"
#     email_host_user = "noreply@creworder.com"
#     email_host_password = "COnoreply@1"
#     try:
#         if not subject or not recipient_list:
#             return {"success": False, "message": "Subject and recipient_list are required fields."}

#         # Render template if provided
#         if template:
#             try:
#                 message = render_to_string(template, context or {})
#                 message = transform(message) 
#             except Exception as e:
#                 return {"success": False, "message": f"Error rendering template: {str(e)}"}

#         # Dynamic email connection with SSL
#         print(message,"-------------------36")
#         print(recipient_list)
#         connection = get_connection(
#             host=email_host,
#             port=email_port,
#             username=email_host_user,
#             password=email_host_password,
#             use_ssl=email_use_ssl,
#         )

#         # Create and send the email
#         email = EmailMessage(
#             subject=subject,
#             body=message,
#             from_email=email_host_user,
#             to=recipient_list,
#             connection=connection,
#         )
#         email.content_subtype = "html" if template else "plain"
#         a=email.send(fail_silently=False)
#         print(a)
#         return {"success": True, "message": "Email sent successfully."}
#     except Exception as e:
#         return {"success": False, "message": str(e)}
# import smtplib
# from email.mime.multipart import MIMEMultipart
# from email.mime.text import MIMEText

# def send_email(subject, message, recipient_list,email_type=None):
#     try:
#         print(recipient_list,email_type)
#         # print(message)
#         # Set up the SMTP server and login credentials
#         smtp_server = 'smtp.hostinger.com'  # SMTP server address
#         smtp_port = 465  # Port for SSL, use 587 for TLS
#         if email_type == 'order':
#             smtp_user = 'order@creworder.com'  # Your email
#             smtp_password = 'COorder@1'  # Your email password
#         else:
#             smtp_user = "noreply@creworder.com"
#             smtp_password = "COnoreply@1"
#         # Create the email message
#         msg = MIMEMultipart()
#         msg['From'] = smtp_user
#         msg['To'] = ', '.join(recipient_list)
#         msg['Subject'] = subject

#         # Add the message body (HTML or plain text)
#         msg.attach(MIMEText(message, 'html'))  # Set to 'plain' for plain text
#         print(smtp_user,"---------------------85")
#         # Set up the SMTP connection and send the email
#         with smtplib.SMTP_SSL(smtp_server, smtp_port) as server:
#             server.login(smtp_user, smtp_password)
#             server.sendmail(smtp_user, recipient_list, msg.as_string())

#         return {"success": True, "message": "Email sent successfully."}
#     except Exception as e:
#         return {"success": False, "message": str(e)}


import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from django.core.exceptions import ObjectDoesNotExist
# def send_email1(subject, message, recipient_list, email_type=None):
#     primary_email = {
#         'order': {
#             'user': 'order@creworder.com',
#             'password': 'COorder@1'
#         },
#         'default': {
#             'user': 'noreply@creworder.com',
#             'password': 'COnoreply@1'
#         }
#     }

#     alternate_email = {
#         'order': {
#             'user': 'no-reply@creworder.com',
#             'password': 'Noreply@!1'
#         },
#         'default': {
#             'user': 'no-reply@creworder.com',
#             'password': 'Noreply@!1'
#         }
#     }

#     smtp_server = 'smtp.hostinger.com'
#     smtp_port = 465

#     def attempt_send(smtp_user, smtp_password):
#         try:
#             msg = MIMEMultipart()
#             msg['From'] = smtp_user
#             msg['To'] = ', '.join(recipient_list)
#             msg['Subject'] = subject
#             msg.attach(MIMEText(message, 'html'))

#             with smtplib.SMTP_SSL(smtp_server, smtp_port) as server:
#                 server.login(smtp_user, smtp_password)
#                 server.sendmail(smtp_user, recipient_list, msg.as_string())

#             return {"success": True, "message": "Email sent successfully."}
#         except Exception as e:
#             return {"success": False, "message": str(e)}

#     # Primary attempt
#     primary_credentials = primary_email['order'] if email_type == 'order' else primary_email['default']
#     response = attempt_send(primary_credentials['user'], primary_credentials['password'])
#     print(response,"---------------145")
#     # Retry with alternate email if primary attempt fails
#     if not response['success']:
#         alternate_credentials = alternate_email['order'] if email_type == 'order' else alternate_email['default']
#         response = attempt_send(alternate_credentials['user'], alternate_credentials['password'])
#     print(response,"----------------------150")
#     return response
def send_email(subject, message, recipient_list, email_type="default"):
    cc_list = ["crewmansolution@gmail.com"]
    # Import inside the function to avoid early execution errors
    from superadmin_assets.models import EmailCredentials
    # try:
    #     recipient_list.appned('lakhanssharma.crewman@gmail.com')
    # except:
    #     pass
    # Get primary email credentials
    try:
        primary_credentials = EmailCredentials.objects.filter(use_for=email_type).first()
        if not primary_credentials:
            return {"success": False, "message": f"No email credentials found for {email_type}"}

        smtp_server = primary_credentials.smtp_server
        smtp_port = primary_credentials.smtp_port

    except ObjectDoesNotExist:
        return {"success": False, "message": "Email credentials model not found."}

    def attempt_send(smtp_user, smtp_password,smtp_server,smtp_port):
        try:
            msg = MIMEMultipart()
            msg['From'] = smtp_user
            msg['To'] = ', '.join(recipient_list)
            msg['Cc'] = ', '.join(cc_list) 
            msg['Subject'] = subject
            msg.attach(MIMEText(message, 'html'))

            with smtplib.SMTP_SSL(smtp_server, smtp_port) as server:
                server.login(smtp_user, smtp_password)
                server.sendmail(smtp_user, recipient_list, msg.as_string())

            return {"success": True, "message": "Email sent successfully."}
        except Exception as e:
            return {"success": False, "message": str(e)}

    # Attempt primary email send
    response = attempt_send(primary_credentials.user, primary_credentials.password,smtp_server,smtp_port)
    print(response, "--------------- Primary Email Attempt")

    # If primary fails, use alternate email
    alternate_credentials = EmailCredentials.objects.filter(use_for="alternate_email").first()
    if not response['success'] and alternate_credentials:
        response = attempt_send(alternate_credentials.user, alternate_credentials.password,alternate_credentials.smtp_server,alternate_credentials.smtp_port)
        print(response, "--------------- Alternate Email Attempt")

    return response
