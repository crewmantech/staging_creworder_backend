import random
import string
from django.db import models
from accounts.models import Company, Branch
from django.contrib.auth.models import User

from accounts.utils import generate_unique_id
from orders.models import Products


from middleware.request_middleware import get_request

class BaseModel(models.Model):
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="%(app_label)s_%(class)s_created_by")
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="%(app_label)s_%(class)s_updated_by")

    def save(self, *args, **kwargs):
        request = get_request()
        if request and request.user.is_authenticated:
            if not self.pk:
                self.created_by = request.user
            self.updated_by = request.user
        super().save(*args, **kwargs)
    class Meta:
        abstract = True

class LeadModel(BaseModel):
    status=[
        (1,"Read"),
        (0,"Unread")
    ]
    id = models.CharField(max_length=50, primary_key=True, unique=True)
    customer_name = models.CharField(max_length=50)
    customer_number = models.CharField(max_length=50)
    customer_call_id = models.CharField(max_length=50)
    assign_user = models.ForeignKey(User,on_delete=models.CASCADE)
    status = models.IntegerField(choices=status,default=0)
    remark = models.TextField()
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE)
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        db_table = 'lead_table'
    def save(self, *args, **kwargs):
        if not self.id:
            self.id = generate_unique_id(LeadModel, prefix='KYI')
        super().save(*args, **kwargs)
    def __str__(self):
        return self.customer_name
    

class LeadSourceModel(BaseModel):
    branch = models.ForeignKey(Branch, related_name="custom_models", on_delete=models.CASCADE,null=True, blank=True)
    company = models.ForeignKey(Company, related_name="custom_models", on_delete=models.CASCADE,null=True, blank=True)
    name = models.CharField(max_length=200, null=False, blank=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    id = models.CharField(max_length=50, primary_key=True, unique=True)
    class Meta:
        db_table = 'lead_source_table'
    def save(self, *args, **kwargs):
        if not self.id:
            self.id = generate_unique_id(LeadSourceModel, prefix='KYI')
        super().save(*args, **kwargs)
    def __str__(self):
        return self.name

    # class Lead(BaseModel):
    # # Fields as mentioned
    # name = models.CharField(max_length=255)
    # email = models.EmailField(max_length=255)
    # phone = models.CharField(max_length=15)
    # postalcode = models.CharField(max_length=20)
    # city = models.CharField(max_length=100)
    # state = models.CharField(max_length=100)
    # address = models.TextField()
    # message = models.TextField()
    # branch = models.ForeignKey(Branch, on_delete=models.CASCADE)
    # company = models.ForeignKey(Company, on_delete=models.CASCADE)
    # # Foreign Key to ProductModel
    # product = models.ForeignKey(ProductModel, related_name="leads", on_delete=models.CASCADE)
    # # Select Lead - Could be a choice field or any other logic to mark a lead
    # select_lead = models.BooleanField(default=False)
    # # Timestamps
    # created_at = models.DateTimeField(auto_now_add=True)
    # updated_at = models.DateTimeField(auto_now=True)

    # def __str__(self):
    #     return f"Lead for {self.product.product_name} by {self.name}"

    # class Meta:
    #     db_table = 'leads_table'


    # branch
    # company
    # name 
    # created_at
    # updated_at
    
# class Lead(BaseModel):
#     name = models.CharField(max_length=255)
#     email = models.EmailField()
#     phone = models.CharField(max_length=20)
#     postalcode = models.CharField(max_length=20)
#     city = models.CharField(max_length=100)
#     state = models.CharField(max_length=100)
#     address = models.TextField()
#     message = models.TextField()
    
#     # Foreign Key relations
#     product = models.ForeignKey(ProductModel, on_delete=models.CASCADE)
#     lead_source = models.ForeignKey(LeadSourceModel, on_delete=models.CASCADE)
    
#     # Audit fields
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)

#     def __str__(self):
#         return f"Lead: {self.name} ({self.email})"
    

class LeadStatusModel(BaseModel):
    branch = models.ForeignKey(Branch, related_name="custom_status_models", on_delete=models.CASCADE,null=True, blank=True)
    company = models.ForeignKey(Company, related_name="custom_status_models", on_delete=models.CASCADE,null=True, blank=True)
    name = models.CharField(max_length=200, null=False, blank=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    id = models.CharField(max_length=50, primary_key=True, unique=True)
    class Meta:
        db_table = 'lead_status_table'
    def save(self, *args, **kwargs):
        if not self.id:
            self.id = generate_unique_id(LeadSourceModel, prefix='KYI')
        super().save(*args, **kwargs)
    def __str__(self):
        return self.name
    
    
class DealCategoryModel(BaseModel):
    branch = models.ForeignKey(Branch, related_name="deal_category_models", on_delete=models.CASCADE,null=True, blank=True)
    company = models.ForeignKey(Company, related_name="deal_category_models", on_delete=models.CASCADE,null=True, blank=True)
    name = models.CharField(max_length=200, null=False, blank=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    id = models.CharField(max_length=50, primary_key=True, unique=True)
    class Meta:
        db_table = 'deal_category_table'
    def save(self, *args, **kwargs):
        if not self.id:
            self.id = generate_unique_id(LeadSourceModel, prefix='KYI')
        super().save(*args, **kwargs)
    def __str__(self):
        return self.name
    

class UserCategoryAssignment(BaseModel):
    user_profile = models.ForeignKey(User, on_delete=models.CASCADE, related_name="category_assignments")
    deal_category = models.ForeignKey(DealCategoryModel, on_delete=models.CASCADE)
    assigned_at = models.DateTimeField(auto_now_add=True)
    id = models.CharField(max_length=50, primary_key=True, unique=True)
    def save(self, *args, **kwargs):
        if not self.id:
            self.id = generate_unique_id(UserCategoryAssignment, prefix='UAI')
        super().save(*args, **kwargs)
    def __str__(self):
        return f"{self.user_profile.profile} - {self.deal_category.name}"
    

class Pipeline(BaseModel):
    name = models.CharField(max_length=200, null=False, blank=False)
    branch = models.ForeignKey(Branch, related_name="pipeline_models", on_delete=models.CASCADE,null=True, blank=True)
    company = models.ForeignKey(Company, related_name="pipeline_models", on_delete=models.CASCADE,null=True, blank=True)
    lead_source = models.ForeignKey(LeadSourceModel, on_delete=models.CASCADE)
    deal_category = models.ForeignKey(DealCategoryModel, on_delete=models.CASCADE)
    assigned_users = models.ManyToManyField(User, related_name="pipelines", blank=True)  # Changed to ManyToManyField
    round_robin = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_assigned_index = models.IntegerField(default=-1)
    id = models.CharField(max_length=50, primary_key=True, unique=True)
    def save(self, *args, **kwargs):
        if not self.id:
            self.id = generate_unique_id(Pipeline, prefix='PLI')
        super().save(*args, **kwargs)  
    def __str__(self):
        return f"Pipeline {self.id} - {self.lead_source}"
    


class Lead(BaseModel):
    lead_id = models.CharField(max_length=10, unique=True, editable=False)

    customer_name = models.CharField(max_length=255)
    customer_email = models.EmailField()
    customer_phone = models.CharField(max_length=20)
    customer_postalcode = models.CharField(max_length=20)
    customer_city = models.CharField(max_length=100)
    customer_state = models.CharField(max_length=100)
    customer_address = models.TextField()
    customer_message = models.TextField()
    
    product = models.ForeignKey(Products, on_delete=models.CASCADE)
    lead_source = models.ForeignKey(LeadSourceModel, on_delete=models.CASCADE)
    pipeline = models.ForeignKey(Pipeline, on_delete=models.SET_NULL, null=True, blank=True)
    assign_user = models.ForeignKey(User, on_delete=models.CASCADE)
    
    status = models.ForeignKey(LeadStatusModel, on_delete=models.SET_NULL, null=True, blank=True)
    remark = models.TextField(null=True, blank=True)
    
    branch = models.ForeignKey(Branch, related_name="lead_branch", on_delete=models.CASCADE, null=True, blank=True)
    company = models.ForeignKey(Company, blank=True, null=True, on_delete=models.CASCADE, related_name="lead_company")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    id = models.CharField(max_length=50, primary_key=True, unique=True)
    def generate_lead_id(self):
        """Generate a custom id with prefix LEAD and 5 random alphanumeric characters"""
        return f"LEAD{''.join(random.choices(string.ascii_uppercase + string.digits, k=5))}"

    def save(self, *args, **kwargs):
        if not self.lead_id:
            unique = False
            while not unique:
                new_id = self.generate_lead_id()
                if not Lead.objects.filter(lead_id=new_id).exists():
                    self.lead_id = new_id
                    unique = True
        if not self.id:
            self.id = generate_unique_id(Lead, prefix='LDI')
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Lead: {self.customer_name} ({self.customer_email})"

    class Meta:
        permissions = [
            ('update_lead_status_remark', 'Can update only status and remark fields'),
        ]
        

class lead_form(BaseModel):
    id = models.CharField(max_length=50, primary_key=True, unique=True)
    form_name = models.CharField(max_length=255)
    fields = models.JSONField()  # To store the dynamic fields and values
    pipeline = models.ForeignKey(Pipeline, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        db_table = 'lead_form'

    def save(self, *args, **kwargs):
        if not self.id:
            self.id = generate_unique_id(lead_form, prefix='LFI')
        super().save(*args, **kwargs)     
    def __str__(self):
        return f"Request {self.id} - Pipeline {self.pipeline}"