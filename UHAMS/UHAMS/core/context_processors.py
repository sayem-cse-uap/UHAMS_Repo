from functools import wraps

from django.shortcuts import redirect

from .models import User
def load_logged_in_user(request):
    user_id = request.session.get('user_id')
    if user_id:
        try:
            # Fetch the user using the custom session ID
            user = User.objects.get(id=user_id)
            return {'logged_in_user': user}
        except User.DoesNotExist:
            pass

    return {'logged_in_user': None}

def custom_login_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if 'user_id' not in request.session:
            return redirect('login')  # Redirect to your login URL name
        return view_func(request, *args, **kwargs)
    return wrapper
