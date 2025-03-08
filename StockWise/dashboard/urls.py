# dashboard/urls.py
from django.urls import path
from dashboard.views import *

urlpatterns = [
    path('config/', dashboard_config, name='dashboard_config'),
    path('config/update/', update_dashboard_config, name='update_dashboard_config'),
    path('overview/', dashboard_overview, name='dashboard_overview'),
    path('alerts/', dashboard_alerts, name='dashboard_alerts'),
    path('active_operations/', dashboard_active_operations, name='dashboard_active_operations'),
    path('stats/', dashboard_stats, name='dashboard_stats'),
    path('efficiency/', dashboard_efficiency, name='dashboard_efficiency'),
    path('my_widgets/', my_widgets, name='my_widgets'),
    path('save_widgets/', save_widgets, name='save_widgets'),
    path('extended_stats/', dashboard_extended_stats, name='extended_stats'),
    path('low_stock/', dashboard_low_stock, name='dashboard_low_stock'),
    path('recent_activity/', dashboard_recent_activity, name='dashboard_recent_activity'),
]