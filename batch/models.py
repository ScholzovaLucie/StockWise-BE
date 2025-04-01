from django.db import models

from history.models import History


# Create your models here.

class Batch(models.Model):
    product = models.ForeignKey('product.Product', on_delete=models.CASCADE, related_name="batches")
    batch_number = models.CharField(max_length=100)
    expiration_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.batch_number} - {self.product.name}'

    def save(self, *args, **kwargs):
        if self.pk:
            previous = Batch.objects.get(pk=self.pk)
            if previous.batch_number != self.batch_number:
                History.objects.create(
                    related_id=self.id,
                    type='batch',
                    description=f"Změněno číslo šarže z {previous.batch_number} na {self.batch_number}"
                )
            super().save(*args, **kwargs)

        else:
            super().save(*args, **kwargs)
            History.objects.create(
                related_id=self.id,
                type='batch',
                description=f"Vytvořena nová šarže {self.batch_number}")


    def delete(self, *args, **kwargs):
        History.objects.create(
            related_id=self.id,
            type='batch',
            description=f"Odstraněna šarže {self.batch_number}")
        super().delete(*args, **kwargs)