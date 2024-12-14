from .models import Notif

def notification_count(request):
    notif_count = 0  # Default count for anonymous users or fallback

    if request.user.is_authenticated:
        user = request.user
        
        if user.is_superuser:
            # Count unread notifications for non-superuser created notifications
            notif_count = Notif.objects.filter(
                created_by__is_superuser=False
            ).exclude(read_by=user).count()
        else:
            # Count unread notifications for superuser created notifications
            notif_count = Notif.objects.filter(
                created_by__is_superuser=True
            ).exclude(read_by=user).count()

    return {'notif_count': notif_count}
