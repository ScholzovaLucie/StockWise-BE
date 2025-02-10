from django.db import models


# Create your models here.
class Group(models.Model):
    batch = models.ForeignKey('batch.Batch', on_delete=models.CASCADE, related_name="groups")
    box = models.ForeignKey('box.Box', on_delete=models.CASCADE, related_name="groups")
    quantity = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        """
        Při vytvoření nebo změně Group aktualizujeme množství produktu.
        """
        super().save(*args, **kwargs)

        # Po uložení přepočítáme `amount` produktu
        self.batch.product.refresh_from_db()