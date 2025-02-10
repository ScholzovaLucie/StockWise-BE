from django.db import models


# Create your models here.
class History(models.Model):
    operation = models.ForeignKey('operation.Operation', on_delete=models.CASCADE, related_name="history")
    description = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)