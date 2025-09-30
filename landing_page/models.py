from django.utils import timezone
from django.db import models
from django.contrib.auth.models import User
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

# Slider Section Model
class Slider(BaseModel):
    image = models.ImageField(upload_to='slider_images/')
    heading = models.CharField(max_length=255)
    subheading = models.CharField(max_length=255)
    button1 = models.CharField(max_length=255)
    button2 = models.CharField(max_length=255)
    # created_at = models.DateTimeField(auto_now_add=True,default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)  
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.heading

# Product Feature Model
class ProductFeature(BaseModel):
    heading = models.CharField(max_length=255)
    subheading = models.CharField(max_length=255)
    image = models.ImageField(upload_to='product_feature_images/')
    url = models.URLField()
    # created_at = models.DateTimeField(auto_now_add=True,default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)  
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.heading

# Testimonial Model
class Testimonial(BaseModel):
    name = models.CharField(max_length=255)
    designation = models.CharField(max_length=255)
    profile_img = models.ImageField(upload_to='testimonial_images/')
    message = models.TextField()
    # created_at = models.DateTimeField(auto_now_add=True,default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)  
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

# Client Model
class Client(BaseModel):
    name = models.CharField(max_length=255)
    url = models.URLField()
    logo = models.ImageField(upload_to='client_logos/')
    # created_at = models.DateTimeField(auto_now_add=True,default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)  
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

# About Company Model
class AboutCompany(BaseModel):
    about = models.TextField()
    company = models.CharField(max_length=255)
    logo = models.ImageField(upload_to='about_company_logos/')
    socialmedia = models.JSONField(default=list)  # To store social media data
    # created_at = models.DateTimeField(auto_now_add=True,default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)  
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.company

# Highlight Section Model
class Highlight(BaseModel):
    title = models.CharField(max_length=255)
    image = models.ImageField(upload_to='highlight_images/')
    description = models.TextField()
    # created_at = models.DateTimeField(auto_now_add=True,default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)  
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title


class Newsletter(BaseModel):
    email = models.EmailField(max_length=100, unique=True, null=False)



class Brand(models.Model):
    name = models.CharField(max_length=255)
    number = models.CharField(max_length=20)
    email = models.EmailField()

    dark_logo = models.FileField(upload_to='brand_logos/', null=True, blank=True)
    light_logo = models.FileField(upload_to='brand_logos/', null=True, blank=True)
    dark_small_icon = models.FileField(upload_to='brand_small/', null=True, blank=True)
    light_small_icon = models.FileField(upload_to='brand_small/', null=True, blank=True)
    favicon = models.FileField(upload_to='brand_favicons/', null=True, blank=True)
    loader = models.FileField(upload_to='brand_loader/', null=True, blank=True)
    theme_color_code = models.CharField(max_length=10)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
    

class VersionRelease(models.Model):
    version = models.CharField(max_length=20)
    release_date = models.DateField()
    description = models.TextField()

class Feature(models.Model):
    version_release = models.ForeignKey(VersionRelease, related_name='features', on_delete=models.CASCADE)
    bullet = models.TextField()