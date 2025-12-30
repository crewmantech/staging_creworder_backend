from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.contrib.contenttypes.models import ContentType
from .models import ActivityLog
from .serializers import ActivityLogSerializer

class ActivityLogListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Query Params:
        ?module=lead / appointment / follow_up
        ?object_id=LDI001
        ?company=12
        """

        logs = ActivityLog.objects.select_related(
            "content_type", "performed_by"
        ).all()

        module = request.GET.get("module")
        object_id = request.GET.get("object_id")
        company_id = request.GET.get("company")

        # 🔹 Filter by module
        if module:
            try:
                ct = ContentType.objects.get(model=module)
                logs = logs.filter(content_type=ct)
            except ContentType.DoesNotExist:
                return Response({"error": "Invalid module"}, status=400)

        # 🔹 Filter by object id
        if object_id:
            logs = logs.filter(object_id=object_id)

        # 🔹 Company-wise filter (SAFE)
        if company_id:
            valid_ids = []
            for log in logs:
                obj = log.content_object
                if hasattr(obj, "company") and obj.company and str(obj.company.id) == company_id:
                    valid_ids.append(log.id)
            logs = logs.filter(id__in=valid_ids)

        serializer = ActivityLogSerializer(logs.order_by("-created_at"), many=True)
        return Response(serializer.data)
