from datetime import datetime

from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import transaction
from django.db.models import Sum
from django.shortcuts import get_object_or_404

from batch.models import Batch
from box.models import Box
from client.models import Client
from group.models import Group
from operation.models import Operation
from product.models import Product


def create_operation(user, operation_type, number, description, client_id, products, delivery_data=None, invoice_data=None):
    """
    Vytvoří novou operaci (příjemku/výdejku) a přiřadí k ní produkty.

    :param user: Přihlášený uživatel
    :param operation_type: Typ operace ("IN" nebo "OUT")
    :param number: Číslo operace
    :param description: Popis operace
    :param client_id: ID klienta
    :param products: Seznam produktů s množstvím a případnými daty (šarže, expirace, box)
    :param delivery_data: (volitelné) dodací údaje pro výdejku
    :param invoice_data: (volitelné) fakturační údaje pro výdejku
    :return: Objekt vytvořené operace nebo dict s chybou
    """
    try:
        if operation_type not in ['IN', 'OUT']:
            raise ValueError("Neplatný typ operace. Musí být 'IN' nebo 'OUT'.")

        try:
            client = Client.objects.get(id=client_id)
        except ObjectDoesNotExist:
            raise ValueError(f"Klient s ID {client_id} neexistuje.")

        with transaction.atomic():
            operation = Operation.objects.create(
                type=operation_type,
                status='CREATED',
                user=user,
                description=description,
                number=number,
                client=client
            )

            for product_data in products:
                try:
                    product = product_data["product_id"]
                    quantity = product_data["quantity"]
                    batch_number = product_data.get("batch_name")
                    expiration_date = product_data.get("expiration_date")
                    box_ean = product_data.get("box_name")

                    if operation_type == "IN":
                        box = create_new_box(box_ean)
                        add_group_to_in_operation(
                            operation=operation,
                            product_id=product.id,
                            batch_number=batch_number or '',
                            box_id=box.id if box else None,
                            quantity=quantity,
                            expiration_date=expiration_date
                        )
                    else:
                        add_group_to_out_operation(
                            operation=operation,
                            product_id=product.id,
                            batch_number=batch_number or '',
                            quantity=quantity,
                            expiration_date=expiration_date
                        )
                except ObjectDoesNotExist:
                    raise ValueError(f"Produkt s ID {product_data['productId'].id} neexistuje.")
                except Exception as e:
                    raise Exception(e)

            if operation_type == 'OUT' and delivery_data and invoice_data:
                set_delivery_data(operation, delivery_data)
                set_invoice_data(operation, invoice_data)

        return operation

    except ValueError as ve:
        return {"error": str(ve)}

    except Exception as e:
        return {"error": str(e)}

### 🔹 **Přidání skupiny do příjemky**
def add_group_to_in_operation(operation, product_id, batch_number, box_id, quantity, expiration_date=None):
    """
    Přidá novou skupinu (Group) do příjemky.

    :param operation: Operace, ke které se skupina přidává
    :param product_id: ID produktu
    :param batch_number: Název šarže
    :param box_id: ID krabice
    :param quantity: Množství
    :param expiration_date: (volitelné) expirace šarže
    :return: Vytvořená skupina
    """
    product = Product.objects.get(id=product_id)

    # ✅ Ověření, zda už existuje stejná šarže v rámci této operace
    existing_group = operation.groups.filter(batch__batch_number=batch_number).exists()
    if existing_group:
        raise ValueError(f"Šarže {batch_number} už byla do této příjemky přidána.")

    if expiration_date:
        expiration_date = datetime.fromisoformat(expiration_date)

    if expiration_date == "":
        expiration_date = None

    # ✅ Pokud neexistuje, vytvoříme nebo načteme šarži (Batch)
    batch, created = Batch.objects.get_or_create(
        product=product,
        batch_number=batch_number,
        defaults={"expiration_date": expiration_date}
    )

    # ✅ Vytvoření nové krabice, pokud není definována
    box = Box.objects.get(id=box_id) if box_id else None

    # ✅ Vytvoření nové skupiny (Group) a přidání do operace
    group = Group.objects.create(
        batch=batch,
        box=box,
        quantity=quantity
    )
    operation.groups.add(group)

    # ✅ Aktualizace množství produktu
    product.refresh_from_db()
    return group

def add_group_to_out_operation(operation, product_id, quantity, batch_number=None, expiration_date=None):
    """
    Přidá existující skupinu (Group) do výdejky – případně ji rozdělí.

    :param operation: Výdejka
    :param product_id: ID produktu
    :param quantity: Požadované množství
    :param batch_number: (volitelné) Šarže
    :param expiration_date: (volitelné) Expirace
    :return: Seznam přidaných nebo rozdělených skupin
    """
    product = Product.objects.get(id=product_id)
    quantity = int(quantity)

    # Filtrujeme existující groups s tímto produktem, šarží a expirací (pokud jsou specifikovány)
    existing_groups = Group.objects.filter(
        batch__product=product
    )

    if batch_number:
        existing_groups = existing_groups.filter(batch__batch_number=batch_number)
    if expiration_date:
        existing_groups = existing_groups.filter(batch__expiration_date=expiration_date)

    existing_groups.annotate(total_quantity=Sum("quantity")).order_by("batch__expiration_date")

    if not existing_groups:
        raise ValueError(f"Nenalezena žádná dostupná groupa pro produkt {product_id} se šarží {batch_number}.")

    total_available = sum(group.quantity for group in existing_groups)
    if total_available < quantity:
        raise ValueError(
            f"Nedostatečné zásoby pro produkt {product_id}. Požadováno {quantity}, dostupné {total_available}.")

    selected_groups = []
    selected_quantity = 0

    for group in existing_groups:
        if selected_quantity + group.quantity < quantity:
            selected_groups.append(group)
            selected_quantity += group.quantity
        elif selected_quantity + group.quantity == quantity:
            selected_groups.append(group)
            selected_quantity += group.quantity
            break
        else:
            # Poslední groupa přesahuje požadované množství – rozdělíme ji
            remaining_quantity = group.quantity - (quantity - selected_quantity)

            # Vytvoříme novou `group`, která zůstane v původních operacích
            new_group = Group.objects.create(
                batch=group.batch,
                box=group.box,
                quantity=remaining_quantity
            )

            # Přiřadíme novou `group` do stejných operací jako původní `group`
            new_group_operations = group.operations.all()
            for existing_operation in new_group_operations:
                existing_operation.groups.add(new_group)

            # Upravit původní `group` pro výdejku
            group.quantity = quantity - selected_quantity
            selected_groups.append(group)
            selected_quantity += group.quantity
            group.save()
            break

        # Přidáme vybrané `groups` do výdejky
    for group in selected_groups:
        operation.groups.add(group)

    return selected_groups


### 🔹 **Funkce pro správu krabic**
def create_new_box(ean):
    """
    Vytvoří novou krabici podle zadaného EAN.

    :param ean: EAN krabice
    :return: Objekt krabice
    """
    return Box.objects.create(ean=ean or '')


### 🔹 **Přidání dodacích údajů k výdejce**
def set_delivery_data(operation, delivery_data):
    """
    Nastaví dodací údaje pro výdejku.

    :param operation: Výdejka
    :param delivery_data: Slovník s dodacími údaji
    """
    operation.delivery_name = delivery_data.get("delivery_name")
    operation.delivery_street = delivery_data.get("delivery_street")
    operation.delivery_city = delivery_data.get("delivery_city")
    operation.delivery_psc = delivery_data.get("delivery_psc")
    operation.delivery_country = delivery_data.get("delivery_country", "CZ")
    operation.delivery_phone = delivery_data.get("delivery_phone")
    operation.delivery_email = delivery_data.get("delivery_email")
    operation.save()

def set_invoice_data(operation, invoice_data):
    """
    Nastaví fakturační údaje pro výdejku.

    :param operation: Výdejka
    :param invoice_data: Slovník s fakturačními údaji
    """
    operation.invoice_name = invoice_data.get("invoice_name")
    operation.invoice_street = invoice_data.get("invoice_street")
    operation.invoice_city = invoice_data.get("invoice_city")
    operation.invoice_psc = invoice_data.get("invoice_psc")
    operation.invoice_country = invoice_data.get("invoice_country", "CZ")
    operation.invoice_phone = invoice_data.get("invoice_phone")
    operation.invoice_email = invoice_data.get("invoice_email")
    operation.invoice_ico = invoice_data.get("invoice_ico")
    operation.invoice_vat = invoice_data.get("invoice_vat")
    operation.save()

def update_operation(operation, data):
    """
    Aktualizuje operaci o zadaná data.

    :param operation: Operace
    :param data: Slovník s aktualizačními daty
    :return: Aktualizovaná operace
    """
    allowed_fields = [
        "description",
        "number",
        "status",
        'delivery_date',
        'delivery_name',
        'delivery_street',
        'delivery_city',
        'delivery_psc',
        'delivery_country',
        'delivery_phone',
        'delivery_email',
        'delivery_note',
        'invoice_name',
        'invoice_street',
        'invoice_city',
        'invoice_psc',
        'invoice_country',
        'invoice_phone',
        'invoice_email',
        'invoice_ico',
        'invoice_vat'
    ]

    for field in allowed_fields:
        if field in data['delivery_data']:
            setattr(operation, field, data['delivery_data'][field])
        elif field in data['invoice_data']:
            setattr(operation, field, data['invoice_data'][field])
        else:
            if field in data:
                setattr(operation, field, data[field])

    operation.save()
    return operation

def remove_operation(operation):
    """
    Smaže operaci pokud je to možné podle typu.

    :param operation: Operace ke smazání
    :return: True pokud úspěšně smazána
    :raises: Exception pokud nelze smazat
    """
    if operation.type == 'IN':
        groups = operation.groups.all()
        other_operations_exist = any(
            group.operations.exclude(id=operation.id).exists() for group in groups
        )
        if not other_operations_exist:
             batch_id = operation.groups.all().values_list('batch__id', flat=True)
             batches = Batch.objects.filter(id__in=batch_id)
             batches.delete()
             operation.groups.all().delete()
             operation.delete()
             return True
        else:
            raise Exception('Operaci nelze smazat')

    if operation.type == 'OUT':
        operation.groups = None
        operation.save()
        operation.delete()
        return True

def add_product_to_box(operation_id, box_id, product_id, quantity):
    """
    Přidá produkt do krabice v rámci dané operace, případně rozdělí groupy.

    :param operation_id: ID operace
    :param box_id: ID krabice
    :param product_id: ID produktu
    :param quantity: Množství
    :return: Slovník s potvrzením
    """
    with transaction.atomic():
        operation = get_object_or_404(Operation, id=operation_id)
        box = get_object_or_404(Box, id=box_id)
        product = get_object_or_404(Product, id=product_id)

        # Najdeme všechny grupy s tímto produktem, které ještě nejsou rescanned
        groups = operation.groups.filter(batch__product_id=product.id, rescanned=False).order_by('id')

        total_available = sum(group.quantity for group in groups)

        if quantity > total_available:
            raise ValidationError(f"Požadované množství ({quantity}) převyšuje dostupné množství ({total_available}).")

        if total_available < quantity:
            raise ValueError(
                f"Nedostatečné zásoby pro produkt {product.id}. Požadováno {quantity}, dostupné {total_available}.")

        remaining_quantity = quantity
        new_groups = []

        for group in groups:
            if remaining_quantity == 0:
                break

            if group.quantity <= remaining_quantity:
                # Přesuneme celou grupu a označíme ji jako `rescanned`
                group.box = box
                group.rescanned = True
                group.save()
                remaining_quantity -= group.quantity
                new_groups.append(group)

            else:
                # Rozdělíme grupu
                new_group = Group.objects.create(
                    batch=group.batch,
                    box=box,
                    quantity=remaining_quantity,
                    rescanned=True
                )
                group.quantity -= remaining_quantity
                group.save()
                new_groups.append(new_group)
                remaining_quantity = 0

        # Přidáme grupy do operace
        for group in new_groups:
            operation.groups.add(group)

        return {"message": f"Produkt {product.name} přidán do krabice {box.ean} v počtu {quantity} ks."}

def get_operation_product_summary(operation_id):
    """
    Vrátí seznam produktů v dané operaci a jejich množství (celkové a rescanned).

    :param operation_id: ID operace
    :return: List slovníků se souhrnem podle produktu
    """
    operation = get_object_or_404(Operation, id=operation_id)

    product_summary = {}

    for group in operation.groups.all():
        product_id = group.batch.product.id
        product_name = group.batch.product.name

        if product_id not in product_summary:
            product_summary[product_id] = {"id": product_id, "name": product_name, "total_quantity": 0, "rescanned": 0}

        product_summary[product_id]["total_quantity"] += group.quantity
        if group.rescanned:
            product_summary[product_id]["rescanned"] += group.quantity

    return list(product_summary.values())