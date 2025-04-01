from django.db import models


# Create your models here.
class ClientUserRole(models.Model):
    client = models.ForeignKey('client.Client', on_delete=models.CASCADE, related_name="user_roles")
    user = models.ForeignKey('user.User', on_delete=models.CASCADE, related_name="client_roles")
    role = models.ForeignKey('client_role.ClientRole', on_delete=models.CASCADE, related_name="user_roles")