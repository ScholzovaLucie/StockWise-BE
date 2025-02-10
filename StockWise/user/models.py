from django.contrib.auth.base_user import BaseUserManager, AbstractBaseUser
from django.contrib.auth.models import PermissionsMixin
from django.db import models


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email je povinný")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(email, password, **extra_fields)



# Create your models here.
class User(AbstractBaseUser, PermissionsMixin):
    client = models.ManyToManyField('client.Client', related_name="users")
    name = models.CharField(max_length=255)
    email = models.EmailField(null=False, blank=False, unique=True)
    password = models.CharField(max_length=255, null=False, blank=False, default='test')
    role = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    last_login = models.DateTimeField(null=True, blank=True)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    @property
    def is_anonymous(self):
        """Vrací False, protože tento model nepředstavuje anonymního uživatele."""
        return False

    @property
    def is_authenticated(self):
        """Vrací True, pokud je uživatel přihlášen (neanonymní)."""
        return True

    def __str__(self):
        return self.email