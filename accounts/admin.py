from django.contrib import admin
from .models import Company, ExpiringToken, InterviewApplication, LoginAttempt, LoginLog, OTPAttempt
from .models import Package
from .models import PackageDetailsModel
from .models import Employees
from .models import Notice1
from .models import Branch
from .models import Module
from .models import FormEnquiry
from .models import SupportTicket
from .models import Department
from .models import Designation
from .models import Leaves
from .models import Holiday
from .models import Award
from .models import Appreciation
from .models import ShiftTiming
from .models import Attendance
from .models import AllowedIP
from .models import Shift_Roster
from .models import PickUpPoint
from .models import UserTargetsDelails
from .models import AdminBankDetails
from .models import QcTable
from .models import StickyNote
from .models import CustomAuthGroup,CompanyInquiry,Enquiry                       
admin.site.register(CompanyInquiry)
admin.site.register(Enquiry)
admin.site.register(Company)
admin.site.register(Package)
admin.site.register(PackageDetailsModel)
admin.site.register(Employees)
admin.site.register(Notice1)
admin.site.register(Branch)
admin.site.register(Module)
admin.site.register(FormEnquiry)
admin.site.register(SupportTicket)
admin.site.register(Department)
admin.site.register(Designation)
admin.site.register(Leaves)
admin.site.register(Holiday)
admin.site.register(Award)
admin.site.register(Appreciation)
admin.site.register(ShiftTiming)
admin.site.register(Attendance)
admin.site.register(AllowedIP)
admin.site.register(Shift_Roster)
admin.site.register(PickUpPoint)
admin.site.register(UserTargetsDelails)
admin.site.register(AdminBankDetails)
admin.site.register(QcTable)
admin.site.register(StickyNote)
admin.site.register(CustomAuthGroup)
admin.site.register(ExpiringToken)
admin.site.register(LoginLog)
admin.site.register(LoginAttempt)
admin.site.register(OTPAttempt)
admin.site.register(InterviewApplication)