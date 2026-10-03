"""Registers the staff-related models in the /admin/ site, with list columns,
filters and search boxes that make browsing them practical."""
from django.contrib import admin

from staffs.models import AmbulanceCall, StaffAssignment, StaffProfile, VacationRecord


@admin.register(StaffProfile)   # same as admin.site.register(StaffProfile, StaffProfileAdmin)
class StaffProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "title", "role", "department", "access_level", "availability_status")   # table columns
    list_filter = ("role", "access_level", "availability_status")   # filter sidebar
    # "user__username" follows the relation to the User table.
    search_fields = ("user__username", "user__first_name", "user__last_name", "department")


# Plain registration (default admin screens) is enough for the assignment history.
admin.site.register(StaffAssignment)


@admin.register(VacationRecord)
class VacationRecordAdmin(admin.ModelAdmin):
    list_display = ("staff", "start_date", "end_date", "status", "reviewed_by")
    list_filter = ("status",)


@admin.register(AmbulanceCall)
class AmbulanceCallAdmin(admin.ModelAdmin):
    list_display = ("location", "status", "ambulance", "handled_by", "created_at")
    list_filter = ("status",)
