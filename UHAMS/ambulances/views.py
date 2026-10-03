from functools import wraps

from django.contrib import messages
from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404

from core.models import User
from .forms import AmbulanceForm, AmbulanceStatusForm
from .models import Ambulance

# Statuses a driver is allowed to set on their own ambulance.
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
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            user = _get_logged_in_user(request)
            if user is None:
                return redirect('login')
            if user.role not in roles:
                messages.error(request, "You do not have permission to access that page.")
                return redirect('home')
            request.uhams_user = user
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def _driver_profile(user):
    return getattr(user, 'driverprofile', None)


def _can_view(user, ambulance):
    if user.role == User.Role.STAFF:
        return True
    profile = _driver_profile(user) if user.role == User.Role.DRIVER else None
    return profile is not None and ambulance.driver_id == profile.pk


@role_required(User.Role.STAFF)
def ambulance_list(request):
    ambulances = Ambulance.objects.select_related('driver__user')

    query = request.GET.get('q', '').strip()
    status = request.GET.get('status', '').strip()

    if query:
        ambulances = ambulances.filter(
            Q(ambulance_id__icontains=query)
            | Q(registration_number__icontains=query)
            | Q(model_name__icontains=query)
            | Q(driver__user__username__icontains=query)
        )
    if status in Ambulance.Status.values:
        ambulances = ambulances.filter(status=status)

    context = {
        'ambulances': ambulances,
        'query': query,
        'selected_status': status,
        'status_choices': Ambulance.Status.choices,
        'total_count': Ambulance.objects.count(),
        'available_count': Ambulance.objects.filter(status=Ambulance.Status.AVAILABLE).count(),
    }
    return render(request, 'ambulances-templates/ambulance-list.html', context)


@role_required(User.Role.STAFF, User.Role.DRIVER)
def ambulance_detail(request, ambulance_pk):
    ambulance = get_object_or_404(Ambulance.objects.select_related('driver__user'), pk=ambulance_pk)
    user = request.uhams_user

    if not _can_view(user, ambulance):
        messages.error(request, "You can only view the ambulance assigned to you.")
        return redirect('home')

    is_staff = user.role == User.Role.STAFF
    allowed = None if is_staff else DRIVER_ALLOWED_STATUSES
    status_form = AmbulanceStatusForm(instance=ambulance, allowed_statuses=allowed)

    return render(request, 'ambulances-templates/ambulance-detail.html', {
        'ambulance': ambulance,
        'status_form': status_form,
        'can_manage': is_staff,
    })


@role_required(User.Role.STAFF)
def create_ambulance(request):
    if request.method == 'POST':
        form = AmbulanceForm(request.POST)
        if form.is_valid():
            ambulance = form.save()
            messages.success(request, f"Ambulance {ambulance.ambulance_id} created successfully!")
            return redirect('ambulance-detail', ambulance_pk=ambulance.pk)
    else:
        form = AmbulanceForm()

    return render(request, 'ambulances-templates/ambulance-form.html', {
        'form': form,
        'page_title': 'Add Ambulance',
        'submit_label': 'Create Ambulance',
    })


@role_required(User.Role.STAFF)
def edit_ambulance(request, ambulance_pk):
    ambulance = get_object_or_404(Ambulance, pk=ambulance_pk)

    if request.method == 'POST':
        form = AmbulanceForm(request.POST, instance=ambulance)
        if form.is_valid():
            form.save()
            messages.success(request, f"Ambulance {ambulance.ambulance_id} updated successfully!")
            return redirect('ambulance-detail', ambulance_pk=ambulance.pk)
    else:
        form = AmbulanceForm(instance=ambulance)

    return render(request, 'ambulances-templates/ambulance-form.html', {
        'form': form,
        'ambulance': ambulance,
        'page_title': f'Edit Ambulance {ambulance.ambulance_id}',
        'submit_label': 'Save Changes',
    })


@role_required(User.Role.STAFF)
def delete_ambulance(request, ambulance_pk):
    ambulance = get_object_or_404(Ambulance, pk=ambulance_pk)

    if request.method == 'POST':
        label = ambulance.ambulance_id
        ambulance.delete()
        messages.success(request, f"Ambulance {label} deleted.")
        return redirect('ambulance-list')

    return render(request, 'ambulances-templates/ambulance-confirm-delete.html', {'ambulance': ambulance})


@role_required(User.Role.STAFF, User.Role.DRIVER)
def update_ambulance_status(request, ambulance_pk):
    ambulance = get_object_or_404(Ambulance, pk=ambulance_pk)
    user = request.uhams_user

    if request.method != 'POST':
        return redirect('ambulance-detail', ambulance_pk=ambulance.pk)

    if not _can_view(user, ambulance):
        messages.error(request, "You can only update the ambulance assigned to you.")
        return redirect('home')

    allowed = None if user.role == User.Role.STAFF else DRIVER_ALLOWED_STATUSES
    form = AmbulanceStatusForm(request.POST, instance=ambulance, allowed_statuses=allowed)
    if form.is_valid():
        form.save()
        messages.success(request, f"Status of {ambulance.ambulance_id} set to {ambulance.get_status_display()}.")
        # A driver freeing the ambulance means the trip is over: close the emergency call.
        if ambulance.status == Ambulance.Status.AVAILABLE:
            call = ambulance.active_call
            if call is not None:
                call.status = 'completed'
                call.save(update_fields=['status'])
                messages.info(request, f"Emergency call at {call.location} marked as completed.")
    else:
        for error in form.errors.get('status', []):
            messages.error(request, error)

    return redirect('ambulance-detail', ambulance_pk=ambulance.pk)


@role_required(User.Role.DRIVER)
def my_ambulance(request):
    """Shortcut for a driver to open the ambulance linked to their profile."""
    profile = _driver_profile(request.uhams_user)
    ambulance = Ambulance.objects.filter(driver=profile).first() if profile else None

    if ambulance is None:
        messages.info(request, "No ambulance has been assigned to you yet.")
        return redirect('driver-dashboard')

    return redirect('ambulance-detail', ambulance_pk=ambulance.pk)
