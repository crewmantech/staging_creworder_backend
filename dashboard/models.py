from django.db import models
from middleware.request_middleware import get_request
from django.contrib.auth.models import User, Permission
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
class Dashboard(models.Model):
    class Meta:
       
        db_table ='dashboard_table'
    name=models.CharField(max_length=255,blank=True,null=True)
    created_at = models.DateField(auto_now_add=True)
    updated_at = models.DateField(auto_now=True)
    def __str__(self):
        return f'{self.name}'
    

class Targets(models.Model):
    name=models.CharField(max_length=255,blank=True,null=True)
    created_at = models.DateField(auto_now_add=True)
    updated_at = models.DateField(auto_now=True)
    def __str__(self):
        return f'{self.name}'

class Labels_layout(models.Model):
    name=models.CharField(max_length=255,blank=True,null=True)
    created_at = models.DateField(auto_now_add=True)
    updated_at = models.DateField(auto_now=True)
    def __str__(self):
        return f'{self.name}'
    
class Assign_role(models.Model):
    name=models.CharField(max_length=255,blank=True,null=True)
    created_at = models.DateField(auto_now_add=True)
    updated_at = models.DateField(auto_now=True)
    def __str__(self):
        return f'{self.name}'
    
class Invoice_management(models.Model):
    name=models.CharField(max_length=255,blank=True,null=True)
    created_at = models.DateField(auto_now_add=True)
    updated_at = models.DateField(auto_now=True)
    def __str__(self):
        return f'{self.name}'
    


class PermissionSetup(BaseModel):
    name = models.CharField(max_length=255, unique=True)
    models_name = models.JSONField()  # Store list of models as JSON
    role_type = models.CharField(max_length=50)  # Role type (admin, superadmin, etc.)

    def __str__(self):
        return self.name
    

class Running_tile(models.Model):
    class Meta:
        permissions = (
                ('view_own_dashboard_running_tile', 'Can view own dashboard running tile'),
                ('view_all_dashboard_running_tile', 'Can view all dashboard running tile'),
                ('view_manager_dashboard_running_tile', 'Can view manager dashboard running tile'),
                ('view_teamlead_dashboard_running_tile', 'Can view team lead dashboard running tile'))
    
    name=models.CharField(max_length=255,blank=True,null=True)
    def __str__(self):
        return f'{self.name}'
class Pending_tile(models.Model):
    class Meta:
        permissions = (
                ('view_own_dashboard_pending_tile', 'Can view own dashboard pending tile'),
                ('view_all_dashboard_pending_tile', 'Can view all dashboard pending tile'),
                ('view_manager_dashboard_pending_tile', 'Can view manager dashboard pending tile'),
                ('view_teamlead_dashboard_pending_tile', 'Can view team lead dashboard pending tile')
            )
    
    name=models.CharField(max_length=255,blank=True,null=True)
    def __str__(self):
        return f'{self.name}'
class Repeat_order_tile(models.Model):
    class Meta:
        permissions = (
                ('view_own_dashboard_repeat_order_tile', 'Can view own dashboard repeat_order tile'),
                ('view_all_dashboard_repeat_order_tile', 'Can view all dashboard repeat_order tile'),
                ('view_manager_dashboard_repeat_order_tile', 'Can view manager dashboard repeat_order tile'),
            ('view_teamlead_dashboard_repeat_order_tile', 'Can view team lead dashboard repeat_order tile')
            )
    
    name=models.CharField(max_length=255,blank=True,null=True)
    def __str__(self):
        return f'{self.name}'
class Rejected_tile(models.Model):
    class Meta:
        permissions = (
                ('view_own_dashboard_rejected_tile', 'Can view own dashboard rejected tile'),
                ('view_all_dashboard_rejected_tile', 'Can view all dashboard rejected tile'),
                ('view_manager_dashboard_rejected_tile', 'Can view manager dashboard rejected tile'),
                ('view_teamlead_dashboard_rejected_tile', 'Can view team lead dashboard rejected tile')
            )
    
    name=models.CharField(max_length=255,blank=True,null=True)
    def __str__(self):
        return f'{self.name}'
class IN_Transit_tile(models.Model):
    class Meta:
        permissions = (
                ('view_own_dashboard_in_transit_tile', 'Can view own dashboard in transit tile'),
                ('view_all_dashboard_in_transit_tile', 'Can view all dashboard in transit tile'),
                ('view_manager_dashboard_in_transit_tile', 'Can view manager dashboard in transit tile'),
                ('view_teamlead_dashboard_in_transit_tile', 'Can view team lead dashboard in transit tile')
                )
    
    name=models.CharField(max_length=255,blank=True,null=True)
    def __str__(self):
        return f'{self.name}'
class Accepted_tile(models.Model):
    class Meta:
        permissions = (
                ('view_own_dashboard_accepted_tile', 'Can view own dashboard accepted tile'),
                ('view_all_dashboard_accepted_tile', 'Can view all dashboard accepted tile'),
                ('view_manager_dashboard_accepted_tile', 'Can view manager dashboard accepted tile'),
            ('view_teamlead_dashboard_accepted_tile', 'Can view team lead dashboard accepted tile'))
    
    name=models.CharField(max_length=255,blank=True,null=True)
    def __str__(self):
        return f'{self.name}'
class No_response_tile(models.Model):
    class Meta:
        permissions = (
                ('view_own_dashboard_no_response_tile', 'Can view own dashboard no response tile'),
                ('view_all_dashboard_no_response_tile', 'Can view all dashboard no response tile'),
                ('view_manager_dashboard_no_response_tile', 'Can view manager dashboard no response tile'),
                ('view_teamlead_dashboard_no_response_tile', 'Can view team lead dashboard no response tile'))
        
    name=models.CharField(max_length=255,blank=True,null=True)
    def __str__(self):
        return f'{self.name}'
class Total_tile(models.Model):
    class Meta:
        permissions = (
                ('view_own_dashboard_total_tile', 'Can view own dashboard total tile'),
                ('view_all_dashboard_total_tile', 'Can view all dashboard total tile'),
                ('view_manager_dashboard_total_tile', 'Can view manager dashboard total tile'),
                ('view_teamlead_dashboard_total_tile', 'Can view team lead dashboard total tile')
                )
    
    name=models.CharField(max_length=255,blank=True,null=True)
    def __str__(self):
        return f'{self.name}'
    
class Future_tile(models.Model):
    class Meta:
        permissions = (
            ('view_own_dashboard_future_tile', 'Can view own dashboard future tile'),
            ('view_all_dashboard_future_tile', 'Can view all dashboard future tile'),
            ('view_manager_dashboard_future_tile', 'Can view manager dashboard future tile'),
            ('view_teamlead_dashboard_future_tile', 'Can view team lead dashboard future tile'),
        )

    name = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f'{self.name}'


class Delivered_tile(models.Model):
    class Meta:
        permissions = (
            ('view_own_dashboard_delivered_tile', 'Can view own dashboard delivered tile'),
            ('view_all_dashboard_delivered_tile', 'Can view all dashboard delivered tile'),
            ('view_manager_dashboard_delivered_tile', 'Can view manager dashboard delivered tile'),
            ('view_teamlead_dashboard_delivered_tile', 'Can view team lead dashboard delivered tile'),
        )

    name = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f'{self.name}'


class Order_chart(models.Model):
    class Meta:
        permissions = (
            ('view_own_dashboard_schedule_order_chart', 'Can view own dashboard schedule order chart'),
            ('view_all_dashboard_schedule_order_chart', 'Can view all dashboard schedule order chart'),
            ('view_manager_dashboard_schedule_order_chart', 'Can view manager dashboard schedule order chart'),
            ('view_teamlead_dashboard_schedule_order_chart', 'Can view team lead dashboard schedule order chart'),
        )

    name = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f'{self.name}'


class Forecast_chart(models.Model):
    class Meta:
        permissions = (
            ('view_all_dashboard_sales_forecast_chart', 'Can view all dashboard sales forecast chart'),
            ('view_manager_dashboard_sales_forecast_chart', 'Can view manager dashboard sales forecast chart'),
            ('view_teamlead_dashboard_sales_forecast_chart', 'Can view team lead dashboard sales forecast chart'),
        )

    name = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f'{self.name}'


class Top_selling_list(models.Model):
    class Meta:
        permissions = (
            ('view_own_dashboard_top_selling_list', 'Can view own dashboard top selling list'),
            ('view_all_dashboard_top_selling_list', 'Can view all dashboard top selling list'),
            ('view_manager_dashboard_top_selling_list', 'Can view manager dashboard top selling list'),
            ('view_teamlead_dashboard_top_selling_list', 'Can view team lead dashboard top selling list'),
     )

    name = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f'{self.name}'


class Team_order_list(models.Model):
    class Meta:
        permissions = (
            # ('view_own_dashboard_team_order_list', 'Can view own dashboard team order list'),
            ('view_all_dashboard_team_order_list', 'Can view all dashboard team order list'),
            ('view_manager_dashboard_team_order_list', 'Can view manager dashboard team order list'),
            ('view_own_team_dashboard_team_order_list', 'Can view own team dashboard team order list'),
        )

    name = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f'{self.name}'


class Initiatedrto(models.Model):
    class Meta:
        permissions = (
            ('view_own_dashboard_initiatedrto', 'Can view own dashboard initiatedrto'),
            ('view_all_dashboard_initiatedrto', 'Can view all dashboard initiatedrto'),
            ('view_manager_dashboard_initiatedrto', 'Can view manager dashboard initiatedrto'),
            ('view_teamlead_dashboard_initiatedrto', 'Can view team lead dashboard initiatedrto'),
        )

    name = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f'{self.name}'


class Rto_tile(models.Model):
    class Meta:
        permissions = (
            ('view_own_dashboard_rto_tile', 'Can view own dashboard rto tile'),
            ('view_all_dashboard_rto_tile', 'Can view all dashboard rto tile'),
            ('view_manager_dashboard_rto_tile', 'Can view manager dashboard rto tile'),
            ('view_teamlead_dashboard_rto_tile', 'Can view team lead dashboard rto tile'),
        )

    name = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f'{self.name}'


class Non_serviceable_tile(models.Model):
    class Meta:
        permissions = (
            ('view_own_dashboard_non_serviceable_tile', 'Can view own dashboard non serviceable tile'),
            ('view_all_dashboard_non_serviceable_tile', 'Can view all dashboard non serviceable tile'),
            ('view_manager_dashboard_non_serviceable_tile', 'Can view manager dashboard non serviceable tile'),
            ('view_teamlead_dashboard_non_serviceable_tile', 'Can view team lead dashboard non serviceable tile'),
        )

    name = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f'{self.name}'


class Reattempt_tile(models.Model):
    class Meta:
        permissions = (
            ('view_own_dashboard_reattempt_tile', 'Can view own dashboard reattempt tile'),
            ('view_all_dashboard_reattempt_tile', 'Can view all dashboard reattempt tile'),
            ('view_manager_dashboard_reattempt_tile', 'Can view manager dashboard reattempt tile'),
            ('view_teamlead_dashboard_reattempt_tile', 'Can view team lead dashboard reattempt tile'),
        )

    name = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f'{self.name}'


class OFD_tile(models.Model):
    class Meta:
        permissions = (
            ('view_own_dashboard_ofd_tile', 'Can view own dashboard ofd tile'),
            ('view_all_dashboard_ofd_tile', 'Can view all dashboard ofd tile'),
            ('view_manager_dashboard_ofd_tile', 'Can view manager dashboard ofd tile'),
            ('view_teamlead_dashboard_ofd_tile', 'Can view team lead dashboard ofd tile'),
        )

    name = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f'{self.name}'


class Exception_tile(models.Model):
    class Meta:
        permissions = (
            ('view_own_dashboard_exception_tile', 'Can view own dashboard exception tile'),
            ('view_all_dashboard_exception_tile', 'Can view all dashboard exception tile'),
            ('view_manager_dashboard_exception_tile', 'Can view manager dashboard exception tile'),
            ('view_teamlead_dashboard_exception_tile', 'Can view team lead dashboard exception tile'),
        )

    name = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f'{self.name}'


class NDR_tile(models.Model):
    class Meta:
        permissions = (
            ('view_own_dashboard_ndr_tile', 'Can view own dashboard ndr tile'),
            ('view_all_dashboard_ndr_tile', 'Can view all dashboard ndr tile'),
            ('view_manager_dashboard_ndr_tile', 'Can view manager dashboard ndr tile'),
            ('view_teamlead_dashboard_ndr_tile', 'Can view team lead dashboard ndr tile'),
        )

    name = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f'{self.name}'
    
class Pendingspickup_tile(models.Model):
    class Meta:
        permissions = (
            ('view_own_dashboard_pendingspickup_tile', 'Can view own dashboard pendingspickup tile'),
            ('view_all_dashboard_pendingspickup_tile', 'Can view all dashboard pendingspickup tile'),
            ('view_manager_dashboard_pendingspickup_tile', 'Can view manager dashboard pendingspickup tile'),
            ('view_teamlead_dashboard_pendingspickup_tile', 'Can view team lead dashboard pendingspickup tile'),
     )

    name = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f'{self.name}'
    
class Deliveredrto_tile(models.Model):
    class Meta:
        permissions = (
            ('view_own_dashboard_deliveredrto_tile', 'Can view own dashboard deliveredrto tile'),
            ('view_all_dashboard_deliveredrto_tile', 'Can view all dashboard deliveredrto tile'),
            ('view_manager_dashboard_deliveredrto_tile', 'Can view manager dashboard deliveredrto tile'),
            ('view_teamlead_dashboard_deliveredrto_tile', 'Can view team lead dashboard deliveredrto tile'),
     )

    name = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f'{self.name}'