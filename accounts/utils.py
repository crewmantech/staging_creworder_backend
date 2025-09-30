from rest_framework.response import Response
from rest_framework import status

def custom_response(success=True, message="", data=None, errors=None, status_code=200):
    return Response({
        "success": success,
        "message": message,
        "data": data if success else None,
        "errors": errors if not success else None,
        "status_code": status_code
    }, status=status_code)


import threading
from django.db import connections
import logging

logger = logging.getLogger(__name__)

def check_and_kill_sleep_queries():
    try:
        with connections['default'].cursor() as cursor:
            cursor.execute("SHOW PROCESSLIST")
            rows = cursor.fetchall()
            for row in rows:
                process_id = row[0]
                command = row[4]
                sleep_time = row[5]

                if command.lower() == 'sleep' and sleep_time > 30:
                    try:
                        cursor.execute(f"KILL {process_id}")
                        logger.info(f"Killed sleep query: {process_id} (sleep {sleep_time}s)")
                    except Exception as e:
                        logger.warning(f"Kill failed: {str(e)}")
    except Exception as e:
        logger.error(f"Sleep kill check failed: {str(e)}")