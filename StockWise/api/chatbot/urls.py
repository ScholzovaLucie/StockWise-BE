# -*- coding: UTF-8 -*-
from django.urls import path

from api.chatbot.view import ChatbotView

urlpatterns = [
    path("", ChatbotView.as_view(), name="chatbot"),
]