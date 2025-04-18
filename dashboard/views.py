# dashboard/api.py
from datetime import timedelta, datetime
from django.db.models import Q

from django.db.models.functions import TruncDay, TruncDate
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.utils.timezone import make_aware, now
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import Sum, Count

from batch.models import Batch
from group.models import Group
from product.models import Product
from operation.models import Operation
from history.models import History
from .models import UserDashboardConfig
from datetime import timedelta
from django.utils import timezone

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_config(request):
    """
    Načte nebo vytvoří konfiguraci dashboardu pro přihlášeného uživatele.
    Vrací pole widgetů a jejich layout.
    """
    stats = request.GET.get("stats")
    type = 'main'
    if stats:
        type = "stats"
    config, created = UserDashboardConfig.objects.get_or_create(user=request.user, type=type)
    data = config.config if isinstance(config.config, dict) else {}
    return Response({
        'widgets': data.get('widgets', []),
        'layout': data.get('layout', [])
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_dashboard_config(request):
    """
    Uloží novou konfiguraci dashboardu (widgety a layout) pro přihlášeného uživatele.
    Očekává data ve formátu { "widgets": [...], "layout": [...] }
    """
    stats = request.GET.get("stats")
    type = 'main'
    if stats:
        type = "stats"
    config, _ = UserDashboardConfig.objects.get_or_create(user=request.user, type=type)
    config.config = request.data
    config.save()
    return Response({'status': 'ok'})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_overview(request):
    """
    Vrací rozšířený přehled skladu:
      - celkový počet kusů (totalItems)
      - celková hodnota zásob (totalValue)
      - celkový počet produktů (totalProducts)
      - počet produktů s nulovým stavem (outOfStockProducts)
      - počet produktů s nízkým stavem zásob (lowStockCount)
      - počet produktů s blížící se expirací (expiringSoonCount)
      - nejzásobenější produkt (mostStockedProduct)
    """
    client_id = request.query_params.get("clientId")

    products = Product.objects.all()
    products = products.filter(client_id=client_id)

    total_items = sum(p.amount for p in products)
    total_value = total_items  # Pro ilustraci (můžete použít cenu apod.)
    total_products = products.count()

    out_of_stock_count = len([p for p in products if p.amount == 0])
    out_of_stock_value = ",".join([p.sku for p in products if p.amount == 0])

    low_stock_threshold = 10
    low_stock_count = len([p for p in products if 0 < p.amount < low_stock_threshold])
    low_stock_value = ",".join([p.sku for p in products if 0 < p.amount < low_stock_threshold])

    # Počet produktů s blížící se expirací – zde definujeme threshold 30 dnů
    expiring_soon_threshold = 30
    now = timezone.now().date()
    expiring_batches = Batch.objects.filter(
        expiration_date__isnull=False,
        expiration_date__lte=datetime.now() + timedelta(days=expiring_soon_threshold)
    )

    if client_id:
        expiring_batches = expiring_batches.filter(product__client_id=client_id)
    else:
        client_ids = request.user.client.all().values_list('id', flat=True)
        expiring_batches = expiring_batches.filter(product__client_id__in=client_ids)

    # Počet šarží s blížící se expirací
    expiring_soon_count = expiring_batches.count()

    # Ulož seznam ID šarží nebo jiný unikátní identifikátor (např. batch number)
    expiring_soon_value = ",".join(expiring_batches.values_list("batch_number", flat=True))

    most_stocked_product = max(products, key=lambda p: p.amount) if products.exists() else None
    most_stock_data = {
        "id": most_stocked_product.id,
        "name": most_stocked_product.name,
        "amount": most_stocked_product.amount,
    } if most_stocked_product else None

    return Response({
        "totalItems": total_items,
        "totalValue": total_value,
        "totalProducts": total_products,
        "outOfStockProducts": {
            'count': out_of_stock_count,
            'data': out_of_stock_value
        },
        "lowStockCount": {
            'count': low_stock_count,
            'data': low_stock_value
        },
        "expiringSoonCount": {
            'count': expiring_soon_count,
            'data': expiring_soon_value
        },
        "mostStockedProduct": most_stock_data,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_low_stock(request):
    """
    Vrací seznam produktů s nízkými zásobami (pod stanoveným prahem).
    """
    client_id = request.query_params.get("clientId")
    threshold = 10  # Prahová hodnota pro nízké zásoby
    products = Product.objects.all()
    client_id = request.GET.get('client')

    if client_id:
        products = products.filter(client_id=client_id)
    else:
        client_ids = request.user.client.all().values_list('id', flat=True)
        products = products.filter(client_id__in=client_ids)

    low_stock = [
        {
            "id": p.id,
            "name": p.name,
            "amount": p.amount,
        }
        for p in products if p.amount < threshold
    ]
    return Response(low_stock)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def dashboard_recent_activity(request):
    """
    Vrací statistiky historie s možností filtrování podle období (rok, měsíc, den) a typu aktivity.
    Pokud není specifikováno období, výchozí je poslední týden.
    """
    year = request.GET.get("filters[year]")
    month = request.GET.get("filters[month]")
    day = request.GET.get("filters[day]")
    from_date = request.GET.get("filters[from_date]")
    to_date = request.GET.get("filters[to_date]")
    client_id = request.query_params.get("clientId")

    history_query = History.objects.all()

    # Filtr podle období
    if from_date or to_date:
        if from_date:
            from_date = parse_date(from_date)
            history_query = history_query.filter(timestamp__gte=from_date)
        if to_date:
            to_date = parse_date(to_date)
            history_query = history_query.filter(timestamp__lte=to_date)
    elif year or month or day:
        if year:
            history_query = history_query.filter(timestamp__year=year)
        if month:
            history_query = history_query.filter(timestamp__month=month)
        if day:
            history_query = history_query.filter(timestamp__day=day)
    else:
        # Výchozí: posledních 7 dní
        last_week = datetime.today() - timedelta(days=7)
        history_query = history_query.filter(timestamp__gte=last_week)

    if client_id:
        product_ids = Product.objects.filter(client_id=client_id).values_list("id", flat=True)
        batch_ids = Batch.objects.filter(product_id__in=product_ids).values_list("id", flat=True)
        group_ids = Group.objects.filter(batch_id__in=batch_ids).values_list("id", flat=True)

        history_query = history_query.filter(
            Q(type="product", related_id__in=product_ids)
            | Q(type="operation",
                related_id__in=Operation.objects.filter(client_id=client_id).values_list("id", flat=True))
            | Q(type="batch", related_id__in=batch_ids)
            | Q(type="group", related_id__in=group_ids)
        )
    else:
        client_ids = request.user.client.all().values_list('id', flat=True)
        product_ids = Product.objects.filter(client_id__in=client_ids).values_list("id", flat=True)
        batch_ids = Batch.objects.filter(product_id__in=product_ids).values_list("id", flat=True)
        group_ids = Group.objects.filter(batch_id__in=batch_ids).values_list("id", flat=True)

        history_query = history_query.filter(
            Q(type="product", related_id__in=product_ids)
            | Q(type="operation",
                related_id__in=Operation.objects.filter(client_id=client_id).values_list("id", flat=True))
            | Q(type="batch", related_id__in=batch_ids)
            | Q(type="group", related_id__in=group_ids)
        )

    # 📊 Počet aktivit podle jednotlivých typů
    history_chart_data = (
        history_query
        .annotate(date=TruncDate("timestamp"))
        .values("date", "type")
        .annotate(count=Count("id"))
        .order_by("date", "type")
    )

    # 📝 Posledních 10 záznamů
    recent_history = history_query.values("id", "description", "timestamp", "type").order_by("-timestamp")[:10]

    # 🚀 Převedení dat do struktury, kterou frontend snadno použije
    chart_data = {}
    for entry in history_chart_data:
        date_str = entry["date"].strftime("%Y-%m-%d")
        type_str = entry["type"]
        if date_str not in chart_data:
            chart_data[date_str] = {}
        chart_data[date_str][type_str] = entry["count"]

    # Převod do pole objektů pro frontend
    formatted_chart_data = [
        {"date": date, **counts} for date, counts in chart_data.items()
    ]

    data = {
        "chart": formatted_chart_data,  # 📊 Data pro graf
        "recent": list(recent_history),  # 📝 Posledních 10 záznamů
    }

    return Response(data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_alerts(request):
    """
    Vrací seznam alertů – produkty s nízkým stavem zásob.
    """
    products = Product.objects.all()
    client_id = request.query_params.get("clientId")
    if client_id:
        products = products.filter(client_id=client_id)
    else:
        client_ids = request.user.client.all().values_list('id', flat=True)
        products = products.filter(client_id__=client_ids)

    threshold = 10
    alerts = [
        {
            "product": p.name,
            "amount": p.amount,
            "alert": "Nízky stav zásob"
        }
        for p in products if p.amount < threshold
    ]
    return Response(alerts)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_active_operations(request):
    client_id = request.query_params.get("clientId")
    operations = Operation.objects.all()
    if client_id:
        operations = operations.filter(client_id=client_id)
    else:
        client_ids = request.user.client.all().values_list('id', flat=True)
        operations = operations.filter(client_id__in=client_ids)

    active_ops = operations.filter(status__in=['CREATED', 'BOX']).order_by('-created_at')
    data = [{
        'id': op.id,
        'number': op.number,
        'type': op.type,
        'status': op.status,
        'created_at': op.created_at,
    } for op in active_ops]
    return Response(data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_stats(request):
    """
    Vrací statistiky operací s možností filtrování podle období.
    """
    year = request.GET.get("filters[year]")
    month = request.GET.get("filters[month]")
    day = request.GET.get("filters[day]")
    from_date = request.GET.get("filters[from_date]")
    to_date = request.GET.get("filters[to_date]")
    client_id = request.query_params.get("clientId")

    operations_query = Operation.objects.all()
    if client_id:
        operations_query = operations_query.filter(client_id=client_id)
    else:
        client_ids = request.user.client.all().values_list('id', flat=True)
        operations_query = operations_query.filter(client_id__in=client_ids)

    # 📆 Filtr podle období
    if from_date or to_date:
        if from_date:
            from_date = parse_date(from_date)
            operations_query = operations_query.filter(updated_at__gte=from_date)
        if to_date:
            to_date = parse_date(to_date)
            operations_query = operations_query.filter(updated_at__lte=to_date)
    elif year or month or day:
        if year:
            operations_query = operations_query.filter(updated_at__year=year)
        if month:
            operations_query = operations_query.filter(updated_at__month=month)
        if day:
            operations_query = operations_query.filter(updated_at__day=day)

    # 📊 Počet operací podle stavu
    total_operations = operations_query.count()
    completed_operations = operations_query.filter(status='COMPLETED').count()
    cancelled_operations = operations_query.filter(status='CANCELLED').count()
    in_progress_operations = operations_query.filter(status__in=['CREATED', 'BOX']).count()

    return Response({
        'totalOperations': total_operations,
        'completedOperations': completed_operations,
        'cancelledOperations': cancelled_operations,
        'inProgressOperations': in_progress_operations,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_efficiency(request):
    """
    Vrací statistiku efektivity skladu.
    """
    now_time = now()
    week_ago = now_time - timedelta(days=7)
    client_id = request.query_params.get("clientId")
    operations = Operation.objects.all()
    if client_id:
        operations = operations.filter(client_id=client_id)
    else:
        client_ids = request.user.client.all().values_list('id', flat=True)
        operations = operations.filter(client_id__in=client_ids)

    # 📊 Celkové operace
    total_operations = operations.count()
    completed_operations = operations.filter(status='COMPLETED').count()
    efficiency = (completed_operations / total_operations * 100) if total_operations > 0 else 0

    # 📊 Efektivita za poslední týden
    total_week = operations.filter(created_at__gte=week_ago).count()
    completed_week = operations.filter(status='COMPLETED', created_at__gte=week_ago).count()
    weekly_efficiency = (completed_week / total_week * 100) if total_week > 0 else 0

    # 📊 Průměrná historická efektivita
    all_efficiencies = operations.values("status").annotate(count=Count("id"))
    avg_efficiency = sum([
        (op["count"] / total_operations * 100)
        for op in all_efficiencies if op["status"] == "COMPLETED"
    ]) if total_operations > 0 else 0

    return Response({
        'efficiency': efficiency,
        'weeklyEfficiency': weekly_efficiency,
        'avgEfficiency': avg_efficiency,
        'description': 'Procento dokončených operací',
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_widgets(request):
    dashboard_type = 'main'
    if request.query_params.get("stats"):
        dashboard_type = 'stats'

    config, created = UserDashboardConfig.objects.get_or_create(user=request.user, type=dashboard_type)
    data = config.config if isinstance(config.config, dict) else {}
    return Response(data.get('widgets', []))


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def save_widgets(request):
    dashboard_type = 'main'
    if request.data.get("stats"):
        dashboard_type = 'stats'

    config, _ = UserDashboardConfig.objects.get_or_create(user=request.user, type=dashboard_type)
    widgets = request.data.get('widgets', [])
    current_config = config.config if isinstance(config.config, dict) else {}
    current_config['widgets'] = widgets
    config.config = current_config
    config.save()
    return Response({'status': 'ok'})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_extended_stats(request):
    # 📊 Trend operací za poslední týden pro každého uživatele
    client_id = request.query_params.get("clientId")
    operations = Operation.objects.all()
    if client_id:
        operations = operations.filter(client_id=client_id)

    trend_data = (
        operations
        .filter()
        .annotate(day=TruncDay("created_at"))
        .values("day", "user__name")
        .annotate(count=Count("id"))
        .order_by("day", "user__name")
    )

    # ⏳ Průměrná doba dokončení operací
    completed_ops = operations.filter(status="COMPLETED")
    total_duration = 0
    count = 0
    for op in completed_ops:
        if op.created_at and op.updated_at:
            duration = (op.updated_at - op.created_at).total_seconds() / 60
            total_duration += duration
            count += 1
    avg_completion_time = total_duration / count if count > 0 else 0

    # 👥 Nejaktivnější skladníci
    top_users = (
        operations.values("user__name")
        .annotate(op_count=Count("id"))
        .order_by("-op_count")[:5]
    )

    return Response({
        "trend": list(trend_data),
        "avgCompletionTime": avg_completion_time,
        "topUsers": list(top_users),
    })