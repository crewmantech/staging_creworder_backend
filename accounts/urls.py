from django.urls import path, include
from rest_framework.routers import DefaultRouter

from follow_up.views import DoctorViewSet
from .views import AgentAttendanceUserWiseAPIView, AgreementViewSet, AssignRole,AgentListByManagerAPIView, AgentListByTeamleadAPIView, CSVUserUploadView, CompanyInquiryViewSet, CompanyMonthlySalaryPreviewAPIView, CompanyMonthlySummaryView, CompanySalaryViewSet, CompanyUserAPIKeyViewSet, CompanyUserViewSet, CustomPasswordResetView, DeleteUserListView, EnquiryViewSet, ForceLogoutView, InterviewApplicationViewSet, ManagerTeamLeadAgentAPIView, ManagerViewSet, MonthlyCompanyStatsView, QcScoreViewSet, ReminderNotesViewSet, ResetPasswordAPIView, StickyNoteViewSet, TeamleadViewSet, UpdateTeamLeadManagerAPIView, UserExportView, UserPermissionStatusView, UserViewSet, CompanyViewSet, PackageViewSet, UserPermissionsView, \
    UserProfileViewSet, \
    NoticeViewSet, BranchViewSet, AdminSelfSignUp, FormEnquiryViewSet, SupportTicketViewSet, ModuleViewSet, \
    GetSpecificUsers, \
    GetNoticesForUser, DepartmentViewSet, DesignationViewSet, LeaveViewSet, HolidayViewSet, AwardViewSet, \
    AppreciationViewSet, ShiftViewSet, AttendanceViewSet, Testing, GetUsernameSuggestions, AttendanceView, \
    IPRestrictedLoginView,ShiftRosterViewSet,GetPackageModule,CustomAuthGroupViewSet,UserGroupViewSet,\
    GroupPermissionViewSet,PermmisionViewSet,FetchPermissionView,PickUpPointView,TargetView,AdminBankDetailsViewSet,\
    AddAllowIpViewSet,QcViewSet,GetPackagesModule , UserTargetsDelailsFilterAPIView, UsersTeamAPIView, UsersWithTargetsAPIView,UsersNdrAPIView,UserMonthlyPerformanceAPIView

router = DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'companies', CompanyViewSet)
router.register(r'packages', PackageViewSet)
# router.register(r'user-roles', UserRoleViewSet)
router.register(r'user-profiles', UserProfileViewSet)
router.register(r'notices', NoticeViewSet)
router.register(r'branches', BranchViewSet)
router.register(r'form-enquiries', FormEnquiryViewSet)
router.register(r'support-tickets', SupportTicketViewSet)
router.register(r'modules', ModuleViewSet)
router.register(r'departments', DepartmentViewSet)
router.register(r'designations', DesignationViewSet)
router.register(r'leaves', LeaveViewSet)
router.register(r'holidays', HolidayViewSet)
router.register(r'awards', AwardViewSet)
router.register(r'appreciations', AppreciationViewSet)
router.register(r'shifts', ShiftViewSet)
router.register(r'shiftroster', ShiftRosterViewSet, basename='shiftroster')
router.register(r'attendances', AttendanceViewSet)
router.register(r'get-module', GetPackageModule,basename='get-module')
router.register(r'get-url', GetPackagesModule,basename='get-url')
router.register(r'auth-role-group',CustomAuthGroupViewSet,basename='auth-role')
router.register(r'user-group', UserGroupViewSet, basename='user-group')
router.register(r'group-permissions', GroupPermissionViewSet, basename='group-permissions')
router.register(r'pick-up-point', PickUpPointView, basename='pickup-point')
router.register(r'user-target', TargetView, basename='user-target')
router.register(r'bank-details', AdminBankDetailsViewSet, basename='admin-bank-details')
router.register(r'add-ip-forlogin', AddAllowIpViewSet, basename='add-ip-forlogin')
router.register(r'qc',QcViewSet,basename='qc')
router.register(r'notes', StickyNoteViewSet, basename='stickynote')
router.register(r'inquiries', CompanyInquiryViewSet)
router.register(r'enquiries', EnquiryViewSet, basename='enquiry')
router.register(r'company-users', CompanyUserViewSet, basename='company-user')
router.register(r'agreements', AgreementViewSet, basename='agreement')
router.register(r'qcscore', QcScoreViewSet, basename='qcscore')
router.register(r'assign-company-user', CompanyUserAPIKeyViewSet, basename='assign-company-user')
router.register(r'reminder-notes', ReminderNotesViewSet, basename='remindernotes')
router.register(r"interviews", InterviewApplicationViewSet, basename="interview")
router.register(r"company-salary", CompanySalaryViewSet, basename="company-salary")
router.register(r"doctors", DoctorViewSet, basename="doctor")
# router.register(r'assign-role',AssignRole,basename='assign-role')
urlpatterns = [
    path('', include(router.urls)),
    path('users-with-targets/', UsersWithTargetsAPIView.as_view(), name='users-with-targets'),
    path('user-permission-status/', UserPermissionStatusView.as_view(), name='user_permission_status'),
    path('user-permissions/', UserPermissionsView.as_view(), name="user-permissions"),
    path('self-signup/', AdminSelfSignUp.as_view(), name="self-signup"),
    path('specific-users/', GetSpecificUsers.as_view(), name="specific-users"),
    path('user-notices/', GetNoticesForUser.as_view(), name="user-notices"),
    path('username-suggestions/', GetUsernameSuggestions.as_view(), name="username-suggestions"),
    path('get-attendance/', AttendanceView.as_view(), name='get-attendance'),
    path('get-permission-ids/', FetchPermissionView.as_view(), name='fetch-permissions'),
    path('testing/', Testing.as_view(), name="testing"),
    #path('update-agent-teamlead-manager/',UpdateTeamleadManagerAPIView.as_view(),name ='update-teamlead-manager'),
    # get manager and teamlead under all agent
    path('assign-role/', AssignRole.as_view(), name='assign-role'),
    path('agents/by_manager/', AgentListByManagerAPIView.as_view(), name='agent-list-by-manager'),
    path('agents/by_teamlead/', AgentListByTeamleadAPIView.as_view(), name='agent-list-by-teamlead'),
    path('teamlead-users/', TeamleadViewSet.as_view(), name='teamlead_users'),
    path('manager-users/', ManagerViewSet.as_view(), name='manager_users'),
    path('teamlist/', ManagerTeamLeadAgentAPIView.as_view(), name='teamlist'),
    path('update-teamlead-manager/', UpdateTeamLeadManagerAPIView.as_view(), name='update-teamlead-manager'),
    path('force_logout/<int:user_id>/', ForceLogoutView.as_view(), name='force_logout'),
    path('user/bulk_upload/', CSVUserUploadView.as_view(), name='csv_user_upload'),
    path('user/export/', UserExportView.as_view(), name='user_export'),
    path('reset-password/<uidb64>/<token>/', ResetPasswordAPIView.as_view(), name='reset_password'),
    path('password/reset/', CustomPasswordResetView.as_view(), name='password_reset'),
    path('monthly-company-stats/', MonthlyCompanyStatsView.as_view(), name='monthly-company-stats'),
    path('user-targets/filter/', UserTargetsDelailsFilterAPIView.as_view(), name='user-targets-filter'),
    path('user-team/', UsersTeamAPIView.as_view(), name='user-team'),
    path("delete-users/", DeleteUserListView.as_view(), name="delete-user-list"),
    path('company-summary/', CompanyMonthlySummaryView.as_view(), name='company-monthly-summary'),
    path('ndr-users/', UsersNdrAPIView.as_view(), name='ndr-users'),
    path('attendance-summary/', AgentAttendanceUserWiseAPIView.as_view(), name='attendance-summary'),
    path('user-performance-dashboard/', UserMonthlyPerformanceAPIView.as_view(), name='user-monthly-performance'),
    path("company-salary-preview/",CompanyMonthlySalaryPreviewAPIView.as_view(),name="company-salary-preview",
)
]
