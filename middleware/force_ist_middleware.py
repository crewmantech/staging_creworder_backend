import json
import pytz
from dateutil import parser
from django.utils import timezone
from django.http import QueryDict

IST = pytz.timezone("Asia/Kolkata")

class ForceISTDateTimeMiddleware:
    """
    Force ALL incoming datetime values into Indian Standard Time (IST)
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
                pass

        return self.get_response(request)

    # =========================
    # Helpers
    # =========================
    def _process_data(self, data):
        if isinstance(data, dict):
            for k, v in data.items():
                data[k] = self._process_data(v)
        elif isinstance(data, list):
            return [self._process_data(i) for i in data]
        else:
            return self._process_value(data)
        return data

    def _process_value(self, value):
        if not isinstance(value, str):
            return value

        try:
            dt = parser.parse(value)

            # If datetime is naive → assume IST
            if timezone.is_naive(dt):
                dt = IST.localize(dt)
            else:
                dt = dt.astimezone(IST)

            return dt.isoformat()
        except Exception:
            return value
