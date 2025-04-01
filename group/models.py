from django.db import models

from history.models import History


# Create your models here.
class Group(models.Model):
    batch = models.ForeignKey('batch.Batch', on_delete=models.CASCADE, related_name="groups")
    box = models.ForeignKey('box.Box', null=True, on_delete=models.CASCADE, related_name="groups")
    quantity = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    rescanned = models.BooleanField(default=False)

    def __str__(self):
        return f'{self.quantity} x {self.batch.product.name}'

    def save(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        if self.pk:
            previous = Group.objects.get(pk=self.pk)
            if previous.quantity != self.quantity:
                History.objects.create(user=user,
                                       type="group",
                                       related_id=self.id,
                                       description=f"Změněno množství z {previous.quantity} na {self.quantity}")
            super().save(*args, **kwargs)

        else:
            super().save(*args, **kwargs)
            History.objects.create(user=user,
                                   type="group",
                                   related_id=self.id,
                                   description=f"Vytvořena nová skupina s množstvím {self.quantity}")

        self.batch.product.refresh_from_db()

    def delete(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        History.objects.create(user=user,
                               type="group",
                               related_id=self.id, description=f"Odstraněna skupina s množstvím {self.quantity}")
        super().delete(*args, **kwargs)
