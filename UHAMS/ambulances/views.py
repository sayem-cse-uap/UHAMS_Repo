"""
ambulances.views - managing the ambulance fleet.

Who can do what:
    STAFF   list, view, create, edit, delete any ambulance; change any status.
    DRIVER  view their OWN ambulance and set its status to Available / On Trip /
            Offline only (DRIVER_ALLOWED_STATUSES). Setting it back to Available
            also closes the emergency call it was serving.
"""
from functools import wraps

from django.contrib import messages
from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404

from core.models import User
from .forms import AmbulanceForm, AmbulanceStatusForm
from .models import Ambulance

# Statuses a driver is allowed to set on their own ambulance.
# (Maintenance is excluded: only staff decide that a vehicle goes to maintenance.)
DRIVER_ALLOWED_STATUSES = [
    Ambulance.Status.AVAILABLE,
    Ambulance.Status.ON_TRIP,
    Ambulance.Status.OFFLINE,
]


def _get_logged_in_user(request):
    """The project uses its own session key ('user_id') instead of django.contrib.auth login."""
    user_id = request.session.get('user_id')
    if not user_id:
        return None
    return User.objects.filter(id=user_id).first()


def role_required(*roles):
    """Login + role check that matches the project's custom session login."""
    # This app has its own copy of the decorator that exists in core/decorators.py.
    # It behaves the same way except it does not check is_active or flush the session.
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            user = _get_logged_in_user(request)
            if user is None:
                return redirect('core:login')
            if user.role not in roles:
                messages.error(request, "You do not have permission to access that page.")
                return redirect('core:home')
            # Make the user available to the view (and avoid a second lookup there).
            request.uhams_user = user
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def _driver_profile(user):
    """The user's DriverProfile, or None. `driverprofile` is the automatic
    reverse accessor of DriverProfile.user (OneToOne); getattr with a default
    avoids an exception when the user has no profile."""
    return getattr(user, 'driverprofile', None)


def _can_view(user, ambulance):
    """Staff may see every ambulance; a driver only the one linked to their profile."""
    if user.role == User.Role.STAFF:
        return True
    profile = _driver_profile(user) if user.role == User.Role.DRIVER else None
    return profile is not None and ambulance.driver_id == profile.pk


@role_required(User.Role.STAFF)
def ambulance_list(request):
    """The fleet table with a text search (?q=) and a status filter (?status=)."""
    ambulances = Ambulance.objects.select_related('driver__user')

    query = request.GET.get('q', '').strip()
    status = request.GET.get('status', '').strip()

    if query:
        # Match the text against ID, plate, model or the driver's username (OR).
        ambulances = ambulances.filter(
            Q(ambulance_id__icontains=query)
            | Q(registration_number__icontains=query)
            | Q(model_name__icontains=query)
            | Q(driver__user__username__icontains=query)
        )
    # Ignore unknown status values coming from a hand-edited URL.
    if status in Ambulance.Status.values:
        ambulances = ambulances.filter(status=status)

    context = {
        'ambulances': ambulances,
        'query': query,
        'selected_status': status,
        'status_choices': Ambulance.Status.choices,
        # Overall numbers for the two summary tiles (not affected by the filters).
        'total_count': Ambulance.objects.count(),
        'available_count': Ambulance.objects.filter(status=Ambulance.Status.AVAILABLE).count(),
    }
    return render(request, 'ambulances-templates/ambulance-list.html', context)


@role_required(User.Role.STAFF, User.Role.DRIVER)
def ambulance_detail(request, pk):
    """One ambulance's details, plus the quick status form."""
    ambulance = get_object_or_404(Ambulance.objects.select_related('driver__user'), pk=pk)
    user = request.uhams_user

    # A driver must not be able to open somebody else's ambulance by editing the URL.
    if not _can_view(user, ambulance):
        messages.error(request, "You can only view the ambulance assigned to you.")
        return redirect('core:home')

    is_staff = user.role == User.Role.STAFF
    # None = all statuses (staff); drivers get the shorter list.
    allowed = None if is_staff else DRIVER_ALLOWED_STATUSES
    status_form = AmbulanceStatusForm(instance=ambulance, allowed_statuses=allowed)

    return render(request, 'ambulances-templates/ambulance-detail.html', {
        'ambulance': ambulance,
        'status_form': status_form,
        # Edit/Delete buttons are only shown to staff.
        'can_manage': is_staff,
    })


@role_required(User.Role.STAFF)
def create_ambulance(request):
    """Add a new ambulance."""
    if request.method == 'POST':
        form = AmbulanceForm(request.POST)
        if form.is_valid():
            # Ambulance.save() also writes the ambulance ID into the driver's profile.
            ambulance = form.save()
            messages.success(request, f"Ambulance {ambulance.ambulance_id} created successfully!")
            return redirect('ambulances:detail', pk=ambulance.pk)
    else:
        form = AmbulanceForm()

    # The same template serves "add" and "edit"; these two values change its wording.
    return render(request, 'ambulances-templates/ambulance-form.html', {
        'form': form,
        'page_title': 'Add Ambulance',
        'submit_label': 'Create Ambulance',
    })


@role_required(User.Role.STAFF)
def edit_ambulance(request, pk):
    """Edit an existing ambulance (including changing its driver)."""
    ambulance = get_object_or_404(Ambulance, pk=pk)

    if request.method == 'POST':
        # instance=ambulance makes the form UPDATE this row instead of creating a new one.
        form = AmbulanceForm(request.POST, instance=ambulance)
        if form.is_valid():
            form.save()
            messages.success(request, f"Ambulance {ambulance.ambulance_id} updated successfully!")
            return redirect('ambulances:detail', pk=ambulance.pk)
    else:
        form = AmbulanceForm(instance=ambulance)

    return render(request, 'ambulances-templates/ambulance-form.html', {
        'form': form,
        'ambulance': ambulance,
        'page_title': f'Edit Ambulance {ambulance.ambulance_id}',
        'submit_label': 'Save Changes',
    })


@role_required(User.Role.STAFF)
def delete_ambulance(request, pk):
    """Ask for confirmation (GET), then delete (POST). Deleting through a POST
    form - never a plain link - protects against accidental/forged deletions."""
    ambulance = get_object_or_404(Ambulance, pk=pk)

    if request.method == 'POST':
        label = ambulance.ambulance_id   # remember it: the object is gone after delete()
        ambulance.delete()
        messages.success(request, f"Ambulance {label} deleted.")
        return redirect('ambulances:list')

    return render(request, 'ambulances-templates/ambulance-confirm-delete.html', {'ambulance': ambulance})


@role_required(User.Role.STAFF, User.Role.DRIVER)
def update_ambulance_status(request, pk):
    """Handle the quick status form (POST only; a GET just goes back to the detail page)."""
    ambulance = get_object_or_404(Ambulance, pk=pk)
    user = request.uhams_user

    if request.method != 'POST':
        return redirect('ambulances:detail', pk=ambulance.pk)

    if not _can_view(user, ambulance):
        messages.error(request, "You can only update the ambulance assigned to you.")
        return redirect('core:home')

    allowed = None if user.role == User.Role.STAFF else DRIVER_ALLOWED_STATUSES
    form = AmbulanceStatusForm(request.POST, instance=ambulance, allowed_statuses=allowed)
    if form.is_valid():
        form.save()
        messages.success(request, f"Status of {ambulance.ambulance_id} set to {ambulance.get_status_display()}.")
        # A driver freeing the ambulance means the trip is over: close the emergency call.
        # (The same also happens when staff set it to Available.)
        if ambulance.status == Ambulance.Status.AVAILABLE:
            call = ambulance.active_call
            if call is not None:
                call.status = 'completed'
                call.save(update_fields=['status'])
                messages.info(request, f"Emergency call at {call.location} marked as completed.")
    else:
        # Show the form's validation message(s) as flash messages.
        for error in form.errors.get('status', []):
            messages.error(request, error)

    return redirect('ambulances:detail', pk=ambulance.pk)


@role_required(User.Role.DRIVER)
def my_ambulance(request):
    """Shortcut for a driver to open the ambulance linked to their profile."""
    profile = _driver_profile(request.uhams_user)
    ambulance = Ambulance.objects.filter(driver=profile).first() if profile else None

    if ambulance is None:
        messages.info(request, "No ambulance has been assigned to you yet.")
        return redirect('drivers:dashboard')

    return redirect('ambulances:detail', pk=ambulance.pk)
