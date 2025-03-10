from django.http import JsonResponse
from rest_framework.views import APIView

from chatbot.fast_prompts.models import FastPrompts
from chatbot.prompt.models import Prompt
from client.models import Client
from user.models import User


def create_fast_prompts_with_default_values(user_id, client_id):
    user = User.objects.filter(id=user_id).first()
    client = Client.objects.filter(id=client_id).first()

    default_prompts = Prompt.objects.filter(default=True)

    fast_prompts = FastPrompts.objects.create(
        user=user,
        client=client,
    )
    fast_prompts.prompts.add(*default_prompts)
    fast_prompts.save()

    return fast_prompts


def get_fast_prompts(user_id, client_id):
    user = User.objects.filter(id=user_id).first()
    client = Client.objects.filter(id=client_id).first()

    return FastPrompts.objects.filter(user=user, client=client).first().prompts


class FastPromptsAPI(APIView):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def post(self, request, *args, **kwargs):
        prompts = []
        client_id = int(request.POST.get('client')) if request.POST.get('client') != '0' else None
        user_id = request.user.id

        user = User.objects.filter(id=user_id).first()
        client = Client.objects.filter(id=client_id).first()

        fast_prompts = FastPrompts.objects.filter(user=user, client=client)
        if fast_prompts:
            if fast_prompts.first().prompts.all().count() > 0:
                for prompt in fast_prompts.first().prompts.all():
                    prompts.append(prompt.text)
            else:
                default_prompts = FastPrompts.objects.filter(default=True)
                fast_prompts.prompts.add(*default_prompts)
                fast_prompts.save()

        else:
            fast_prompts = create_fast_prompts_with_default_values(
                user_id,
                client_id,
            )
            for prompt in fast_prompts.prompts.all():
                prompts.append(prompt.text)

        return JsonResponse(data={'content': prompts}, safe=False, status=200)
