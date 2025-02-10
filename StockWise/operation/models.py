from django.db import models


# Create your models here.
class Operation(models.Model):
    OPERATION_TYPE_CHOICES = [
        ('IN', 'Příjem'),
        ('OUT', 'Výdej'),
        ('MOVE', 'Přesun')
    ]

    OPERATION_STATUS_CHOICES = [
        ('CREATED', 'Vytvořeno'),
        ('IN_PROGRESS', 'Probíhá'),
        ('COMPLETED', 'Dokončeno'),
        ('CANCELLED', 'Zrušeno')
    ]

    type = models.CharField(max_length=10, choices=OPERATION_TYPE_CHOICES)
    status = models.CharField(max_length=15, choices=OPERATION_STATUS_CHOICES, default='CREATED')
    user = models.ForeignKey('user.User', on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    description = models.TextField(blank=True, null=True)

    groups = models.ManyToManyField('group.Group', related_name='operations')