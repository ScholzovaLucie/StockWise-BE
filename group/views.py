from functools import reduce

from django.shortcuts import get_object_or_404
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from django.db.models import Q

from group.models import Group
from group.serializers import GroupSerializer, GroupListSerializer
from utils.pagination import CustomPageNumberPagination


# Create your views here.
class GroupViewSet(viewsets.ModelViewSet):
    queryset = Group.objects.all()
    serializer_class = GroupSerializer

    def get_queryset(self):
        client_id = self.request.GET.get('client_id')
        client_ids = self.request.user.client.all().values_list('id', flat=True)

        queryset = Group.objects.select_related(
            "batch__product",
            "box"
        ).prefetch_related("operations").filter(
            batch__product__client_id__in=client_ids
        )

        if client_id:
            queryset = queryset.filter(batch__product__client_id=client_id)

        return queryset

    def get_serializer_class(self):
        if self.action == "list":
            return GroupListSerializer
        return GroupSerializer

    @action(detail=False, methods=['get'], url_path='search')
    def search(self, request):
        query = request.GET.get('q', '')
        client_id = request.GET.get('clientId', '')

        if not query:
            return Response({"detail": "Query parameter 'q' is required."}, status=status.HTTP_400_BAD_REQUEST)

        data_query = query.split(',')
        if len(data_query) > 1:
            data_query = [term.strip() for term in data_query if term.strip()]
            query_filters = reduce(
                lambda q, term: q |
                                Q(id__icontains=term) |
                                Q(batch__batch_number__icontains=term) |
                                Q(batch__product__sku__icontains=term) |
                                Q(batch__product__name__icontains=term) |
                                Q(box__ean__icontains=term),
                data_query,
                Q()
            )

            groups = Group.objects.filter(query_filters).only("id")

        else:
            groups = Group.objects.filter(
                Q(id__icontains=query) |
                Q(batch__product__sku__icontains=query) |
                Q(batch__product__name__icontains=query) |
                Q(batch__batch_number__icontains=query) |
                Q(box__ean__icontains=query)
            )

        if client_id:
            groups = groups.filter(batch__item__client_id=client_id)

        paginator = CustomPageNumberPagination()
        paginator.page_size = request.GET.get('page_size') or 10
        paginated_data = paginator.paginate_queryset(groups, request)

        serializer = self.get_serializer(paginated_data, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='remove_from_box')
    def remove_from_box(self, request, pk=None):
        """
        Odebere grupu z krabice (resetuje její box na None)
        """
        group = get_object_or_404(Group, id=pk)

        # Odebereme krabici (box) z grupy
        group.box = None
        group.rescanned = False  # Reset flag
        group.save()

        return Response({"message": f"Produkt {group.batch.product.name} odebrán z krabice."}, status=200)

