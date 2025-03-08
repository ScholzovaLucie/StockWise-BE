from django.db import models



# Create your models here.
class Box(models.Model):
    ean = models.CharField('EAN', max_length=40, null=False, blank=True)
    width = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    height = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    depth = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    weight = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    position = models.ForeignKey( 'position.Position', null=True, blank=True, on_delete=models.CASCADE, related_name="boxes")

    def __str__(self):
        return f'{self.ean} ({self.width}x{self.height}x{self.depth})'