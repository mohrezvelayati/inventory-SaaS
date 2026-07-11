from django.db import models
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    full_name = models.CharField(max_length=255)
    username = models.CharField(max_length=150, unique=True)
    phone_number = models.CharField(max_length=11, unique=True)
    
    REQUIRED_FIELDS = ['phone_number']

    def __str__(self):
        return self.username