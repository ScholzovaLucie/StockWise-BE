import json
import logging
import time
from base64 import b64encode

from django.conf import settings
from django.http import JsonResponse
from openai import OpenAI
from rest_framework.views import APIView
import tiktoken

from chatbot.assistantDataCreator import get_function
from chatbot.assistant_threads.models import ChatBotAssistantThread
from client.models import Client
from user.models import User


class ChatbotView(APIView):
    API_KEY = settings.OPENAI_API_KEY
    DEV_ASSISTANT_KEY = 'asst_b7UzE26Vd2tq2rDB5Pq8PhOO'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.response = []
        if not self.API_KEY:
            raise ValueError("OPENAI_API_KEY není nastaven v Django settings!")

        self.client = OpenAI(api_key=self.API_KEY)

    def post(self, request):
        try:
            self.client_id = int(request.data.get('client')) if request.data.get('client') and request.data.get('client') != '0' else None

            if not self.client_id:
                return JsonResponse(data={
                'element': 'p',
                'class': 'warning',
                'content': "Client is not fill"}
            , safe=False, status=404)

            self.set_thread_id(request.user.id, self.client_id)

            if request.POST.get('history'):
                messages = self.client.beta.threads.messages.list(
                    thread_id=self.thread.thread_id
                )
                self.message_parser(messages)

            if request.POST.get("prompt") or request.POST.get("input_chat"):
                prompt = request.POST.get("prompt") if request.POST.get("prompt") else request.POST.get("input_chat")
                self.chatbot(prompt, self.client_id)

            if request.POST.get("reset"):
                self.reset(request.user.id, self.client_id)

        except Exception as e:
            exception = str(e)
            self.response.append({
                'element': 'p',
                'class': 'warning',
                'content': exception
            })
            logging.error(exception)
            logging.getLogger('django').error(f'ChatBot error {exception}')
            print(exception)
            return JsonResponse(data=self.response, safe=False, status=500)

        return JsonResponse(data=self.response, safe=False, status=200)

    def chatbot(self, prompt, client_id):
        """
        :param prompt:
        :type prompt: str
        :param client_id:
        :type client_id: int
        """
        try:
            self.send_user_message(prompt)
            run = self.create_thread_run()
            self.monitor_run_status(run, client_id)
            self.process_run_completion()
        except Exception as e:
            self.custom_handle_exception(e, prompt)

    def send_user_message(self, prompt):
        try:
            self.client.beta.threads.messages.create(
                thread_id=self.thread.thread_id,
                role='user',
                content=prompt
            )
        except Exception as e:
            self.custom_handle_exception(e, prompt)

    def create_thread_run(self):
        run = self.client.beta.threads.runs.create(
            thread_id=self.thread.thread_id,
            assistant_id=self.DEV_ASSISTANT_KEY
        )
        return run

    def monitor_run_status(self, run, client_id):
        run_status = self.get_run_status(run)
        while run_status.status != 'completed':
            if run_status.status == 'requires_action':
                calls = run_status.required_action.submit_tool_outputs.tool_calls
                run = self.tool_calls(calls, client_id, run)
            time.sleep(1)
            run_status = self.get_run_status(run)

    def get_run_status(self, run):
        run_status = self.client.beta.threads.runs.retrieve(
            thread_id=self.thread.thread_id,
            run_id=run.id,
        )
        return run_status

    def process_run_completion(self):
        run_steps = self.client.beta.threads.messages.list(
            thread_id=self.thread.thread_id
        )
        self.message_parser(run_steps)

    def custom_handle_exception(self, exeption, prompt):
        exception = str(exeption)
        if "Can't add messages to " in exception:
            self.already_running_run(exception, prompt)
        else:
            exception = str(exeption.args[0])
            self.response.append({
                'element': 'p',
                'class': 'warning',
                'content': exception
            })
            logging.getLogger('django').error(f'ChatBot error {exception}')
            print(exception)

    def reset(self, user_id, client_id):
        self.response = []
        thread = ChatBotAssistantThread.objects.filter(user__id=user_id, client__id=client_id)
        if thread:
            thread = thread.first()
            thread.absolut_token_count += thread.token_count
            thread.token_count = 0
            thread.thread_id = self.client.beta.threads.create().id
            thread.save(update_fields=['thread_id', 'absolut_token_count', 'token_count'])

    def tool_calls(self, calls, client_id, run):
        results = []

        for call in calls:
            try:
                results.append(self.requires_action(call, client_id))

            except Exception as e:
                exception = str(e.args[0])
                self.response.append({
                    'element': 'p',
                    'class': 'warning',
                    'content': exception
                })
                logging.getLogger('django').error(f'ChatBot error {exception}')
                print(exception)
                results.append({
                    'tool_call_id': call.id,
                    'output': str(None)
                })

        run = self.client.beta.threads.runs.submit_tool_outputs(
            thread_id=self.thread.thread_id,
            run_id=run.id,
            tool_outputs=results
        )

        return run

    def message_parser(self, run_steps):
        data = run_steps.data
        encoding = tiktoken.get_encoding("cl100k_base")
        encoding = tiktoken.encoding_for_model(settings.OPENAI_MODEL)
        tokens_count = 0

        if settings.OPENAI_MODEL == "gpt-3.5-turbo-0301":
            tokens_per_message = 4
            tokens_per_name = -1
        else:
            tokens_per_message = 3
            tokens_per_name = 1

        for message in data:
            role = message.role
            content = message.content[0]

            if content.type == 'image_file':
                file_id = content.image_file.file_id
                api_response = self.client.files.with_raw_response.retrieve_content(file_id)
                if api_response.status_code == 200:
                    img = api_response.content
                    encoded = b64encode(img)
                    uri = f'data:image/jpeg;base64,{encoded.decode("utf-8")}'
                    self.response.append({
                        'element': 'img',
                        'src': uri,
                        'class': role,
                        'alt': file_id,
                    })

            else:
                tokens_count += tokens_per_message
                tokens_count += len(encoding.encode(content.text.value))
                tokens_count += tokens_per_name
                text = content.text.value
                self.response.append({
                    'element': 'div',
                    'class': ['response_text', role],
                    'content': text
                })

        self.thread.token_count = tokens_count
        self.thread.save()

    def set_thread_id(self, user_id, client_id):
        thread = ChatBotAssistantThread.objects.filter(user__id=user_id, client__id=client_id).first()
        if thread is not None:
            self.thread = thread
        else:
            thread = self.client.beta.threads.create()
            user = User.objects.filter(id=user_id).first()
            client = Client.objects.filter(id=client_id).first()
            thread = ChatBotAssistantThread.objects.create(
                user=user,
                thread_id=thread.thread_id,
                client=client
            )
            self.thread = thread.thread

    def already_running_run(self, exception, prompt):
        run_id = exception.split('run ')[1].split(' is')[0]
        self.client.beta.threads.runs.cancel(
            run_id=run_id,
            thread_id=self.thread.thread_id
        )
        self.client.beta.threads.messages.create(
            thread_id=self.thread.thread_id,
            role='user',
            content=prompt
        )

    @staticmethod
    def requires_action(call, client_id):
        call_id = call.id

        function_name = call.function.name
        parameters = json.loads(call.function.arguments)
        function, model, serializer = get_function(function_name)
        result = function(
            call_id,
            parameters,
            client_id,
            model,
            serializer
        )

        return result
