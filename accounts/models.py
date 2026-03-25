from django.db import models
from django.contrib.auth.models import User

class OTP(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    otp = models.CharField(max_length=6)
    is_verified = models.BooleanField(default=False)

    def __str__(self):
        return self.user.username
