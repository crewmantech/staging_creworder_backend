from rest_framework import serializers
from .models import Brand, Feature, Newsletter, Slider, ProductFeature, Testimonial, Client, AboutCompany, Highlight, VersionRelease

class SliderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Slider
        fields = '__all__'

class ProductFeatureSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductFeature
        fields = '__all__'

class TestimonialSerializer(serializers.ModelSerializer):
    class Meta:
        model = Testimonial
        fields = '__all__'

class ClientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Client
        fields = '__all__'


class SocialMediaSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    logo = serializers.ImageField()  # Or use URLField if you want to allow URL inputs
    url = serializers.URLField()

class AboutCompanySerializer(serializers.ModelSerializer):
    socialmedia = SocialMediaSerializer(many=True)  # Allows multiple social media entries

    class Meta:
        model = AboutCompany
        fields = '__all__'


class HighlightSerializer(serializers.ModelSerializer):
    class Meta:
        model = Highlight
        fields = '__all__'

class NewsletterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Newsletter
        fields = '__all__'

class BrandSerializer(serializers.ModelSerializer):
    class Meta:
        model = Brand
        fields = '__all__'


class FeatureSerializer(serializers.ModelSerializer):
    class Meta:
        model = Feature
        fields = ['bullet']


class VersionReleaseSerializer(serializers.ModelSerializer):
    features = serializers.ListField(
        child=serializers.CharField(), write_only=True
    )
    feature_list = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = VersionRelease
        fields = ['id', 'version', 'release_date', 'description', 'features', 'feature_list']

    def get_feature_list(self, obj):
        return [feature.bullet for feature in obj.features.all()]

    def create(self, validated_data):
        features_data = validated_data.pop('features', [])
        version_release = VersionRelease.objects.create(**validated_data)
        Feature.objects.bulk_create([
            Feature(version_release=version_release, bullet=bullet)
            for bullet in features_data
        ])
        return version_release

    def update(self, instance, validated_data):
        features_data = validated_data.pop('features', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if features_data is not None:
            instance.features.all().delete()
            Feature.objects.bulk_create([
                Feature(version_release=instance, bullet=bullet)
                for bullet in features_data
            ])

        return instance