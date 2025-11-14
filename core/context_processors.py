# context_processors.py
from .models import Notification

def notifications(request):
    if request.user.is_authenticated:
        all_notifications = Notification.objects.filter(user=request.user).order_by('-timestamp')
        unread_notification_count = all_notifications.filter(is_read=False).count()
    else:
        all_notifications = Notification.objects.none()
        unread_notification_count = 0

    return {
        "all_notifications": all_notifications,
        "unread_notification_count": unread_notification_count,
    }
