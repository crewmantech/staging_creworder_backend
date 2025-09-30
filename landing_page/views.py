from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Brand, Newsletter, Slider, ProductFeature, Testimonial, Client, AboutCompany, Highlight, VersionRelease
from .serializers import BrandSerializer, NewsletterSerializer, SliderSerializer, ProductFeatureSerializer, TestimonialSerializer, ClientSerializer, AboutCompanySerializer, HighlightSerializer, VersionReleaseSerializer
from .permissions import ReadOnlyOrAuthenticated
from rest_framework import viewsets

# Slider API View
class SliderAPIView(APIView):
    permission_classes = [ReadOnlyOrAuthenticated]
    def get(self, request, id=None):
        if id:
            try:
                slider = Slider.objects.get(id=id)
                serializer = SliderSerializer(slider)
                return Response(
                    {"Success": True, "Data": serializer.data},
                    status=status.HTTP_200_OK,
                )
            except Slider.DoesNotExist:
                return Response(
                    {"Success": False, "Message": "Not found."},
                    status=status.HTTP_404_NOT_FOUND,
                )
        else:
            sliders = Slider.objects.all()
            serializer = SliderSerializer(sliders, many=True)
            return Response(
                {"Success": True, "Data": serializer.data},
                status=status.HTTP_200_OK,
            )

    def post(self, request):
        serializer = SliderSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {"Success": True, "Data": serializer.data},
                status=status.HTTP_201_CREATED,
            )
        return Response(
            {"Success": False, "Errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )

    def put(self, request, id):
        try:
            slider = Slider.objects.get(id=id)
        except Slider.DoesNotExist:
            return Response(
                {"Success": False, "Message": "Not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        
        serializer = SliderSerializer(slider, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {"Success": True, "Data": serializer.data},
                status=status.HTTP_200_OK,
            )
        return Response(
            {"Success": False, "Errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )

    def delete(self, request, id):
        try:
            slider = Slider.objects.get(id=id)
            slider.delete()
            return Response(
                {"Success": True, "Message": "Deleted successfully."},
                status=status.HTTP_204_NO_CONTENT,
            )
        except Slider.DoesNotExist:
            return Response(
                {"Success": False, "Message": "Not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

# Product Feature API View
class ProductFeatureAPIView(APIView):
    permission_classes = [ReadOnlyOrAuthenticated]
    def get(self, request, id=None):
        if id:
            try:
                product_feature = ProductFeature.objects.get(id=id)
                serializer = ProductFeatureSerializer(product_feature)
                return Response(
                    {"Success": True, "Data": serializer.data},
                    status=status.HTTP_200_OK,
                )
            except ProductFeature.DoesNotExist:
                return Response(
                    {"Success": False, "Message": "Not found."},
                    status=status.HTTP_404_NOT_FOUND,
                )
        else:
            product_features = ProductFeature.objects.all()
            serializer = ProductFeatureSerializer(product_features, many=True)
            return Response(
                {"Success": True, "Data": serializer.data},
                status=status.HTTP_200_OK,
            )

    def post(self, request):
        serializer = ProductFeatureSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {"Success": True, "Data": serializer.data},
                status=status.HTTP_201_CREATED,
            )
        return Response(
            {"Success": False, "Errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )

    def put(self, request, id):
        try:
            product_feature = ProductFeature.objects.get(id=id)
        except ProductFeature.DoesNotExist:
            return Response(
                {"Success": False, "Message": "Not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        
        serializer = ProductFeatureSerializer(product_feature, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {"Success": True, "Data": serializer.data},
                status=status.HTTP_200_OK,
            )
        return Response(
            {"Success": False, "Errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )

    def delete(self, request, id):
        try:
            product_feature = ProductFeature.objects.get(id=id)
            product_feature.delete()
            return Response(
                {"Success": True, "Message": "Deleted successfully."},
                status=status.HTTP_204_NO_CONTENT,
            )
        except ProductFeature.DoesNotExist:
            return Response(
                {"Success": False, "Message": "Not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

# Testimonial API View
class TestimonialAPIView(APIView):
    permission_classes = [ReadOnlyOrAuthenticated]
    def get(self, request, id=None):
        if id:
            try:
                testimonial = Testimonial.objects.get(id=id)
                serializer = TestimonialSerializer(testimonial)
                return Response(
                    {"Success": True, "Data": serializer.data},
                    status=status.HTTP_200_OK,
                )
            except Testimonial.DoesNotExist:
                return Response(
                    {"Success": False, "Message": "Not found."},
                    status=status.HTTP_404_NOT_FOUND,
                )
        else:
            testimonials = Testimonial.objects.all()
            serializer = TestimonialSerializer(testimonials, many=True)
            return Response(
                {"Success": True, "Data": serializer.data},
                status=status.HTTP_200_OK,
            )

    def post(self, request):
        serializer = TestimonialSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {"Success": True, "Data": serializer.data},
                status=status.HTTP_201_CREATED,
            )
        return Response(
            {"Success": False, "Errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )

    def put(self, request, id):
        try:
            testimonial = Testimonial.objects.get(id=id)
        except Testimonial.DoesNotExist:
            return Response(
                {"Success": False, "Message": "Not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        
        serializer = TestimonialSerializer(testimonial, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {"Success": True, "Data": serializer.data},
                status=status.HTTP_200_OK,
            )
        return Response(
            {"Success": False, "Errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )

    def delete(self, request, id):
        try:
            testimonial = Testimonial.objects.get(id=id)
            testimonial.delete()
            return Response(
                {"Success": True, "Message": "Deleted successfully."},
                status=status.HTTP_204_NO_CONTENT,
            )
        except Testimonial.DoesNotExist:
            return Response(
                {"Success": False, "Message": "Not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

# Client API View
class ClientAPIView(APIView):
    permission_classes = [ReadOnlyOrAuthenticated]
    def get(self, request, id=None):
        if id:
            try:
                client = Client.objects.get(id=id)
                serializer = ClientSerializer(client)
                return Response(
                    {"Success": True, "Data": serializer.data},
                    status=status.HTTP_200_OK,
                )
            except Client.DoesNotExist:
                return Response(
                    {"Success": False, "Message": "Not found."},
                    status=status.HTTP_404_NOT_FOUND,
                )
        else:
            clients = Client.objects.all()
            serializer = ClientSerializer(clients, many=True)
            return Response(
                {"Success": True, "Data": serializer.data},
                status=status.HTTP_200_OK,
            )

    def post(self, request):
        serializer = ClientSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {"Success": True, "Data": serializer.data},
                status=status.HTTP_201_CREATED,
            )
        return Response(
            {"Success": False, "Errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )

    def put(self, request, id):
        try:
            client = Client.objects.get(id=id)
        except Client.DoesNotExist:
            return Response(
                {"Success": False, "Message": "Not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        
        serializer = ClientSerializer(client, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {"Success": True, "Data": serializer.data},
                status=status.HTTP_200_OK,
            )
        return Response(
            {"Success": False, "Errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )

    def delete(self, request, id):
        try:
            client = Client.objects.get(id=id)
            client.delete()
            return Response(
                {"Success": True, "Message": "Deleted successfully."},
                status=status.HTTP_204_NO_CONTENT,
            )
        except Client.DoesNotExist:
            return Response(
                {"Success": False, "Message": "Not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

# About Company API View
class AboutCompanyAPIView(APIView):
    permission_classes = [ReadOnlyOrAuthenticated]
    def get(self, request, id=None):
        if id:
            try:
                about_company = AboutCompany.objects.get(id=id)
                serializer = AboutCompanySerializer(about_company)
                return Response(
                    {"Success": True, "Data": serializer.data},
                    status=status.HTTP_200_OK,
                )
            except AboutCompany.DoesNotExist:
                return Response(
                    {"Success": False, "Message": "Not found."},
                    status=status.HTTP_404_NOT_FOUND,
                )
        else:
            about_companies = AboutCompany.objects.all()
            serializer = AboutCompanySerializer(about_companies, many=True)
            return Response(
                {"Success": True, "Data": serializer.data},
                status=status.HTTP_200_OK,
            )

    def post(self, request):
        serializer = AboutCompanySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {"Success": True, "Data": serializer.data},
                status=status.HTTP_201_CREATED,
            )
        return Response(
            {"Success": False, "Errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )

    def put(self, request, id):
        try:
            about_company = AboutCompany.objects.get(id=id)
        except AboutCompany.DoesNotExist:
            return Response(
                {"Success": False, "Message": "Not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = AboutCompanySerializer(about_company, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {"Success": True, "Data": serializer.data},
                status=status.HTTP_200_OK,
            )
        return Response(
            {"Success": False, "Errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )

    def delete(self, request, id):
        try:
            about_company = AboutCompany.objects.get(id=id)
            about_company.delete()
            return Response(
                {"Success": True, "Message": "Deleted successfully."},
                status=status.HTTP_204_NO_CONTENT,
            )
        except AboutCompany.DoesNotExist:
            return Response(
                {"Success": False, "Message": "Not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

# Highlight API View
class HighlightAPIView(APIView):
    permission_classes = [ReadOnlyOrAuthenticated]
    def get(self, request, id=None):
        if id:
            try:
                highlight = Highlight.objects.get(id=id)
                serializer = HighlightSerializer(highlight)
                return Response(
                    {"Success": True, "Data": serializer.data},
                    status=status.HTTP_200_OK,
                )
            except Highlight.DoesNotExist:
                return Response(
                    {"Success": False, "Message": "Not found."},
                    status=status.HTTP_404_NOT_FOUND,
                )
        else:
            highlights = Highlight.objects.all()
            serializer = HighlightSerializer(highlights, many=True)
            return Response(
                {"Success": True, "Data": serializer.data},
                status=status.HTTP_200_OK,
            )

    def post(self, request):
        serializer = HighlightSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {"Success": True, "Data": serializer.data},
                status=status.HTTP_201_CREATED,
            )
        return Response(
            {"Success": False, "Errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )

    def put(self, request, id):
        try:
            highlight = Highlight.objects.get(id=id)
        except Highlight.DoesNotExist:
            return Response(
                {"Success": False, "Message": "Not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        
        serializer = HighlightSerializer(highlight, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {"Success": True, "Data": serializer.data},
                status=status.HTTP_200_OK,
            )
        return Response(
            {"Success": False, "Errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )

    def delete(self, request, id):
        try:
            highlight = Highlight.objects.get(id=id)
            highlight.delete()
            return Response(
                {"Success": True, "Message": "Deleted successfully."},
                status=status.HTTP_204_NO_CONTENT,
            )
        except Highlight.DoesNotExist:
            return Response(
                {"Success": False, "Message": "Not found."},
                status=status.HTTP_404_NOT_FOUND,
            )



class NewsletterViewSet(viewsets.ModelViewSet):
    queryset = Newsletter.objects.all()
    serializer_class = NewsletterSerializer

from rest_framework.parsers import MultiPartParser, FormParser
class BrandViewSet(viewsets.ModelViewSet):
    queryset = Brand.objects.all()
    serializer_class = BrandSerializer
    parser_classes = [MultiPartParser, FormParser]
    permission_classes = [ReadOnlyOrAuthenticated] 


class VersionReleaseViewSet(viewsets.ModelViewSet):
    queryset = VersionRelease.objects.all()
    serializer_class = VersionReleaseSerializer
    permission_classes = [ReadOnlyOrAuthenticated] 