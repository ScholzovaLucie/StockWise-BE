from django.http import JsonResponse
from rest_framework import viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
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
        return User.objects.filter(clients_managed__in=user.clients_managed.all()).distinct()

@api_view(['POST'])
@permission_classes([])
def register_user(request):
    """Endpoint pro registraci nového uživatele."""
    email = request.data.get("email")
    password = request.data.get("password")

    if not email or not password:
        return Response({"error": "Všechna pole jsou povinná."}, status=400)

    if not is_strong_password(password):
        return Response({"error": "Heslo musí mít alespoň 8 znaků, jedno číslo, jedno velké písmeno a speciální znak."}, status=400)

    if User.objects.filter(email=email).exists():
        return Response({"error": "Uživatel s tímto e-mailem již existuje."}, status=400)

    user = User.objects.create(
        email=email,
        password=make_password(password)  # Hashování hesla
    )

    logger.info(f"Nový uživatel {email} zaregistrován.")
    return Response({"message": "Registrace byla úspěšná.", "user": UserSerializer(user).data}, status=201)

@api_view(['POST'])
@permission_classes([])
def login_user(request):
    """Endpoint pro přihlášení uživatele a vrácení JWT tokenu."""
    email = request.data.get("email")
    password = request.data.get("password")

    user = authenticate(request, username=email, password=password)
    if user is None:
        return Response({"error": "Neplatné přihlašovací údaje."}, status=401)

    refresh = RefreshToken.for_user(user)
    access_token = str(refresh.access_token)

    response = JsonResponse({"message": "Přihlášení úspěšné."})
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=False,  # Změň na True v produkci
        samesite="Lax"
    )
    response.set_cookie(
        key="refresh_token",
        value=str(refresh),
        httponly=True,
        secure=False,  # Změnit na True v produkci
        samesite="Lax"
    )

    return response


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_user(request):
    """Endpoint pro odhlášení uživatele – zneplatnění refresh tokenu."""
    try:
        refresh_token = request.data.get("refresh")
        token = RefreshToken(refresh_token)
        token.blacklist()
        logger.info("Refresh token zneplatněn, uživatel odhlášen.")
        return Response({"message": "Odhlášení proběhlo úspěšně."}, status=200)
    except Exception as e:
        logger.error(f"Chyba při odhlašování: {e}")
        return Response({"error": "Chyba při odhlašování."}, status=400)

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