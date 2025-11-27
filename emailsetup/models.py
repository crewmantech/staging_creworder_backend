from django.db import models
from phonenumber_field.modelfields import PhoneNumberField
from accounts.models import Branch, Company
from middleware.request_middleware import get_request
from django.contrib.auth.models import User

# from django.utils import timezone


class BaseModel(models.Model):
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="%(class)s_created_by")
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="%(class)s_updated_by")

    def save(self, *args, **kwargs):
        request = get_request()
        if request and request.user.is_authenticated:
            if not self.pk:
                self.created_by = request.user
            self.updated_by = request.user
        super().save(*args, **kwargs)

    class Meta:
        abstract = True

class EmailTemplate(BaseModel):
    templatename = models.CharField(max_length=255)
    code = models.TextField()  # Store HTML code
    subject = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, null=True, blank=True)
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, null=True, blank=True)
    column = models.JSONField()  #Store additional JSON data
    
    class Meta:
        db_table = 'email_template_table'
    def __str__(self):
        return self.templatename


class AgentAuthentication(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, null=True, blank=True)
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, null=True, blank=True)
    email = models.EmailField(max_length=100, null=False)
    phone = PhoneNumberField( null=False, blank=False, region="IN")  # Accepts Indian phone numbers

    class Meta:
        db_table = 'agent_authentication_table'

    def __str__(self):
        return self.email
    

class AgentReport(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, null=True, blank=True)
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, null=True, blank=True)
    email = models.EmailField(max_length=100, null=False)

    class Meta:
        db_table = 'agent_report_table'

    def __str__(self):
        return self.email
    
from django.core.exceptions import ValidationError
class AgentAuthenticationNew(models.Model):
    company = models.ForeignKey(
    "accounts.Company",
    on_delete=models.CASCADE,
    null=True,
    blank=True
)

    branch = models.ForeignKey(
        "accounts.Branch",
        on_delete=models.CASCADE,
        null=True,
        blank=True
)

    users = models.ManyToManyField(
        User,
        through="AgentUserMapping",
        related_name="agent_auth_users",
        blank=True
    )

    email = models.EmailField(max_length=100)
    phone = PhoneNumberField(region="IN")

    class Meta:
        db_table = 'agent_authenticationnew_table'

    def __str__(self):
        return self.email


class AgentUserMapping(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, unique=True)
    agent_auth = models.ForeignKey(AgentAuthenticationNew, on_delete=models.CASCADE)

    class Meta:
        db_table = "agent_user_mapping"
        constraints = [
            models.UniqueConstraint(
                fields=["user"],
                name="user_unique_globally_for_agent_auth"
            )
        ]

    def __str__(self):
        return f"{self.user} → {self.agent_auth}"

    def clean(self):
        if AgentUserMapping.objects.filter(user=self.user).exists() and not self.pk:
            raise ValidationError("This user is already assigned to another entity.")