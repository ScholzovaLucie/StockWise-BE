from django.db import models

from history.models import History


# Create your models here.
class Operation(models.Model):
    VALID_TRANSITIONS = {
        'CREATED': ['BOX', 'CANCELLED'],
        'BOX': ['COMPLETED', 'CANCELLED'],
        'COMPLETED': [],
        'CANCELLED': []
    }

    OPERATION_TYPE_CHOICES = [
        ('IN', 'Příjem'),
        ('OUT', 'Výdej'),
    ]

    OPERATION_STATUS_CHOICES = [
        ('CREATED', 'Vytvořeno'),
        ('COMPLETED', 'Dokončeno'),
        ('CANCELLED', 'Zrušeno'),
        ('BOX', 'Balení')
    ]

    number = models.CharField(blank=True, null=True)
    client = models.ForeignKey('client.Client', verbose_name='Client', null=False, on_delete=models.CASCADE)
    type = models.CharField(max_length=10, choices=OPERATION_TYPE_CHOICES)
    status = models.CharField(max_length=15, choices=OPERATION_STATUS_CHOICES, default='CREATED')
    user = models.ForeignKey('user.User', on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    description = models.TextField(blank=True, null=True)
    cash_on_delivery = models.PositiveIntegerField(
        'Cash on delivery',
        blank=True,
        default=0
    )
    delivery_date = models.DateTimeField(
        'Delivery date',
        null=True,
        blank=True
    )
    delivery_name = models.CharField(
        'Delivery name',
        null=True,
        blank=True,
        max_length=80
    )
    delivery_street = models.CharField(
        'Delivery street',
        null=True,
        blank=True,
        max_length=80
    )
    delivery_city = models.CharField(
        'Delivery city',
        null=True,
        blank=True,
        max_length=80
    )
    delivery_psc = models.CharField(
        'Delivery zip code',
        null=True,
        blank=True,
        max_length=80
    )
    delivery_country = models.CharField(
        'Delivery country',
        null=True,
        blank=True,
        max_length=80,
        default='CZ'
    )
    delivery_phone = models.CharField(
        'Delivery phone',
        null=True,
        blank=True,
        max_length=80
    )
    delivery_email = models.CharField(
        'Delivery email',
        null=True,
        blank=True,
        max_length=80
    )
    delivery_note = models.CharField(
        'Delivery note',
        null=True,
        blank=True,
        max_length=300
    )
    invoice_name = models.CharField(
        'Invoice name',
        null=True,
        blank=True,
        max_length=80
    )
    invoice_street = models.CharField(
        'Invoice street',
        null=True,
        blank=True,
        max_length=80
    )
    invoice_city = models.CharField(
        'Invoice city',
        null=True,
        blank=True,
        max_length=80
    )
    invoice_psc = models.CharField(
        'Invoice zip code',
        null=True,
        blank=True,
        max_length=80
    )
    invoice_country = models.CharField(
        'Invoice country',
        null=True,
        blank=True,
        max_length=80,
        default='CZ'
    )
    invoice_phone = models.CharField(
        'Invoice phone',
        null=True,
        blank=True,
        max_length=80
    )
    invoice_email = models.CharField(
        'Invoice email',
        null=True,
        blank=True,
        max_length=80
    )
    invoice_ico = models.CharField(
        'IC',
        null=True,
        blank=True,
        max_length=30
    )
    invoice_vat = models.CharField(
        'VAT number',
        null=True,
        blank=True,
        max_length=30
    )

    groups = models.ManyToManyField('group.Group', related_name='operations')

    def __str__(self):
        return str(self.number)

    def save(self, *args, **kwargs):
        """Sledování všech změn v operaci."""
        is_new = not self.pk
        user = kwargs.pop('user', None)  # Uživatele předáme jako parametr

        if not is_new:
            previous = Operation.objects.get(pk=self.pk)
            changes = []

            if previous.status != self.status and self.status not in self.VALID_TRANSITIONS[previous.status]:
                raise ValueError(f"Neplatný přechod stavu z {previous.status} na {self.status}")


            for field in ['status', 'number', 'description', 'delivery_date', 'delivery_name', 'invoice_name']:
                old_value = getattr(previous, field)
                new_value = getattr(self, field)
                if old_value != new_value:
                    changes.append(f"{field} změněno z '{old_value}' na '{new_value}'")

            if changes:
                History.objects.create(
                    type="operation",
                    related_id=self.id,
                    user=user,
                    description="; ".join(changes)
                )

        super().save(*args, **kwargs)

        if is_new:
            History.objects.create(
                type="operation",
                related_id=self.id,
                user=user,
                description=f"Vytvořena operace {self.number}"
            )

    def delete(self, *args, **kwargs):
        user = kwargs.pop('user', None)  # Uživatele předáme jako parametr
        History.objects.create(
            type="operation",
            related_id=self.id,
            user=user,
            description=f"Odstraněna operace {self.number}"
        )
        super().delete(*args, **kwargs)