from django.contrib import admin
from .models import GroupInfoTH, Schedule, GroupInfoPOD, SchedulePOD, GroupInfoMD, ScheduleMD, GroupInfoFD, ScheduleFD 
  
# Register your models here.
admin.site.register(GroupInfoTH)
admin.site.register(Schedule)

admin.site.register(GroupInfoPOD)
admin.site.register(SchedulePOD)

admin.site.register(GroupInfoMD)
admin.site.register(ScheduleMD)

admin.site.register(GroupInfoFD)
admin.site.register(ScheduleFD)