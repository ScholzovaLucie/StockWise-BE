from django.core.management.base import BaseCommand
from collections import defaultdict
from product.models import Product
from operation.models import Operation

class Command(BaseCommand):
    help = "Přepočítá množství všech produktů a uloží je do amount_cached"

    def handle(self, *args, **options):
        self.stdout.write("📦 Spouštím přepočet množství...")

        product_amounts = defaultdict(int)

        # Všechny operace s přednačtenými skupinami, batch a produktem
        operations = Operation.objects.prefetch_related(
            "groups__batch__product"
        )

        for op in operations:
            for group in op.groups.all():
                product = getattr(group.batch, "product", None)
                if not product:
                    continue
                if op.type == 'IN':
                    product_amounts[product.id] += group.quantity
                elif op.type == 'OUT':
                    product_amounts[product.id] -= group.quantity

        # Hromadný update všech produktů
        products = Product.objects.filter(id__in=product_amounts.keys())
        for p in products:
            p.amount_cached = product_amounts[p.id]

        Product.objects.bulk_update(products, ["amount_cached"])

        self.stdout.write(self.style.SUCCESS("✅ Hotovo – množství všech produktů aktualizováno."))