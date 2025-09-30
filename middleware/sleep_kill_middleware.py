import threading

from accounts.utils import check_and_kill_sleep_queries




class SleepQueryCleanerMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Run cleanup in background thread
        thread = threading.Thread(target=check_and_kill_sleep_queries, daemon=True)
        thread.start()

        # Return response immediately
        response = self.get_response(request)
        return response