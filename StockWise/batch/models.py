from django.db import models


# Create your models here.

class Batch(models.Model):
    product = models.ForeignKey('product.Product', on_delete=models.CASCADE, related_name="batches")
    batch_number = models.CharField(max_length=100)
    expiration_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
