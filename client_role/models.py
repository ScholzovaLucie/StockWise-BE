from django.db import models

# Create your models here.
class ClientRole(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)