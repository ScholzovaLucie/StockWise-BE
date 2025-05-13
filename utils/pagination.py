from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

class CustomPageNumberPagination(PageNumberPagination):
    # Výchozí počet položek na stránku
    page_size = 10

    # Umožňuje klientovi nastavit počet položek na stránku přes parametr `?page_size=XX`
    page_size_query_param = 'page_size'

    # Maximální počet položek na stránku
    max_page_size = 100

    # Vlastní parametr, kterým lze stránkování úplně vypnout: `?no_page=1`
    no_page_param = 'no_page'

    def paginate_queryset(self, queryset, request, view=None):
        # Pokud je v URL dotazu `no_page=1`, vrátí celý queryset bez stránkování
        if request.query_params.get(self.no_page_param) == '1':
            return None
        return super().paginate_queryset(queryset, request, view)

    def get_paginated_response(self, data):
        # Formát výstupní odpovědi se stránkováním
        return Response({
            'count': self.page.paginator.count,  # Celkový počet položek
            'results': data  # Aktuální stránka dat
        })