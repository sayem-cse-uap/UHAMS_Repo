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
            profile = form.save()
            messages.success(request, f"Staff member {profile.user.username} registered successfully!")
            return redirect('manage-staff-detail', pk=profile.pk)
    else:
        form = StaffRegistrationForm(actor=actor)

    return render(request, 'staffs-templates/register-staff.html', {'form': form})


@role_required(User.Role.STAFF)
def staff_dashboard(request):
    user = request.uhams_user
    my_profile = StaffProfile.objects.filter(user=user).first()
    context = {
        'my_profile': my_profile,
        'appointments': Appointment.objects.select_related(
            'doctor__user', 'patient__user', 'time_block').order_by('-date', '-id'),
        'doctors': DoctorProfile.objects.select_related('user'),
        'patients': PatientProfile.objects.select_related('user', 'assigned_staff__user'),
        'staffs': StaffProfile.listAllStaff(),
        'ambulance_calls': AmbulanceCall.objects.select_related(
            'ambulance', 'handled_by__user')[:10],
    }
    return render(request, 'staffs-templates/staff-dashboard.html', context)


# ----------------------------------------------------------------------
# Manager screens: staff list and per-staff editing
# ----------------------------------------------------------------------
@manager_required
def manage_staff_list(request):
    staff = StaffProfile.listAllStaff()
    query = request.GET.get('q', '').strip()
    role = request.GET.get('role', '').strip()
    access = request.GET.get('access', '').strip()

    if query:
        staff = staff.filter(
            Q(user__username__icontains=query) | Q(user__first_name__icontains=query)
            | Q(user__last_name__icontains=query) | Q(department__icontains=query)
            | Q(title__icontains=query)
        )
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


SENSITIVE_ACTIONS = {'role', 'salary'}


@manager_required
def manage_staff_detail(request, pk):
    actor = request.staff_profile
    target = get_object_or_404(StaffProfile.objects.select_related('user'), pk=pk)
    can_manage = can_manage_staff(actor, target)
    can_sensitive = can_edit_sensitive(actor, target)
    access_choices = allowed_access_levels(actor) if can_sensitive else None

    action = request.POST.get('action') if request.method == 'POST' else None

    def data_for(name):
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
        if not can_manage:
            messages.error(request, "Only an administrator can modify an administrator's profile.")
            return redirect('manage-staff-detail', pk=target.pk)
        if action in SENSITIVE_ACTIONS and not can_sensitive:
            messages.error(request, "You cannot change your own role or salary.")
            return redirect('manage-staff-detail', pk=target.pk)

        try:
            if action == 'role' and role_form.is_valid():
                target.changeRoleOfStaff(role_form.cleaned_data['role'], actor)
                messages.success(request, "Role updated.")
                return redirect('manage-staff-detail', pk=target.pk)

            if action == 'salary' and salary_form.is_valid():
                target.changeSalaryOfStaff(salary_form.cleaned_data['salary'], actor)
                messages.success(request, "Salary updated.")
                return redirect('manage-staff-detail', pk=target.pk)

            if action == 'details' and details_form.is_valid():
                target.changeDetailsOfStaff(actor, **details_form.cleaned_data)
                messages.success(request, "Staff details updated.")
                return redirect('manage-staff-detail', pk=target.pk)

            if action == 'assignment' and assignment_form.is_valid():
                target.assignStaff(assignment_form.cleaned_data['assignment'], assigned_by=actor)
                messages.success(request, "Assignment updated.")
                return redirect('manage-staff-detail', pk=target.pk)

            if action == 'room' and room_form.is_valid():
                target.ReAllocateRoom(room_form.cleaned_data['room'], assigned_by=actor)
                messages.success(request, "Staff member moved to the new room.")
                return redirect('manage-staff-detail', pk=target.pk)

            if action == 'assign_patient' and assign_patient_form.is_valid():
                patient = assign_patient_form.cleaned_data['patient']
                target.managePatient(patient, 'assign')
                messages.success(request, f"{patient.user.username} assigned to {target.user.username}.")
                return redirect('manage-staff-detail', pk=target.pk)

            if action == 'release_patient' and release_form.is_valid():
                patient = release_form.cleaned_data['patient']
                target.managePatient(patient, 'release')
                messages.success(request, f"{patient.user.username} released.")
                return redirect('manage-staff-detail', pk=target.pk)
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

    request_form = VacationRequestForm(request.POST if action == 'request' else None)
    cancel_form = VacationCancelForm(request.POST if action == 'cancel' else None, staff=staff)

    if request.method == 'POST':
        try:
            if action == 'request' and request_form.is_valid():
                cd = request_form.cleaned_data
                staff.requestVacation(cd['start_date'], cd['end_date'], cd['reason'])
                messages.success(request, "Vacation request sent to your managers.")
                return redirect('my-vacations')
            if action == 'cancel' and cancel_form.is_valid():
                cancel_form.cleaned_data['vacation'].cancel(staff)
                messages.success(request, "Vacation request cancelled.")
                return redirect('my-vacations')
            if action == 'cancel':
                messages.error(request, "That request can no longer be cancelled.")
                return redirect('my-vacations')
        except ValidationError as exc:
            if action == 'request':
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
                record.approve(actor) if approve else record.reject(actor)
                messages.success(request, f"{record.staff.user.username}'s request was {'approved' if approve else 'rejected'}.")
            except ValidationError as exc:
                for message in exc.messages:
                    messages.error(request, message)
            except PermissionDenied as exc:
                messages.error(request, str(exc))
        else:
            messages.error(request, "That request could not be found.")
        return redirect('manage-vacations')

    status = request.GET.get('status', VacationRecord.PENDING).strip()
    records = VacationRecord.objects.select_related('staff__user', 'reviewed_by__user')
    if status in dict(VacationRecord.STATUS_CHOICES):
        records = records.filter(status=status)
    else:
        status = ''
    records = list(records.order_by('start_date', 'id'))
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
    calls = AmbulanceCall.objects.select_related('ambulance', 'handled_by__user')
    status = request.GET.get('status', '').strip()
    if status in dict(AmbulanceCall.STATUS_CHOICES):
        calls = calls.filter(status=status)
    else:
        status = ''
    return render(request, 'staffs-templates/call-list.html', {
        'calls': calls[:100],
        'selected_status': status,
        'status_choices': AmbulanceCall.STATUS_CHOICES,
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
            call = actor.emergencyAmbulanceCallRequestHandling(
                form.cleaned_data['location'], form.cleaned_data['description'])
            if call.status == AmbulanceCall.DISPATCHED:
                driver = call.ambulance.driver.user
                messages.success(request, f"Ambulance {call.ambulance.ambulance_id} dispatched (driver {driver.get_full_name() or driver.username}).")
            else:
                messages.warning(request, "No ambulance with a driver is free right now. The call is pending; dispatch one when it becomes available.")
            return redirect('call-detail', pk=call.pk)
    else:
        form = EmergencyCallForm()
    return render(request, 'staffs-templates/call-form.html', {'form': form})


@staff_profile_required
def call_detail(request, pk):
    actor = request.staff_profile
    call = get_object_or_404(
        AmbulanceCall.objects.select_related('ambulance__driver__user', 'handled_by__user'), pk=pk)
    action = request.POST.get('action') if request.method == 'POST' else None
    dispatch_form = DispatchForm(request.POST if action == 'dispatch' else None)

    if request.method == 'POST':
        try:
            if action == 'dispatch' and dispatch_form.is_valid():
                ambulance = dispatch_form.cleaned_data['ambulance'] or actor.listAllAvailableAmbulances().first()
                if ambulance is None:
                    raise ValidationError("No ambulance with a driver is available right now.")
                actor.dispatchAmbulance(ambulance, call)
                messages.success(request, f"Ambulance {ambulance.ambulance_id} dispatched.")
                return redirect('call-detail', pk=call.pk)
            if action == 'complete':
                actor.completeAmbulanceCall(call)
                messages.success(request, "Call marked as completed; the ambulance is available again.")
                return redirect('call-detail', pk=call.pk)
            if action == 'cancel':
                actor.cancelAmbulanceCall(call)
                messages.success(request, "Call cancelled.")
                return redirect('call-detail', pk=call.pk)
        except ValidationError as exc:
            for message in exc.messages:
                messages.error(request, message)
            call.refresh_from_db()
            dispatch_form = DispatchForm()

    return render(request, 'staffs-templates/call-detail.html', {
        'call': call,
        'dispatch_form': dispatch_form,
        'free_ambulances': StaffProfile.listAllAvailableAmbulances().count(),
    })
