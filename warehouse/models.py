from django.db import models


class Warehouse(models.Model):
    name = models.CharField(max_length=255)
    description = models.CharField(blank=True, default='', max_length=255)
    city = models.CharField(blank=True, default='', max_length=255)
    state = models.CharField(blank=True, default='', max_length=255)
    address = models.CharField(blank=True, default='', max_length=255)
    psc = models.CharField(blank=True, default='', max_length=7)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name