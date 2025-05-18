import pytest
from user.models import User
from operation.services.operation_service import *


# Fixture pro vytvoření uživatele a klienta
@pytest.fixture
def user_with_client(client_factory):
    client = client_factory()
    user = User.objects.create(email='testuser@example.com', password='pass')
    user.client.add(client)
    return user

# Fixture pro vytvoření testovacího produktu
@pytest.fixture
def test_product(user_with_client):
    client = user_with_client.client.first()
    return Product.objects.create(name='Test Product', sku='TP001', client=client)


# Testuje vytvoření nové krabice
@pytest.mark.django_db
def test_create_new_box():
    box = create_new_box('BOX123')
    assert box.ean == 'BOX123'


# Testuje přidání skupiny do IN operace – vytvoření batch, group, přiřazení boxu
@pytest.mark.django_db
def test_add_group_to_in_operation_creates_group(user_with_client, test_product):
    client = user_with_client.client.first()
    operation = Operation.objects.create(number='IN001', type='IN', status='CREATED', user=user_with_client, client=client)
    box = create_new_box('EAN001')
    group = add_group_to_in_operation(operation, test_product.id, 'B001', box.id, 10, '2099-12-31')
    assert group.quantity == 10
    assert group.batch.batch_number == 'B001'


# Testuje výběr správných skupin pro OUT operaci podle batch a quantity
@pytest.mark.django_db
def test_add_group_to_out_operation_selects_correct_groups(user_with_client, test_product):
    batch = Batch.objects.create(batch_number='B002', product=test_product)
    group = Group.objects.create(batch=batch, quantity=10)
    operation = Operation.objects.create(number='OUT001', type='OUT', status='CREATED', user=user_with_client, client=test_product.client)
    selected_groups = add_group_to_out_operation(operation, test_product.id, 5, 'B002')
    assert sum(g.quantity for g in selected_groups) == 5


# Testuje nastavení dodacích údajů operace
@pytest.mark.django_db
def test_set_delivery_data(user_with_client):
    operation = Operation.objects.create(number='OPD001', type='OUT', status='CREATED', user=user_with_client, client=user_with_client.client.first())
    data = {"delivery_name": "Name", "delivery_street": "Street", "delivery_city": "City", "delivery_psc": "12345"}
    set_delivery_data(operation, data)
    assert operation.delivery_name == "Name"


# Testuje nastavení fakturačních údajů operace
@pytest.mark.django_db
def test_set_invoice_data(user_with_client):
    operation = Operation.objects.create(number='OPI001', type='OUT', status='CREATED', user=user_with_client, client=user_with_client.client.first())
    data = {"invoice_name": "Firm", "invoice_city": "City", "invoice_psc": "12345"}
    set_invoice_data(operation, data)
    assert operation.invoice_name == "Firm"


# Testuje aktualizaci operace – popis + adresy
@pytest.mark.django_db
def test_update_operation_updates_fields(user_with_client):
    operation = Operation.objects.create(number='U001', type='OUT', status='CREATED', user=user_with_client, client=user_with_client.client.first())
    updated = update_operation(operation, {
        "description": "Popis",
        "delivery_data": {"delivery_city": "New City"},
        "invoice_data": {"invoice_city": "Invo City"}
    })
    assert updated.description == "Popis"
    assert updated.delivery_city == "New City"
    assert updated.invoice_city == "Invo City"


# Testuje odstranění IN operace – včetně odstranění napojených skupin
@pytest.mark.django_db
def test_remove_operation_in_type(user_with_client, test_product):
    client = user_with_client.client.first()
    batch = Batch.objects.create(product=test_product, batch_number="B004")
    group = Group.objects.create(batch=batch, quantity=5)
    operation = Operation.objects.create(type='IN', number='R001', status='CREATED', client=client, user=user_with_client)
    operation.groups.add(group)
    assert remove_operation(operation) is True
    assert not Operation.objects.filter(id=operation.id).exists()


# Testuje přidání produktu do boxu pomocí `add_product_to_box`
@pytest.mark.django_db
def test_add_product_to_box(user_with_client, test_product):
    client = user_with_client.client.first()
    batch = Batch.objects.create(product=test_product, batch_number="B005")
    group = Group.objects.create(batch=batch, quantity=10)
    operation = Operation.objects.create(type='IN', number='B001', status='CREATED', client=client, user=user_with_client)
    operation.groups.add(group)
    box = create_new_box("EANBOX")
    result = add_product_to_box(operation.id, box.id, test_product.id, 5)
    assert "EANBOX" in result['message']


# Testuje získání souhrnu produktů v operaci (celkové množství atd.)
@pytest.mark.django_db
def test_get_operation_product_summary(user_with_client, test_product):
    batch = Batch.objects.create(product=test_product, batch_number="SUM001")
    group = Group.objects.create(batch=batch, quantity=5)
    operation = Operation.objects.create(type='IN', number='SUM01', status='CREATED', client=test_product.client, user=user_with_client)
    operation.groups.add(group)
    summary = get_operation_product_summary(operation.id)
    assert summary[0]["total_quantity"] == 5


# Testuje úspěšné vytvoření IN operace pomocí `create_operation`
@pytest.mark.django_db
def test_create_operation_in_success(user_with_client, test_product):
    client = user_with_client.client.first()
    result = create_operation(
        user=user_with_client,
        operation_type="IN",
        number="IN999",
        description="Test příjem",
        client_id=client.id,
        products=[{
            "product_id": test_product,
            "quantity": 3,
            "batch_name": "BATCH_IN",
            "expiration_date": "2099-12-31",
            "box_name": "BOX-IN-001"
        }],
        delivery_data={},
        invoice_data={}
    )
    assert isinstance(result, Operation)
    assert result.groups.count() == 1


# Testuje chybějící skupinu (neexistující batch) při vytváření OUT operace – očekává se chybová odpověď
@pytest.mark.django_db
def test_create_operation_out_missing_group(user_with_client, test_product):
    client = user_with_client.client.first()
    result = create_operation(
        user=user_with_client,
        operation_type="OUT",
        number="OUT999",
        description="Test výdej",
        client_id=client.id,
        products=[{
            "product_id": test_product,
            "quantity": 10,
            "batch_name": "NONEXIST",
            "expiration_date": "2099-12-31"
        }],
        delivery_data={},
        invoice_data={}
    )
    assert isinstance(result, dict)
    assert "error" in result


# Testuje zadání neplatného typu operace (např. "XYZ") – očekává se chybová odpověď
@pytest.mark.django_db
def test_create_operation_invalid_type(user_with_client, test_product):
    client = user_with_client.client.first()
    result = create_operation(
        user=user_with_client,
        operation_type="XYZ",
        number="ERR001",
        description="Chybný typ",
        client_id=client.id,
        products=[],
        delivery_data={},
        invoice_data={}
    )
    assert isinstance(result, dict)
    assert result["error"] == "Neplatný typ operace. Musí být 'IN' nebo 'OUT'."