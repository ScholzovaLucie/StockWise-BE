from django.db import models

# Create your models here.
class ChatLog(models.Model):
    query = models.TextField()
    response = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)