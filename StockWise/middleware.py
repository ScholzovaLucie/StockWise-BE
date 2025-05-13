from django.contrib.auth import get_user_model
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.exceptions import AuthenticationFailed
import logging

logger = logging.getLogger(__name__)

User = get_user_model()

# Vlastní autentizační třída, která zkusí JWT token získat z cookies (a případně i z hlavičky)
class CookieJWTAuthentication(JWTAuthentication):
    def authenticate(self, request):
        # Získání access tokenu z cookie
        access_token = request.COOKIES.get('access_token')

        # Pokud není token v cookies, zkus ho získat z hlavičky Authorization
        if not access_token:
            auth_header = request.META.get('HTTP_AUTHORIZATION')
            if auth_header and auth_header.startswith('Bearer '):
                access_token = auth_header.split(' ')[1]  # Odstranění prefixu "Bearer"

        # Pokud stále není token dostupný, vrať None
        if not access_token:
            return None

        try:
            # Validace tokenu (ověření platnosti a dekódování)
            validated_token = self.get_validated_token(access_token)

            # Načtení uživatele na základě tokenu
            user = self.get_user(validated_token)

            return (user, validated_token)
        except AuthenticationFailed as e:
            # Logování chyby při autentizaci (např. expirovaný token)
            logger.warning(f"Authentication failed: {e}")
            return None  # Autentizace selhala

        return None