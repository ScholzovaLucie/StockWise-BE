from django.db import models



# Create your models here.
class Box(models.Model):
    width = models.DecimalField(max_digits=10, decimal_places=2)
    height = models.DecimalField(max_digits=10, decimal_places=2)
    depth = models.DecimalField(max_digits=10, decimal_places=2)
    weight = models.DecimalField(max_digits=10, decimal_places=2)
    position = models.ForeignKey('position.Position', on_delete=models.CASCADE, related_name="boxes")