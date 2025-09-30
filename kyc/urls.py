from rest_framework.routers import DefaultRouter
from .views import AadhaarOTPVerificationView, AadhaarVerificationView, BankAccountVerificationPennyDropView, BankAccountVerificationPennyLessView, BankIFSCVerificationView, GSTAndPANVerificationView, GSTSearchGSTINView, GSTStateViewSet, IncomeTaxForm16View, KYCViewSet, OTPViewSet, PANVerificationView, SearchGSTINView, SearchTANView, TDSCalculatorView, TaxPLReportView, TrackGSTReturnsView, VerifyPANDetailsView
from django.urls import include, path
router = DefaultRouter()
router.register(r'kyc', KYCViewSet)
router.register(r'gst_state', GSTStateViewSet)
router.register(r'otp', OTPViewSet, basename='otp')
urlpatterns = [
    path('', include(router.urls)),
    path("kyc/aadhaar/", AadhaarVerificationView.as_view(), name="aadhaar-verification"),
    path('aadhaar/otp/', AadhaarOTPVerificationView.as_view(), name='aadhaar_otp'),
    path("bank/ifsc/", BankIFSCVerificationView.as_view(), name="ifsc-verification"),
    path("bank/account-verification/penny-drop/", BankAccountVerificationPennyDropView.as_view(), name="penny-drop-verification"),
    path("bank/account-verification/penny-less/", BankAccountVerificationPennyLessView.as_view(), name="penny-less-verification"),
    path("mca/pan/", PANVerificationView.as_view(), name="pan-verification"),
    path("mca/tan/", SearchTANView.as_view(), name="tan-search"),
    path("gst/compliance/search/", SearchGSTINView.as_view(), name="gstin-search"),
    path("income-tax/form16/", IncomeTaxForm16View.as_view(), name="income-tax-form16"),
    path("tax-pl/report/", TaxPLReportView.as_view(), name="tax-pl-report"),
    path("gst/public/search/", GSTSearchGSTINView.as_view(), name="gst-public-search"),
    path("gst/returns/track/", TrackGSTReturnsView.as_view(), name="gst-returns-track"),
    path("tds/verify-pan/", VerifyPANDetailsView.as_view(), name="tds-verify-pan"),
    path("tds/calculator/", TDSCalculatorView.as_view(), name="tds-calculator"),
    path("verify-pan-gst/", GSTAndPANVerificationView.as_view(), name="verify-pan-gst"),
]
