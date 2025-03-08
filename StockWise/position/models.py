from django.db import models

from history.models import History


# Create your models here.
class Position(models.Model):
    code = models.CharField(max_length=100)
    warehouse = models.ForeignKey('warehouse.Warehouse', null=False, on_delete=models.CASCADE)

    def __str__(self):
        return f'{self.code} ({self.warehouse.name})'

    def save(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        if self.pk:
            previous = Position.objects.get(pk=self.pk)
            if previous.code != self.code:
                History.objects.create(
                    user=user,
                    type="position",
                    related_id=self.id,
                    description=f"Změněn kód pozice z {previous.code} na {self.code}")
            super().save(*args, **kwargs)

        else:
            super().save(*args, **kwargs)
            History.objects.create(
                user=user,
                type="position",
                related_id=self.id,
                description=f"Vytvořena nová pozice {self.code}")

    def delete(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        History.objects.create(
            user=user,
            type="position",
            related_id=self.id,
            description=f"Odstraněna pozice {self.code}")
        super().delete(*args, **kwargs)
