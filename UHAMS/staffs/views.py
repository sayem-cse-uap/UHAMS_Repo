"""
staffs.views - the pages used by hospital staff.

  Staff dashboard ............ overview of appointments, doctors, patients, staff, calls
  Register staff ............. managers create staff accounts
  Manage staff (list/detail).. managers edit roles, salaries, assignments, patients
  Vacations .................. every staff member requests leave; managers review it
  Emergency calls ............ log a call, dispatch/complete/cancel it

Typical view anatomy used throughout this file:
  1. A decorator checks who is allowed in (and attaches request.staff_profile).
  2. On POST, build a form from request.POST and validate it.
  3. If valid, call a MODEL method to do the work (rules live in staffs/models.py),
     show a flash message and redirect (Post/Redirect/Get).
  4. Otherwise re-render the template; forms show their own errors.
"""
from django.contrib import messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from appointments.models import Appointment
from core.decorators import role_required
from core.models import User
from doctors.models import DoctorProfile
from patients.models import PatientProfile
from .decorators import manager_required, staff_profile_required
from .forms import (
    AssignmentForm, AssignPatientForm, DispatchForm, EmergencyCallForm,
    ReleasePatientForm, RoleForm, RoomForm, SalaryForm, StaffDetailsForm,
    StaffRegistrationForm, VacationCancelForm, VacationRequestForm, VacationReviewForm,
)
from .models import AmbulanceCall, StaffProfile, VacationRecord
from .permissions import allowed_access_levels, can_edit_sensitive, can_manage_staff


@manager_required
def register_staff(request):
    """Only managers/admins create staff accounts."""
    actor = request.staff_profile
    if request.method == 'POST':
        form = StaffRegistrationForm(request.POST, actor=actor)
        if form.is_valid():
            profile = form.save()   # creates the User and the StaffProfile together
            messages.success(request, f"Staff member {profile.user.username} registered successfully!")
            return redirect('staffs:member-detail', pk=profile.pk)
    else:
        form = StaffRegistrationForm(actor=actor)

    return render(request, 'staffs-templates/register-staff.html', {'form': form})


@role_required(User.Role.STAFF)
def staff_dashboard(request):
    """Landing page for staff: summary tiles and tables of everything in the hospital.

    Uses role_required (not staff_profile_required) on purpose: a STAFF account
    with no profile yet must still be able to open this page, where the template
    tells them to ask for a profile to be created."""
    user = request.uhams_user
    my_profile = StaffProfile.objects.filter(user=user).first()
    # Each entry becomes a variable in the template. select_related() joins the
    # related tables so listing rows does not trigger one extra query per row.
    context = {
        'my_profile': my_profile,
        'appointments': Appointment.objects.select_related(
            'doctor__user', 'patient__user', 'time_block').order_by('-date', '-id'),
        'doctors': DoctorProfile.objects.select_related('user'),
        'patients': PatientProfile.objects.select_related('user', 'assigned_staff__user'),
        'staffs': StaffProfile.listAllStaff(),
        'ambulance_calls': AmbulanceCall.objects.select_related(
            'ambulance', 'handled_by__user')[:10],   # only the 10 most recent calls
    }
    return render(request, 'staffs-templates/staff-dashboard.html', context)


# ----------------------------------------------------------------------
# Manager screens: staff list and per-staff editing
# ----------------------------------------------------------------------
@manager_required
def manage_staff_list(request):
    """Searchable/filterable list of all staff. Filters come from the query
    string (?q=...&role=...&access=...), so the page is a plain GET form."""
    staff = StaffProfile.listAllStaff()
    query = request.GET.get('q', '').strip()
    role = request.GET.get('role', '').strip()
    access = request.GET.get('access', '').strip()

    if query:
        # Q objects combined with | mean OR: match the text in ANY of these fields.
        staff = staff.filter(
            Q(user__username__icontains=query) | Q(user__first_name__icontains=query)
            | Q(user__last_name__icontains=query) | Q(department__icontains=query)
            | Q(title__icontains=query)
        )
    # Only apply role/access filters when the value is a real choice, so a
    # hand-edited URL with junk in it is simply ignored.
    if role in dict(StaffProfile.ROLE_CHOICES):
        staff = staff.filter(role=role)
    if access in dict(StaffProfile.ACCESS_CHOICES):
        staff = staff.filter(access_level=access)

    return render(request, 'staffs-templates/manage-staff-list.html', {
        'staff_members': staff,
        'query': query,
        'selected_role': role,
        'selected_access': access,
        'role_choices': StaffProfile.ROLE_CHOICES,
        'access_choices': StaffProfile.ACCESS_CHOICES,
    })


# Actions that change pay/rank. These are blocked when editing yourself.
SENSITIVE_ACTIONS = {'role', 'salary'}


@manager_required
def manage_staff_detail(request, pk):
    """One staff member's page, with a separate form for each thing a manager can do.

    `actor`  = the manager using the page.   `target` = the staff member being edited.

    Every form on the page posts to this same URL with a hidden field
    name="action" value="role|salary|details|assignment|room|assign_patient|release_patient".
    Only the form whose name matches `action` receives request.POST; the others
    are rendered empty. (Same trick as core.views.account_settings.)
    """
    actor = request.staff_profile
    target = get_object_or_404(StaffProfile.objects.select_related('user'), pk=pk)
    # Permission flags, computed once and used for both the checks below and the template.
    can_manage = can_manage_staff(actor, target)        # may I touch this person at all?
    can_sensitive = can_edit_sensitive(actor, target)   # may I change role/salary/access?
    access_choices = allowed_access_levels(actor) if can_sensitive else None

    action = request.POST.get('action') if request.method == 'POST' else None

    def data_for(name):
        """Return the POST data for the form called `name`, or None (= unbound form)."""
        return request.POST if action == name else None

    role_form = RoleForm(data_for('role'), prefix='role', initial={'role': target.role})
    salary_form = SalaryForm(data_for('salary'), prefix='salary', initial={'salary': target.salary})
    details_form = StaffDetailsForm(
        data_for('details'), prefix='details', access_choices=access_choices,
        initial={
            'title': target.title, 'department': target.department,
            'availability_status': target.availability_status,
            'access_level': target.access_level,
        },
    )
    assignment_form = AssignmentForm(data_for('assignment'), prefix='assignment')
    room_form = RoomForm(data_for('room'), prefix='room')
    assign_patient_form = AssignPatientForm(data_for('assign_patient'), prefix='assign')
    release_form = ReleasePatientForm(data_for('release_patient'), prefix='release', staff=target)

    if request.method == 'POST':
        # --- Permission gates BEFORE doing anything. The template hides the
        # forms the actor may not use, but a hand-made POST must be refused here too.
        if not can_manage:
            messages.error(request, "Only an administrator can modify an administrator's profile.")
            return redirect('staffs:member-detail', pk=target.pk)
        if action in SENSITIVE_ACTIONS and not can_sensitive:
            messages.error(request, "You cannot change your own role or salary.")
            return redirect('staffs:member-detail', pk=target.pk)

        try:
            # Each branch: right action + valid form -> call the model method -> flash message -> redirect.
            if action == 'role' and role_form.is_valid():
                target.changeRoleOfStaff(role_form.cleaned_data['role'], actor)
                messages.success(request, "Role updated.")
                return redirect('staffs:member-detail', pk=target.pk)

            if action == 'salary' and salary_form.is_valid():
                target.changeSalaryOfStaff(salary_form.cleaned_data['salary'], actor)
                messages.success(request, "Salary updated.")
                return redirect('staffs:member-detail', pk=target.pk)

            if action == 'details' and details_form.is_valid():
                # **cleaned_data passes title=..., department=..., ... as keyword arguments.
                target.changeDetailsOfStaff(actor, **details_form.cleaned_data)
                messages.success(request, "Staff details updated.")
                return redirect('staffs:member-detail', pk=target.pk)

            if action == 'assignment' and assignment_form.is_valid():
                target.assignStaff(assignment_form.cleaned_data['assignment'], assigned_by=actor)
                messages.success(request, "Assignment updated.")
                return redirect('staffs:member-detail', pk=target.pk)

            if action == 'room' and room_form.is_valid():
                target.ReAllocateRoom(room_form.cleaned_data['room'], assigned_by=actor)
                messages.success(request, "Staff member moved to the new room.")
                return redirect('staffs:member-detail', pk=target.pk)

            if action == 'assign_patient' and assign_patient_form.is_valid():
                patient = assign_patient_form.cleaned_data['patient']
                target.managePatient(patient, 'assign')
                messages.success(request, f"{patient.user.username} assigned to {target.user.username}.")
                return redirect('staffs:member-detail', pk=target.pk)

            if action == 'release_patient' and release_form.is_valid():
                patient = release_form.cleaned_data['patient']
                target.managePatient(patient, 'release')
                messages.success(request, f"{patient.user.username} released.")
                return redirect('staffs:member-detail', pk=target.pk)
        # Rule violations raised by the model methods (e.g. "staff member is on
        # leave") become red flash messages instead of a crash.
        except ValidationError as exc:
            for message in exc.messages:
                messages.error(request, message)
        except PermissionDenied as exc:
            messages.error(request, str(exc) or "You do not have permission to perform this action.")

    return render(request, 'staffs-templates/manage-staff-detail.html', {
        'target': target,
        'can_manage': can_manage,
        'can_sensitive': can_sensitive,
        'is_self': actor.pk == target.pk,
        'role_form': role_form,
        'salary_form': salary_form,
        'details_form': details_form,
        'assignment_form': assignment_form,
        'room_form': room_form,
        'assign_patient_form': assign_patient_form,
        # `target.patients` is the reverse side of PatientProfile.assigned_staff.
        'assigned_patients': target.patients.select_related('user'),
        'assignment_history': target.checkStaffAssignmentHistory().select_related('assigned_by__user'),
        'vacations': target.checkVacationHistoryOfStaff(),
    })


# ----------------------------------------------------------------------
# Vacations
# ----------------------------------------------------------------------
@staff_profile_required
def my_vacations(request):
    """Every staff member: request time off, see status, withdraw pending requests."""
    staff = request.staff_profile
    action = request.POST.get('action') if request.method == 'POST' else None

    # Same "one page, several forms, hidden action field" pattern as above.
    request_form = VacationRequestForm(request.POST if action == 'request' else None)
    cancel_form = VacationCancelForm(request.POST if action == 'cancel' else None, staff=staff)

    if request.method == 'POST':
        try:
            if action == 'request' and request_form.is_valid():
                cd = request_form.cleaned_data
                staff.requestVacation(cd['start_date'], cd['end_date'], cd['reason'])
                messages.success(request, "Vacation request sent to your managers.")
                return redirect('staffs:vacations')
            if action == 'cancel' and cancel_form.is_valid():
                cancel_form.cleaned_data['vacation'].cancel(staff)
                messages.success(request, "Vacation request cancelled.")
                return redirect('staffs:vacations')
            if action == 'cancel':
                # Invalid cancel form: the id was not one of this staff
                # member's pending requests (already reviewed, or someone else's).
                messages.error(request, "That request can no longer be cancelled.")
                return redirect('staffs:vacations')
        except ValidationError as exc:
            if action == 'request':
                # Show model-level problems (overlap, past date) inside the request form.
                request_form.add_error(None, exc)
            else:
                for message in exc.messages:
                    messages.error(request, message)
        except PermissionDenied as exc:
            messages.error(request, str(exc))

    return render(request, 'staffs-templates/my-vacations.html', {
        'request_form': request_form,
        'vacations': staff.checkVacationHistoryOfStaff().select_related('reviewed_by__user'),
        'on_leave': staff.is_on_leave(),
    })


@manager_required
def manage_vacations(request):
    """Managers approve or reject vacation requests."""
    actor = request.staff_profile

    if request.method == 'POST':
        form = VacationReviewForm(request.POST)
        if form.is_valid():
            record = form.cleaned_data['vacation']
            approve = form.cleaned_data['decision'] == 'approve'
            try:
                # The model enforces who may review what (no self-approval, etc.).
                record.approve(actor) if approve else record.reject(actor)
                messages.success(request, f"{record.staff.user.username}'s request was {'approved' if approve else 'rejected'}.")
            except ValidationError as exc:
                for message in exc.messages:
                    messages.error(request, message)
            except PermissionDenied as exc:
                messages.error(request, str(exc))
        else:
            messages.error(request, "That request could not be found.")
        return redirect('staffs:vacation-requests')

    # GET: show the queue. By default only PENDING requests; ?status=... changes that,
    # and an empty/unknown status shows everything.
    status = request.GET.get('status', VacationRecord.PENDING).strip()
    records = VacationRecord.objects.select_related('staff__user', 'reviewed_by__user')
    if status in dict(VacationRecord.STATUS_CHOICES):
        records = records.filter(status=status)
    else:
        status = ''
    # Oldest start date first, so the most urgent requests are at the top.
    records = list(records.order_by('start_date', 'id'))
    # Attach extra attributes the template reads: whether to show the
    # Approve/Reject buttons, and otherwise the reason they are not available.
    for record in records:
        record.can_review = record.review_block_reason(actor) is None
        record.review_note = record.review_block_reason(actor) if record.status == VacationRecord.PENDING else ''

    return render(request, 'staffs-templates/manage-vacations.html', {
        'records': records,
        'selected_status': status,
        'status_choices': VacationRecord.STATUS_CHOICES,
    })


# ----------------------------------------------------------------------
# Emergency ambulance calls
# ----------------------------------------------------------------------
@staff_profile_required
def call_list(request):
    """All emergency calls (newest first), optionally filtered by ?status=..."""
    calls = AmbulanceCall.objects.select_related('ambulance', 'handled_by__user')
    status = request.GET.get('status', '').strip()
    if status in dict(AmbulanceCall.STATUS_CHOICES):
        calls = calls.filter(status=status)
    else:
        status = ''
    return render(request, 'staffs-templates/call-list.html', {
        'calls': calls[:100],   # cap the page at 100 rows
        'selected_status': status,
        'status_choices': AmbulanceCall.STATUS_CHOICES,
        # The two tiles at the top of the page:
        'pending_count': AmbulanceCall.objects.filter(status=AmbulanceCall.PENDING).count(),
        'free_ambulances': StaffProfile.listAllAvailableAmbulances().count(),
    })


@staff_profile_required
def call_new(request):
    """Log an emergency call; the first free ambulance with a driver is dispatched automatically."""
    actor = request.staff_profile
    if request.method == 'POST':
        form = EmergencyCallForm(request.POST)
        if form.is_valid():
            # One model method does the whole job: create the call, then try to dispatch.
            call = actor.emergencyAmbulanceCallRequestHandling(
                form.cleaned_data['location'], form.cleaned_data['description'])
            if call.status == AmbulanceCall.DISPATCHED:
                driver = call.ambulance.driver.user
                messages.success(request, f"Ambulance {call.ambulance.ambulance_id} dispatched (driver {driver.get_full_name() or driver.username}).")
            else:
                # No ambulance free: the call was still saved as 'pending'.
                messages.warning(request, "No ambulance with a driver is free right now. The call is pending; dispatch one when it becomes available.")
            return redirect('staffs:call-detail', pk=call.pk)
    else:
        form = EmergencyCallForm()
    return render(request, 'staffs-templates/call-form.html', {'form': form})


@staff_profile_required
def call_detail(request, pk):
    """One call's page: details plus buttons to dispatch, complete or cancel it
    (which buttons appear depends on the call's status; see call-detail.html)."""
    actor = request.staff_profile
    call = get_object_or_404(
        AmbulanceCall.objects.select_related('ambulance__driver__user', 'handled_by__user'), pk=pk)
    action = request.POST.get('action') if request.method == 'POST' else None
    dispatch_form = DispatchForm(request.POST if action == 'dispatch' else None)

    if request.method == 'POST':
        try:
            if action == 'dispatch' and dispatch_form.is_valid():
                # The dropdown is optional; blank means "just take the first available one".
                ambulance = dispatch_form.cleaned_data['ambulance'] or actor.listAllAvailableAmbulances().first()
                if ambulance is None:
                    raise ValidationError("No ambulance with a driver is available right now.")
                actor.dispatchAmbulance(ambulance, call)
                messages.success(request, f"Ambulance {ambulance.ambulance_id} dispatched.")
                return redirect('staffs:call-detail', pk=call.pk)
            if action == 'complete':
                actor.completeAmbulanceCall(call)
                messages.success(request, "Call marked as completed; the ambulance is available again.")
                return redirect('staffs:call-detail', pk=call.pk)
            if action == 'cancel':
                actor.cancelAmbulanceCall(call)
                messages.success(request, "Call cancelled.")
                return redirect('staffs:call-detail', pk=call.pk)
        except ValidationError as exc:
            for message in exc.messages:
                messages.error(request, message)
            # The failed operation may have left in-memory changes on `call`;
            # reload it so the page shows what is really in the database.
            call.refresh_from_db()
            dispatch_form = DispatchForm()

    return render(request, 'staffs-templates/call-detail.html', {
        'call': call,
        'dispatch_form': dispatch_form,
        'free_ambulances': StaffProfile.listAllAvailableAmbulances().count(),
    })
