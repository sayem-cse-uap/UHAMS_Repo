"""
Permanent (301) redirects from the pre-restructure URLs to the current ones,
so existing bookmarks and links keep working. Safe to delete once no longer needed.

Background: the URLs used to be wordy and inconsistent (e.g. "staffs/staff-dashboard/",
"patients/patient-dashboard/"). They were later cleaned up to the short forms
documented in UHAMS/urls.py. Rather than break every saved bookmark, each old
path below simply answers "this moved permanently" and sends the browser to the
new location.
"""
from django.urls import path
from django.views.generic import RedirectView


def _go(old, new):
    """Build one redirect rule.

    old: the legacy URL path (may contain converters such as <int:pk>).
    new: the *name* of the current URL, e.g. 'staffs:dashboard'.

    RedirectView looks up `new` with reverse(), and because the old pattern
    captured values like <int:pk>/<int:doctor_id>, those are passed on to the
    new URL automatically. permanent=True makes it an HTTP 301, which tells
    browsers and search engines to remember the new address.
    """
    return path(old, RedirectView.as_view(pattern_name=new, permanent=True))


urlpatterns = [
    # core
    _go('register-new-user/', 'core:register'),

    # staffs/ -> staff/
    _go('staffs/register-staff/', 'staffs:register'),
    _go('staffs/staff-dashboard/', 'staffs:dashboard'),
    _go('staffs/manage/', 'staffs:member-list'),
    _go('staffs/manage/vacations/', 'staffs:vacation-requests'),
    _go('staffs/manage/<int:pk>/', 'staffs:member-detail'),
    _go('staffs/vacations/', 'staffs:vacations'),
    _go('staffs/calls/', 'staffs:call-list'),
    _go('staffs/calls/new/', 'staffs:call-create'),
    _go('staffs/calls/<int:pk>/', 'staffs:call-detail'),

    # patients
    _go('patients/register-patient/', 'patients:register'),
    _go('patients/patient-dashboard/', 'patients:dashboard'),
    _go('patients/book-appointment/<int:doctor_id>/', 'patients:book-appointment'),

    # doctors
    _go('doctors/register-doctor/', 'doctors:register'),
    _go('doctors/doctor-dashboard/', 'doctors:dashboard'),

    # drivers
    _go('drivers/register-driver/', 'drivers:register'),
    _go('drivers/driver-dashboard/', 'drivers:dashboard'),

    # ambulances
    _go('ambulances/add/', 'ambulances:create'),
    _go('ambulances/my-ambulance/', 'ambulances:mine'),
]
