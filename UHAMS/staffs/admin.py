from django.contrib import admin

from staffs.models import AmbulanceCall, StaffAssignment, StaffProfile, VacationRecord


@admin.register(StaffProfile)
class StaffProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "title", "role", "department", "access_level", "availability_status")
    list_filter = ("role", "access_level", "availability_status")
    search_fields = ("user__username", "user__first_name", "user__last_name", "department")


admin.site.register(StaffAssignment)


@admin.register(VacationRecord)
class VacationRecordAdmin(admin.ModelAdmin):
    list_display = ("staff", "start_date", "end_date", "status", "reviewed_by")
    list_filter = ("status",)


@admin.register(AmbulanceCall)
class AmbulanceCallAdmin(admin.ModelAdmin):
    list_display = ("location", "status", "ambulance", "handled_by", "created_at")
    list_filter = ("status",)
