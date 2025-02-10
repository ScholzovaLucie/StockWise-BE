# -*- coding: UTF-8 -*-
from django.urls import path

from operation.views import *


urlpatterns = [
    path('create_operation', create_operation_view, name="create_operation"),
    path('add_group_to_operation_view/<int:operation_id>/', add_group_to_operation_view, name="add_group_to_operation_view"),
    path('process_operation_view/<int:operation_id>/', process_operation_view, name="process_operation_view"),
]