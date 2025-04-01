from datetime import timezone, datetime

from django.db import models
from django.db.models import Sum

from group.models import Group
from history.models import History
from operation.models import Operation


# Create your models here.
class Product(models.Model):
    sku = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField('Created At', auto_now_add=True)
    client = models.ForeignKey('client.Client', verbose_name='Client', null=False, on_delete=models.CASCADE)

    _amount_override = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return self.name or self.sku

    @property
    def amount(self):
        """
        Dynamicky vypočítá množství produktu na základě sumy všech Group, kde je tento produkt.
        """

        if self._amount_override is not None:
            return self._amount_override

        total_amount = 0
        operations = Operation.objects.filter(groups__batch__product_id=self.id).distinct()
        if len(operations) > 0:
            for operation in operations:
                if operation.type == 'IN':
                    total_amount += sum(
                        [group.quantity for group in operation.groups.filter(batch__product_id=self.id)])
                if operation.type == 'OUT':
                    total_amount -= sum(
                        [group.quantity for group in operation.groups.filter(batch__product_id=self.id)])
        return total_amount

    def set_test_amount(self, value):
        """
        Metoda pouze pro testy - umožňuje ručně nastavit `amount` bez ovlivnění běžného provozu.
        """
        self._amount_override = value

    def save(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        if self.pk:
            previous = Product.objects.get(pk=self.pk)
            if previous.name != self.name:
                History.objects.create(
                    user=user,
                    type="product",
                    related_id=self.id,
                    description=f"Změněn název produktu z {previous.name} na {self.name}"
                )
            super().save(*args, **kwargs)

        else:
            super().save(*args, **kwargs)
            History.objects.create(
                user=user,
                type="product",
                related_id=self.id,
                description=f"Vytvořen produkt {self.name}"
            )

    def delete(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        History.objects.create(
            user=user,
            type="product",
            related_id=self.id,
            description=f"Odstraněn produkt {self.name}")
        super().delete(*args, **kwargs)
