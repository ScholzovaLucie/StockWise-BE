from django.urls import path
from user.views import *

urlpatterns = [
    path('register/', register_user, name="register"),
    path('login/', login_user, name="login"),
    path('logout/', logout_user, name="logout"),
    path('me/', get_authenticated_user, name='auth-me'),
    path('refresh/', get_authenticated_user, name='refresh-token'),
]