from .models import Notif, UserNotif
from django.db.models import Q

# def notification_count(request):
#     notif_count = 0  # Default count for anonymous users or fallback

#     if request.user.is_authenticated:
#         user = request.user
        
#         if user.is_superuser:
#             # Count unread notifications for non-superuser created notifications
#             notif_count = Notif.objects.filter(
#                 created_by__is_superuser=False
#             ).exclude(read_by=user).count()
#         else:
#             # Count unread notifications for superuser created notifications
#             notif_count = Notif.objects.filter(
#                 created_by__is_superuser=True
#             ).exclude(read_by=user).count()

#     return {'notif_count': notif_count}

def notification_count(request):
    notif_count = 0  # Default count for anonymous users or fallback

    if request.user.is_authenticated:
        user = request.user
        
        if user.is_superuser:
            # Superusers count unread notifications not created by other superusers
            notif_count = Notif.objects.filter(
                created_by__is_superuser=False
            ).exclude(read_by=user).count()
        else:
            # Regular users:
            # Count general unread notifications (created by superusers)
            general_notif_count = Notif.objects.filter(
                created_by__is_superuser=True
            ).exclude(
                Q(read_by=user) | Q(personal_notif=True)
            ).count()

            # Count targeted unread notifications for the logged-in user
            targeted_notif_count = UserNotif.objects.filter(
                user=user,
                read=False  # Only unread notifications
            ).count()

            print("general_notif_count: ", general_notif_count)
            print("targeted_notif_count: ", targeted_notif_count)

            # Total notification count
            notif_count = general_notif_count + targeted_notif_count

    return {'notif_count': notif_count}

