"""
URL configuration for StockWise project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from django.urls import path, re_path
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

from batch.views import BatchViewSet
from box.views import BoxViewSet
from chat_log.views import ChatLogViewSet
from chatbot.fast_prompts.views import FastPromptsAPI
from chatbot.views import ChatbotView, StatisticsView
from client.views import ClientViewSet
from client_role.views import ClientRoleViewSet
from client_user_role.views import ClientUserRoleViewSet
from group.views import GroupViewSet
from history.views import HistoryViewSet
from operation.views import OperationViewSet
from position.views import PositionViewSet
from product.views import ProductViewSet
from stock_change.views import StockChangeViewSet
from user.views import UserViewSet
from warehouse.views import WarehouseViewSet


schema_view = get_schema_view(
    openapi.Info(
        title="StockWise API",
        default_version='v1',
        description="API dokumentace pro StockWise skladovou aplikaci",
        terms_of_service="https://www.google.com/policies/terms/",
        contact=openapi.Contact(email="lucka.scholz@gmail.com"),
        license=openapi.License(name="MIT License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)


# Nastavení routeru
router = DefaultRouter()
router.register(r'clients', ClientViewSet)
router.register(r'client_roles', ClientRoleViewSet)
router.register(r'client_user_roles', ClientUserRoleViewSet)
router.register(r'users', UserViewSet)
router.register(r'batches', BatchViewSet)
router.register(r'warehouses', WarehouseViewSet)
router.register(r'operations', OperationViewSet)
router.register(r'groups', GroupViewSet)
router.register(r'positions', PositionViewSet)
router.register(r'histories', HistoryViewSet)
router.register(r'boxes', BoxViewSet)
router.register(r'stock_changes', StockChangeViewSet)
router.register(r'chat_logs', ChatLogViewSet)
router.register(r'products', ProductViewSet)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include(router.urls)),
    path('api/products/', include('product.urls'), name="products"),
    path('api/auth/', include('user.urls')),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    path('api/dashboard/', include('dashboard.urls')),
    path("api/chatbot", ChatbotView.as_view(), name="chatbot"),
    path("api/statistics", StatisticsView.as_view(), name="chatbot_statistics"),
    path(r'api/chatbot/fast_prompts', FastPromptsAPI.as_view()),
]
