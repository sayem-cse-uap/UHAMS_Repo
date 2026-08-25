from django.db import models

# Create your models here.
class User(models.Model):
    userID = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20)
    password = models.CharField(max_length=220)
    class Meta:
        abstract = True

    def register(self):
        """Register new user function here"""
        print("oh, new person")

    def login(self):
        """Login user function here"""
        print("good to see you back")


    def logout(self):
        """Logout user function here"""
        print("see you later")

    def updateProfile(self, **data):
        """Update user profile function here"""
        print("data update code, then maybe return Boolean True if updated, or return False if unsuccessful for some reasone")