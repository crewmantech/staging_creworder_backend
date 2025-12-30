import json
import pytz
from dateutil import parser
from django.utils import timezone
from django.http import QueryDict

IST = pytz.timezone("Asia/Kolkata")

class ForceISTDateTimeMiddleware:
    """
    - If datetime is already IST (+05:30) → keep it
    - If datetime is any other timezone → convert to IST
    - If datetime is naive → assume IST
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        if request.method in ("POST", "PUT", "PATCH") and request.body:
            try:
                if "application/json" in request.content_type:
                    data = json.loads(request.body)
                    data = self._process_data(data)
                    request._body = json.dumps(data).encode("utf-8")

                elif "application/x-www-form-urlencoded" in request.content_type:
                    mutable = QueryDict(request.body, mutable=True)
                    for key, value in mutable.items():
                        mutable[key] = self._process_value(value)
                    request.POST = mutable

            except Exception:
                pass  # never break API

        return self.get_response(request)

    # =========================
    # Helpers
    # =========================
    def _process_data(self, data):
        if isinstance(data, dict):
            return {k: self._process_data(v) for k, v in data.items()}
        if isinstance(data, list):
            return [self._process_data(i) for i in data]
        return self._process_value(data)

    def _process_value(self, value):
        if not isinstance(value, str):
            return value

        try:
            dt = parser.parse(value)

            # Naive datetime → assume IST
            if timezone.is_naive(dt):
                return IST.localize(dt).isoformat()

            # Already IST → DO NOT CHANGE
            if dt.utcoffset().total_seconds() == 19800:  # 5.5 hrs
                return dt.isoformat()

            # Other timezone → convert to IST
            return dt.astimezone(IST).isoformat()

        except Exception:
            return value
