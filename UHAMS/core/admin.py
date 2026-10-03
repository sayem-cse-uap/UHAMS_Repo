from django.contrib import admin
from .models import User

# Register your models here.
# Makes the custom User editable in the /admin/ site. (A plain register() gives
# a basic form; Django's UserAdmin would add nicer password handling.)
admin.site.register(User)
