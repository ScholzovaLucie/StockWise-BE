import jwt
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils.deprecation import MiddlewareMixin

User = get_user_model()

class JWTAuthenticationMiddleware(MiddlewareMixin):
    def process_request(self, request):
        token = request.headers.get("Authorization", None)
        if token and token.startswith("Bearer "):
            try:
                payload = jwt.decode(token.split(" ")[1], settings.SECRET_KEY, algorithms=["HS256"])
                request.user = User.objects.get(id=payload["user_id"])
            except (jwt.ExpiredSignatureError, jwt.DecodeError, User.DoesNotExist):
                request.user = None