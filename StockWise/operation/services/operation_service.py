from django.db import transaction
from django.db.models import Sum
from batch.models import Batch
from box.models import Box
from group.models import Group
from operation.models import Operation
from stock_change.models import StockChange
from product.models import Product



def add_group_to_operation(operation, batch_id, box_id, quantity):
    """
    Přidání skupiny (Group) do operace (příjem/výdej).
    """
    batch = Batch.objects.get(id=batch_id)
    box = Box.objects.get(id=box_id) if box_id else None

    validate_operation(operation)

    group = Group.objects.create(
        batch=batch,
        box=box,
        quantity=quantity
    )
    operation.groups.add(group)

    # Aktualizace množství produktu
    batch.product.refresh_from_db()
    return group


### 🔹 Metody pro výdej ###

def reserve_batches_for_out_operation(operation):
    """
    Rezervace šarží pro výdej.
    """
    if operation.status != 'CREATED':
        raise ValueError("Operace není ve stavu 'Vytvořeno'.")

    validate_operation(operation)

    for group in operation.groups.all():
        batch = group.batch
        if batch.quantity < group.quantity:
            raise ValueError(f"Nedostatek zásob ve šarži {batch.batch_number}.")
        batch.quantity -= group.quantity
        batch.save()

    operation.status = 'IN_PROGRESS'
    operation.save()
    return {"message": f"Šarže pro operaci ID {operation.id} byly rezervovány."}


def process_out_operation(operation):
    """
    Zpracování výdejky – aktualizace zásob.
    """
    if operation.status != 'IN_PROGRESS':
        raise ValueError("Operace není ve stavu 'Probíhá'.")

    validate_operation(operation)

    for group in operation.groups.all():
        batch = group.batch

        # Log změny zásob
        StockChange.objects.create(
            product=batch.product,
            batch=batch,
            change=-group.quantity,
            operation=operation,
            user=operation.user
        )

        group.delete()

        # Aktualizace množství produktu
        batch.product.refresh_from_db()

    operation.status = 'COMPLETED'
    operation.save()
    return {"message": f"Výdejka ID {operation.id} byla úspěšně zpracována."}


### 🔹 Metody pro příjem ###

def add_group_to_in_operation(operation, product_id, batch_number, box_id, quantity, expiration_date=None):
    """
    Přidání skupiny (Group) do příjemky – vytvoření nové šarže nebo přidání do existující.
    """
    product = Product.objects.get(id=product_id)

    # Ověření, zda už existuje stejná šarže v rámci této operace
    existing_group = operation.groups.filter(batch__batch_number=batch_number).exists()
    if existing_group:
        raise ValueError(f"Šarže {batch_number} už byla do této příjemky přidána.")

    # Pokud neexistuje, vytvoříme nebo načteme Batch
    batch, created = Batch.objects.get_or_create(
        product=product,
        batch_number=batch_number,
        defaults={"expiration_date": expiration_date}
    )

    box = Box.objects.get(id=box_id) if box_id else None

    # Vytvoření nové Group a přidání do operace
    group = Group.objects.create(
        batch=batch,
        box=box,
        quantity=quantity
    )
    operation.groups.add(group)

    # Aktualizace množství produktu
    product.refresh_from_db()
    return group

def process_in_operation(operation):
    """
    Zpracování příjemky s transakční ochranou.
    """
    if operation.status != 'CREATED':
        raise ValueError("Operace není ve stavu 'Vytvořeno'.")

    with transaction.atomic():  # 🛠 Transakční zámek
        for group in operation.groups.all():
            batch = group.batch

            # Log změny zásob
            StockChange.objects.create(
                product=batch.product,
                batch=batch,
                change=group.quantity,
                operation=operation,
                user=operation.user
            )

        operation.status = 'COMPLETED'
        operation.save()

        # Aktualizace množství produktu
        for group in operation.groups.all():
            group.batch.product.refresh_from_db()

    return {"message": f"Příjemka ID {operation.id} byla úspěšně zpracována."}

def cancel_operation(operation):
    """
    Stornování operace (příjemky nebo výdejky).
    """
    if operation.status == 'COMPLETED':
        raise ValueError("Dokončenou operaci nelze stornovat.")

    with transaction.atomic():
        if operation.type == 'OUT':
            for group in operation.groups.all():
                group.batch.quantity += group.quantity  # Vrácení zásob
                group.batch.save()

        elif operation.type == 'IN':
            for group in operation.groups.all():
                group.batch.delete()  # Odstranění přidané šarže

        operation.status = 'CANCELLED'
        operation.save()

    return {"message": f"Operace ID {operation.id} byla stornována."}


### 🔹 Obecné metody pro operace ###

def create_operation(user, operation_type, description=None):
    """
    Vytvoření nové operace (výdejky nebo příjemky).
    """
    if operation_type not in ['IN', 'OUT']:
        raise ValueError("Neplatný typ operace. Musí být 'IN' nebo 'OUT'.")

    return Operation.objects.create(
        type=operation_type,
        status='CREATED',
        user=user,
        description=description
    )


### 🔹 Přidání skupiny do výdejky (OUT) ###
def add_group_to_out_operation(operation, batch_id, box_id, quantity):
    """
    Přidání skupiny (Group) do výdejky.
    """
    batch = Batch.objects.get(id=batch_id)
    box = Box.objects.get(id=box_id) if box_id else None

    validate_operation(operation)

    group = Group.objects.create(
        batch=batch,
        box=box,
        quantity=quantity
    )
    operation.groups.add(group)

    # Aktualizace množství produktu
    batch.product.refresh_from_db()
    return group


### 🔹 Rezervace šarží pro výdej s upozorněním ###
def reserve_batches_for_out_operation_with_notification(operation):
    """
    Rezervace šarží pro výdej a upozornění na nízké zásoby.
    """
    if operation.status != 'CREATED':
        raise ValueError("Operace není ve stavu 'Vytvořeno'.")

    product_ids = operation.groups.values_list('batch__product_id', flat=True).distinct()

    warnings = []
    for product_id in product_ids:
        notification = check_low_stock(product_id)
        if notification:
            warnings.append(notification)

    result = reserve_batches_for_out_operation(operation)

    if warnings:
        result["warnings"] = warnings

    return result


### 🔹 Automatické přidání skupin podle strategie ###
def add_groups_to_operation_with_strategy(operation, product_id, quantity, strategy='FIFO'):
    """
    Automaticky přidá skupiny (Group) do výdejky na základě strategie (FIFO/FEFO).
    """
    batches = get_batches_for_product(product_id, strategy=strategy)
    remaining_quantity = quantity

    if not batches.exists():
        raise ValueError(f"Pro produkt ID {product_id} nejsou dostupné žádné šarže.")

    for batch in batches:
        if remaining_quantity <= 0:
            break

        batch_quantity = min(remaining_quantity, batch.product.amount)

        group = Group.objects.create(
            batch=batch,
            box=None,  # Box je nyní na úrovni Group, nikoliv Batch
            quantity=batch_quantity
        )
        operation.groups.add(group)

        remaining_quantity -= batch_quantity

    if remaining_quantity > 0:
        raise ValueError(f"Nedostatek zásob pro produkt ID {product_id}. Chybí {remaining_quantity} ks.")

    return {"message": f"Do operace ID {operation.id} byly přidány skupiny pro {quantity} ks produktu."}


### 🔹 Kompletní proces výdeje ###
def process_complete_out_operation(user, product_id, quantity, strategy='FIFO', description=None):
    """
    Kompletní proces výdeje: vytvoření operace, přidání skupin, rezervace a zpracování.
    """
    operation = create_operation(user, operation_type='OUT', description=description)

    add_groups_to_operation_with_strategy(operation, product_id, quantity, strategy)

    reserve_batches_for_out_operation_with_notification(operation)

    result = process_out_operation(operation)

    update_boxes_after_out_operation(operation)

    return result


### 🔹 Ostatní pomocné metody ###

def validate_operation(operation):
    """
    Validace operace před rezervací nebo zpracováním.
    """
    errors = []

    for group in operation.groups.all():
        batch = group.batch
        if operation.type == 'OUT' and batch.quantity < group.quantity:
            errors.append(f"Nedostatek zásob ve šarži {batch.batch_number} pro produkt {batch.product.sku}.")

    if errors:
        raise ValueError("Validace selhala: " + ", ".join(errors))


def check_low_stock(product_id, threshold=10):
    """
    Kontrola, zda produkt nemá zásoby pod definovaným prahem.
    """
    total_quantity = Batch.objects.filter(product_id=product_id).aggregate(total=Sum('quantity'))['total'] or 0

    if total_quantity < threshold:
        return {
            "warning": f"Zásoby produktu ID {product_id} klesly pod stanovenou hranici ({threshold} ks).",
            "total_quantity": total_quantity
        }
    return None


def get_batches_for_product(product_id, strategy='FIFO'):
    """
    Vrátí šarže pro daný produkt podle zvolené strategie (FIFO/FEFO).
    """
    query = Batch.objects.filter(product_id=product_id)

    if strategy == 'FEFO':
        return query.order_by('expiration_date')
    return query.order_by('created_at')


def update_boxes_after_out_operation(operation):
    """
    Aktualizace stavu všech krabic po zpracování výdejky.
    """
    for group in operation.groups.all():
        update_box_status(group)


def update_box_status(group):
    """
    Aktualizace stavu jedné krabice.
    """
    if group.box:
        if group.batch.quantity == 0:
            group.box.status = 'empty'
        group.box.save()