from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.http import JsonResponse
from rest_framework import viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken, AccessToken
from django.contrib.auth import authenticate
from django.contrib.auth.hashers import make_password
from user.models import User
from user.serializers import UserSerializer
import logging

logger = logging.getLogger(__name__)

def is_strong_password(password):
    """Ověří, zda heslo splňuje bezpečnostní pravidla."""
    return (
        len(password) >= 8 and
        any(c.isdigit() for c in password) and
        any(c.isupper() for c in password) and
        any(c in "!@#$%^&*()_+" for c in password)
    )

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        # Ošetření pro Swagger
        if getattr(self, 'swagger_fake_view', False):
            return User.objects.none()  # Swagger nemá přístup k datům

        if user.is_superuser:  # Admin vidí všechny
            return User.objects.all()
        return User.objects.filter(id=user.id).only('id')

@api_view(['POST'])
@permission_classes([AllowAny])
def register_user(request):
    """Endpoint pro registraci nového uživatele."""
    email = request.data.get("email")
    password = request.data.get("password")

    if not email or not password:
        return Response({"error": "Všechna pole jsou povinná."}, status=400)

    if not is_strong_password(password):
        return Response({"error": "Heslo musí mít alespoň 12 znaků, jedno číslo, jedno velké písmeno a speciální znak."}, status=400)

    if User.objects.filter(email=email).exists():
        return Response({"error": "Uživatel s tímto e-mailem již existuje."}, status=400)

    user = User.objects.create(
        email=email,
        password=make_password(password)
    )

    logger.info(f"Nový uživatel {email} zaregistrován.")
    return Response({"message": "Registrace byla úspěšná.", "user": UserSerializer(user).data}, status=201)


@api_view(['POST'])
@permission_classes([AllowAny])
def login_user(request):
    """Endpoint pro přihlášení uživatele a vrácení JWT tokenu v bezpečných cookies."""
    email = request.data.get("email")
    password = request.data.get("password")

    user = authenticate(request, username=email, password=password)
    if user is None or not user.is_active:
        return Response({"error": "Neplatné přihlašovací údaje nebo uživatel je deaktivován."}, status=401)

    refresh = RefreshToken.for_user(user)
    access_token = str(refresh.access_token)

    response = JsonResponse({"message": "Přihlášení úspěšné.", "user": UserSerializer(user).data})
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=True,
        samesite="Strict"
    )
    response.set_cookie(
        key="refresh_token",
        value=str(refresh),
        httponly=True,
        secure=True, 
        samesite="Strict"
    )

    return response


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_user(request):
    """Odhlásí uživatele a odstraní cookies s tokeny."""
    response = JsonResponse({"message": "Odhlášení proběhlo úspěšně."})
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")

    return response


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_authenticated_user(request):
    """Endpoint `/auth/me` vrátí informace o přihlášeném uživateli."""
    user = request.user
    return Response(UserSerializer(user).data)


@api_view(['POST'])
@permission_classes([AllowAny])
def refresh_token(request):
    """
    Endpoint pro obnovu access tokenu pomocí refresh tokenu uloženého v cookie.
    """
    try:
        refresh_token = request.COOKIES.get("refresh_token")
        if not refresh_token:
            return Response({"detail": "Refresh token není k dispozici."}, status=401)

        refresh = RefreshToken(refresh_token)
        new_access_token = str(refresh.access_token)

        response = JsonResponse({"access_token": new_access_token})
        response.set_cookie(
            key="access_token",
            value=new_access_token,
            httponly=True,
            secure=False,  # Nastav na True v produkci
            samesite="Lax"
        )
        return response
    except Exception as e:
        print("Chyba při obnovování tokenu:", e)
        return Response({"detail": "Obnovení tokenu selhalo."}, status=401)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def change_password(request):
    """
    Endpoint pro změnu hesla
    """
    old_password = request.data.get('old_password')
    new_password = request.data.get('new_password')
    confirm_password = request.data.get('confirm_password')

    if new_password != confirm_password:
        return Response({"error": "Nová hesla se neshodují."}, status=400)

    user = request.user
    if not user.check_password(old_password):
        return Response({"error": "Staré heslo není správné."}, status=400)

    user.set_password(new_password)
    user.save()

    return Response({"message": "Heslo bylo úspěšně změněno."}, status=200)

def create_password_reset_token(user):
    token = AccessToken.for_user(user)
    token.set_exp(lifetime=timedelta(minutes=15))
    token["type"] = "password_reset"
    return str(token)

@api_view(['POST'])
@permission_classes([AllowAny])
def request_password_reset(request):
    email = request.data.get("email")
    if not email:
        return Response({"error": "Email je povinný."}, status=400)

    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        return Response({"error": "Uživatel s tímto emailem neexistuje."}, status=404)

    token = create_password_reset_token(user)
    reset_link = f"{settings.FRONTEND_URL}/auth/login/reset-password?token={token}"

    send_mail(
        subject="Obnova hesla",
        message=f"Klikněte na tento odkaz pro reset hesla: {reset_link}",
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[email],
        fail_silently=False,
    )

    return Response({"message": "Odkaz pro reset hesla byl odeslán na email."})


@api_view(['POST'])
@permission_classes([AllowAny])
def reset_password(request):
    token = request.data.get("token")
    new_password = request.data.get("new_password")
    confirm_password = request.data.get("confirm_password")

    if not token or not new_password or not confirm_password:
        return Response({"error": "Všechna pole jsou povinná."}, status=400)

    if new_password != confirm_password:
        return Response({"error": "Hesla se neshodují."}, status=400)

    try:
        decoded_token = AccessToken(token)
        if decoded_token.get("type") != "password_reset":
            return Response({"error": "Neplatný typ tokenu."}, status=400)
        user_id = decoded_token["user_id"]
        user = User.objects.get(id=user_id)
    except (TokenError, User.DoesNotExist):
        return Response({"error": "Token je neplatný nebo expiroval."}, status=400)

    user.set_password(new_password)
    user.save()

    return Response({"message": "Heslo bylo úspěšně změněno."}, status=200)