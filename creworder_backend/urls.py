"""
URL configuration for creworder_backend project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from . import views

from creworder_backend.views import CustomLoginView,VerifyOTPView,LogoutView

urlpatterns = [
    path('superadmin/', admin.site.urls),
    path('', views.welcome, name='welcome'),
    path('api/', include('accounts.urls')),
    path('api/', include('orders.urls')),
    path('api/', include('chat.urls')),
    path('api/', include('follow_up.urls')),
    path('api/', include('cloud_telephony.urls')),
    path('api/', include('lead_management.urls')),
    path('api/', include('shipment.urls')),
    path('api/', include('dashboard.urls')),
    path('api/', include('superadmin_assets.urls')),
    path('api/', include('landing_page.urls')),
    path('api/', include('emailsetup.urls')),
    path('api/', include('kyc.urls')),
    # path('dj-rest-auth/', include('dj_rest_auth.urls')),
    path('dj-rest-auth/login/', CustomLoginView.as_view(), name='rest_login'),
    path('api/login-otp-verify/', VerifyOTPView.as_view(), name='rest_otp'),
    path('api/logout/', LogoutView.as_view(), name='rest_logout'),
]+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
