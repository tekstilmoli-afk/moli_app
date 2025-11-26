from django.contrib.auth import logout
from django.utils import timezone
from datetime import timedelta

class CustomSessionTimeoutMiddleware:
    EXCLUDED_USERS = ["mustafakanyis", "oguzhankanyis", "mehmet"]  # ATILMAYACAK KULLANICILAR
    TIMEOUT_MINUTES = 15  # diğer kullanıcıların timeout süresi

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:

            # --- Bu kullanıcılar asla timeout olmasın ---
            if request.user.username in self.EXCLUDED_USERS:
                return self.get_response(request)

            now = timezone.now()
            last_activity = request.session.get("last_activity")

            if last_activity:
                elapsed = now - timezone.datetime.fromisoformat(last_activity)

                # 15 dakika geçtiyse çıkış yapılır
                if elapsed > timedelta(minutes=self.TIMEOUT_MINUTES):
                    logout(request)

            request.session["last_activity"] = now.isoformat()

        return self.get_response(request)
