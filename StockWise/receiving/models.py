from django.db import models

from batch.models import Batch
from position.models import Position
from product.models import Product
from user.models import User


# Create your models here.
class Receiving(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    position = models.ForeignKey(Position, on_delete=models.CASCADE)
    received_at = models.DateTimeField(auto_now_add=True)
    received_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
