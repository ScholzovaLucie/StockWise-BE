import openai
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status


class ChatbotView(APIView):

    def post(self, request):
        user_message = request.data.get("message", "")

        if not user_message:
            return Response({"error": "No message provided"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)  # Opravený způsob inicializace klienta
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",  # Levnější varianta
                messages=[{"role": "system", "content": "You are a helpful warehouse assistant."},
                          {"role": "user", "content": user_message}]
            )
            chatbot_reply = response.choices[0].message.content
            return Response({"response": chatbot_reply})

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)