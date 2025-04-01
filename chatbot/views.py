import json
import logging
import time
from base64 import b64encode

import pandas as pd
from django.conf import settings
from django.http import JsonResponse
from openai import OpenAI
from rest_framework.parsers import MultiPartParser, JSONParser
from rest_framework.views import APIView

from chatbot.assistant_threads.models import ChatBotAssistantThread
from chatbot.assistantDataCreator import get_function
from client.models import Client


DEV_ASSISTANT_KEY = 'asst_ym2hrOmYeS2LfXOkP53HdCEn'
API_KEY = settings.OPENAI_API_KEY


class OpenAIHandler:
    def __init__(self):
        self.client = OpenAI(api_key=API_KEY)

    def get_or_create_thread(self, user, client, stat_id=None):
        filters = {"user": user, "client": client}
        if stat_id:
            filters["stat_id"] = stat_id

        thread = ChatBotAssistantThread.objects.filter(**filters).first()

        if not thread:
            thread_obj = self.client.beta.threads.create()
            thread = ChatBotAssistantThread.objects.create(
                user=user,
                client=client,
                stat_id=stat_id,
                thread_id=thread_obj.id
            )
        return thread

    def reset_thread(self, thread):
        thread.absolut_token_count += thread.token_count
        thread.token_count = 0
        thread.thread_id = self.client.beta.threads.create().id
        thread.save(update_fields=['thread_id', 'absolut_token_count', 'token_count'])

    def cancel_active_runs(self, thread_id, timeout=10):
        runs = self.client.beta.threads.runs.list(thread_id=thread_id).data
        active = [r for r in runs if r.status in ["queued", "in_progress", "requires_action"]]

        for run in active:
            try:
                self.client.beta.threads.runs.cancel(thread_id=thread_id, run_id=run.id)
            except Exception as e:
                if "Cannot cancel run" not in str(e):
                    raise

            for _ in range(timeout * 2):
                status = self.client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run.id).status
                if status in ["cancelled", "completed", "failed"]:
                    break
                time.sleep(0.5)

            final_status = self.client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run.id).status
            if final_status not in ["cancelled", "completed", "failed"]:
                raise Exception(f"Nelze pokračovat – run {run.id} má stále status: {final_status}")

    def send_prompt(self, thread_id, prompt):
        self.client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=prompt
        )

    def create_run(self, thread_id):
        return self.client.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=DEV_ASSISTANT_KEY
        )

    def wait_for_completion(self, thread_id, run_id, client_id, user, timeout=90):
        for _ in range(timeout):
            status = self.client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run_id)
            if status.status == "completed":
                return True
            elif status.status == "failed":
                raise Exception(status.last_error.message)
            elif status.status == "requires_action":
                calls = status.required_action.submit_tool_outputs.tool_calls
                self._handle_tool_calls(calls, client_id, run_id, user, thread_id)
            time.sleep(1)
        raise Exception("Timeout při čekání na dokončení runu.")

    def _handle_tool_calls(self, calls, client_id, run, user, thread_id):
        results = []
        for call in calls:
            try:
                function_name = call.function.name
                parameters = json.loads(call.function.arguments)
                function, model, serializer = get_function(function_name)
                result = function(call.id, parameters, client_id, model, serializer, user)
                results.append(result)
            except Exception as e:
                results.append({"tool_call_id": call.id, "output": str(e)})

        self.client.beta.threads.runs.submit_tool_outputs(
            thread_id=thread_id,
            run_id=run,
            tool_outputs=results
        )

    def get_response(self, thread_id):
        messages = self.client.beta.threads.messages.list(thread_id=thread_id)
        latest = messages.data[0]
        content = latest.content[0]

        if content.type == "image_file":
            file_id = content.image_file.file_id
            image_response = self.client.files.with_raw_response.retrieve_content(file_id)
            encoded = b64encode(image_response.content)
            return {
                "element": "img",
                "src": f"data:image/jpeg;base64,{encoded.decode()}",
                "alt": file_id
            }

        return {
            "element": "div",
            "content": content.text.value,
            "class": "assistant"
        }

    def get_thread_messages(self, user, client):
        try:
            thread, created = ChatBotAssistantThread.objects.get_or_create(user=user, client=client)
            return self.client.beta.threads.messages.list(thread_id=thread.thread_id)
        except Exception as e:
            raise Exception(e)

    def run_prompt(self, user, client, prompt, stat_id=None):
        thread = self.get_or_create_thread(user, client, stat_id)
        self.reset_thread(thread)
        self.cancel_active_runs(thread.thread_id)
        self.send_prompt(thread.thread_id, prompt)
        run = self.create_run(thread.thread_id)
        self.wait_for_completion(thread.thread_id, run.id, client.id, user)
        return self.get_response(thread.thread_id)



class StatisticsView(APIView):
    STAT_PROMPTS = {
        "stockSummary": (
            "Vygeneruj přehled aktuálního stavu zásob na skladě. "
            "Rozděl zásoby podle produktů a jejich šarží. "
            "U každého záznamu uveď název produktu, označení šarže, aktuální množství a jednotku. "
            "Výstup zobraz jako přehlednou tabulku. "
            "Nepoužívej grafy – při větším počtu položek nejsou efektivní."
        ),

        "expiringSoon": (
            "Zjisti, které produkty mají expirační datum do 30 dnů od dnešního dne. "
            "Uveď název produktu, šarži a datum expirace v přehledné tabulce. "
            "Nepoužívej graf – výstup má být přesný a přehledný."
        ),

        "operationStats": (
            "Spočítej počet příjmů a výdejů zboží za poslední 3 měsíce. "
            "Rozděl vývoj po týdnech a zobraz jako čárový graf se dvěma liniemi – příjem a výdej. "
            "X-osa = týdny, Y-osa = počet operací."
        ),

        "userEfficiency": (
            "Vyhodnoť efektivitu uživatelů za posledních 30 dní podle počtu provedených operací (příjem a výdej). "
            "Zobraz jako sloupcový graf, kde každý sloupec představuje jednoho uživatele."
        ),

        "activityTimeline": (
            "Shrň veškeré změny na skladě za posledních 7 dní – nové operace, úpravy zásob, přesuny a smazání. "
            "Rozděl změny podle typu a seřaď je chronologicky. "
            "Výstup zobraz jako seznam nebo tabulku. Nepoužívej grafy."
        ),

        "lowStock": (
            "Identifikuj produkty, jejichž množství kleslo pod minimální limit. "
            "U každého produktu uveď název, aktuální množství, minimální limit a jednotku. "
            "Zobraz jako tabulku – grafy nejsou vhodné."
        ),

        "topProducts": (
            "Zjisti, které produkty byly nejčastěji vydávány za posledních 30 dní. "
            "Seřaď je sestupně podle počtu výdejů a zobraz jako sloupcový graf."
        ),

        "monthlyOverview": (
            "Shrň klíčové události ve skladu za poslední měsíc: počet nových produktů, provedených operací, expirací a přesunů. "
            "Přidej stručné číselné souhrny a seznam důležitých událostí. "
            "Nepoužívej grafy – výstup má být textový a přehledný."
        ),

        "demandForecast": (
            "Na základě historické spotřeby predikuj odhadované množství jednotek jednotlivých produktů pro příští měsíc. "
            "Zobraz jako čárový graf – pro každý produkt zvlášť, pokud to rozsah dovolí. "
            "V opačném případě zobraz pouze top produkty dle spotřeby."
        ),

        "expiringForecast": (
            "Předpověz množství jednotek, které pravděpodobně expirují během příštího měsíce. "
            "Rozděl predikci po týdnech a zobraz jako sloupcový graf – osa X: týdny, osa Y: počet expirací."
        ),

        "staffUtilization": (
            "Zhodnoť využití zaměstnanců za posledních 30 dní. "
            "Na základě provedených operací odhadni procentuální využití pracovní doby každého zaměstnance. "
            "Zobraz jako kruhový graf nebo bar chart."
        ),

        "warehouseHeatmap": (
            "Vytvoř vizuální heatmapu skladu podle zaplněnosti skladových pozic. "
            "Zobraz graficky pomocí mřížky, kde intenzita barvy odpovídá míře zaplnění – čím plnější pozice, tím sytější barva."
        ),

        "productMovement": (
            "Zobraz tok produktů za poslední 2 týdny – kolik bylo přijato a kolik vydáno. "
            "Zobraz jako čárový nebo sloupcový graf se dvěma sériemi: příjem a výdej."
        )
    }

    def post(self, request):
        user = request.user
        client_id = request.data.get("client")
        stat_id = request.data.get("stat_id")

        if not client_id or not stat_id:
            return JsonResponse({"error": "Chybí client nebo stat_id."}, status=400)

        prompt = self.STAT_PROMPTS.get(stat_id)
        if not prompt:
            return JsonResponse({"error": "Neznamy stat_id."}, status=400)

        try:
            client = Client.objects.filter(id=client_id).first()
            if not client:
                return JsonResponse({"error": "Klient neexistuje."}, status=404)
        except Exception as e:
            return JsonResponse({"error": "Klient neexistuje nebo nebyl nalezen."}, status=500)

        try:
            handler = OpenAIHandler()
            response = handler.run_prompt(user=user, client=client, prompt=prompt, stat_id=stat_id)
            return JsonResponse(response)
        except Exception as e:
            logging.exception("Chyba ve statistice")
            return JsonResponse({"error": str(e)}, status=500)


class ChatbotView(APIView):
    parser_classes = [MultiPartParser, JSONParser]

    def post(self, request):
        try:
            user = request.user
            client_id = request.data.get("client")
            prompt = request.data.get("input_chat") or request.data.get("prompt")
            file = request.FILES.get("file")

            if not client_id:
                return JsonResponse({"error": "Client ID není vyplněn."}, status=400)

            client = Client.objects.filter(id=client_id).first()
            if not client:
                return JsonResponse({"error": "Klient neexistuje."}, status=404)

            handler = OpenAIHandler()

            if request.data.get("reset"):
                handler.reset_thread(user, client)
                return JsonResponse({"message": "Vlákno bylo resetováno."})

            if request.data.get("history"):
                raw_messages = handler.get_thread_messages(user, client)
                messages = []

                for msg in raw_messages.data:
                    messages.append({
                        "role": msg.role,
                        "content": msg.content[0].text.value if msg.content[
                                                                    0].type == "text" else "Obrázek nebo jiný obsah",
                        "created_at": msg.created_at
                    })

                return JsonResponse(messages, safe=False)

            if file:
                df = pd.read_csv(file) if file.name.endswith(".csv") else pd.read_excel(file)
                file_json = df.to_json(orient="records")
                prompt = f"Nahraný soubor obsahuje následující data: {file_json}"

            response = handler.run_prompt(user=user, client=client, prompt=prompt)
            return JsonResponse(response)

        except Exception as e:
            logging.getLogger("django").error(f"Chyba v ChatbotView: {str(e)}")
            return JsonResponse({"error": str(e)}, status=500)

