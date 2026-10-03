from django.contrib import admin

from staffs.models import AmbulanceCall, StaffAssignment, StaffProfile, VacationRecord


@admin.register(StaffProfile)
class StaffProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "title", "role", "department", "access_level", "availability_status")
    list_filter = ("role", "access_level", "availability_status")
    search_fields = ("user__username", "user__first_name", "user__last_name", "department")


admin.site.register(StaffAssignment)
admin.site.register(VacationRecord)
admin.site.register(AmbulanceCall)
