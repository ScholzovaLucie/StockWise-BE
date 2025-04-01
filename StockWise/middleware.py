from django.contrib.auth import get_user_model
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.exceptions import AuthenticationFailed
import logging

logger = logging.getLogger(__name__)

User = get_user_model()

class CookieJWTAuthentication(JWTAuthentication):
    def authenticate(self, request):
        access_token = request.COOKIES.get('access_token')

        # Pokud není token v cookies, zkus ho získat z Authorization hlavičky
        if not access_token:
            auth_header = request.META.get('HTTP_AUTHORIZATION')
            if auth_header and auth_header.startswith('Bearer '):
                access_token = auth_header.split(' ')[1]  # Odstranění prefixu "Bearer"

        if not access_token:
            return None  # Žádný token, žádná autentizace

        try:
            validated_token = self.get_validated_token(access_token)
            user = self.get_user(validated_token)
            return (user, validated_token)
        except AuthenticationFailed as e:
            logger.warning(f"Authentication failed: {e}")
            return None  # Token je neplatný, autentizace selhala

        return None