# dashboard/urls.py
from django.urls import path
from dashboard.views import *

urlpatterns = [
    path('overview/', dashboard_overview, name='dashboard_overview'),
    path('alerts/', dashboard_alerts, name='dashboard_alerts'),
    path('active_operations/', dashboard_active_operations, name='dashboard_active_operations'),
    path('stats/', dashboard_stats, name='dashboard_stats'),
    path('efficiency/', dashboard_efficiency, name='dashboard_efficiency'),
    path('extended_stats/', dashboard_extended_stats, name='extended_stats'),
    path('low_stock/', dashboard_low_stock, name='dashboard_low_stock'),
    path('recent_activity/', dashboard_recent_activity, name='dashboard_recent_activity'),

    path('my_widgets/', my_widgets, name='my_widgets'),
    path('save_widgets/', save_widgets, name='save_widgets'),
]