from django.utils import timezone
from django.conf import settings
from django.contrib.auth import logout

def get_user_profile(user):
    """UserProfile varsa getir, yoksa None döndür."""
    try:
        return user.userprofile
    except:
        return None

class UserBasedTimeoutMiddleware:
    """
    Kullanıcı bazlı timeout yönetimi yapan middleware.
    UserProfile içinde timeout_free=True olan kullanıcılar asla timeout olmaz.
    Diğer kullanıcılar SESSION_COOKIE_AGE kadar süre geçince otomatik logout edilir.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = request.user

        if user.is_authenticated:

            profile = get_user_profile(user)

            # Eğer kullanıcı timeout'tan muaf ise (patron, müdür vb.)
            if profile and profile.timeout_free:
                return self.get_response(request)

            now = timezone.now().timestamp()
            last = request.session.get("last_activity")

            # Timeout kontrolü (ör: 900 saniye = 15 dakika)
            if last and (now - last) > settings.SESSION_COOKIE_AGE:
                logout(request)

            # Her istekte son aktivite zamanını güncelle
            request.session["last_activity"] = now

        return self.get_response(request)
