from django.urls import path
from user.views import *

urlpatterns = [
    path('register/', register_user, name="register"),
    path('login/', login_user, name="login"),
    path('logout/', logout_user, name="logout"),
    path('me/', get_authenticated_user, name='auth-me'),
    path('refresh/', refresh_token, name='refresh-token'),
    path('change-password/', change_password, name='change_password'),
    path('request-password-reset/', request_password_reset, name='request_password_reset'),
    path('reset-password/', reset_password, name='reset_password'),
]