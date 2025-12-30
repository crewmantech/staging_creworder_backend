from django.utils import timezone
from django.http import QueryDict
from dateutil import parser
import pytz

IST = pytz.timezone("Asia/Kolkata")

class ForceISTDateTimeMiddleware:
    """
    Force all incoming datetime fields to Indian Standard Time (IST)
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        # Only apply to write operations
        if request.method in ["POST", "PUT", "PATCH"] and request.body:
            try:
                if request.content_type == "application/json":
                    import json
                    data = json.loads(request.body)

                    for key, value in data.items():
                        if self._is_datetime(value):
                            data[key] = self._convert_to_ist(value)

                    request._body = json.dumps(data).encode("utf-8")

                elif request.content_type == "application/x-www-form-urlencoded":
                    mutable = QueryDict(request.body, mutable=True)
                    for key, value in mutable.items():
                        if self._is_datetime(value):
                            mutable[key] = self._convert_to_ist(value)

                    request.POST = mutable

            except Exception:
                pass  # never break API

        return self.get_response(request)

    def _is_datetime(self, value):
        if not isinstance(value, str):
            return False
        try:
            parser.parse(value)
            return "T" in value
        except Exception:
            return False

    def _convert_to_ist(self, value):
        dt = parser.parse(value)

        # If naive datetime, assume IST
        if timezone.is_naive(dt):
            dt = IST.localize(dt)
        else:
            dt = dt.astimezone(IST)

        return dt.isoformat()
