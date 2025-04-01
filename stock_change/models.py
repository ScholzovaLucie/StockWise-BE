from django.db import models


# Create your models here.
class StockChange(models.Model):
    product = models.ForeignKey('product.Product', on_delete=models.CASCADE, related_name="stock_changes")
    change = models.IntegerField()
    timestamp = models.DateTimeField(auto_now_add=True)