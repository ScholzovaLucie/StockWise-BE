# group/signals.py
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from group.models import Group
from product.models import Product
from operation.models import Operation

@receiver([post_save, post_delete], sender=Group)
def update_product_amount(sender, instance, **kwargs):
    """
    Přepočítá množství produktu, pokud se změní skupina (Group).
    """
    batch = instance.batch
    if not batch or not batch.product:
        return

    product = batch.product
    # Najdeme všechny groupy s daným produktem
    groups = Group.objects.filter(batch__product=product).select_related("operation")

    total = 0
    for group in groups:
        if group.operation_set.type == 'IN':
            total += group.quantity
        elif group.operation_set.type == 'OUT':
            total -= group.quantity

    product.amount_cached = total
    product.save(update_fields=["amount_cached"])