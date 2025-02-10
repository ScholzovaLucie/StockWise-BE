from django.db import models


# Create your models here.
class Position(models.Model):
    code = models.CharField(max_length=100)
    group = models.ForeignKey('group.Group', on_delete=models.CASCADE, related_name="positions")
