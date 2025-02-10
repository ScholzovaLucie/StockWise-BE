from datetime import timezone, datetime

from django.db import models
from django.db.models import Sum

from group.models import Group
from operation.models import Operation


# Create your models here.
class Product(models.Model):
    sku = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField('Created At', auto_now_add=True)
    client = models.ForeignKey('client.Client', verbose_name='Client', null=False, on_delete=models.CASCADE)

    _amount_override = models.IntegerField(null=True, blank=True)

    @property
    def amount(self):
        """
        Dynamicky vypočítá množství produktu na základě sumy všech Group, kde je tento produkt.
        """

        if self._amount_override is not None:
            return self._amount_override

        total_amount = 0
        operations = Operation.objects.filter(groups__batch__product=self)
        for operation in operations:
            if operation.type == 'IN':
                total_amount += operation.groups.filter(batch__product=self).aggregate(Sum('amount'))['amount__sum']
            if operation.type == 'OUT':
                total_amount -= operation.groups.filter(batch__product=self).aggregate(Sum('amount'))['amount__sum']
        return total_amount

    def set_test_amount(self, value):
        """
        Metoda pouze pro testy - umožňuje ručně nastavit `amount` bez ovlivnění běžného provozu.
        """
        self._amount_override = value