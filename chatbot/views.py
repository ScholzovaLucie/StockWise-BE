import json
import logging
import time
from base64 import b64encode

import pandas as pd
from django.conf import settings
from django.core.cache import cache
from django.http import JsonResponse
from openai import AzureOpenAI, OpenAI
from rest_framework.parsers import MultiPartParser, JSONParser
from rest_framework.views import APIView

from chatbot.assistant_threads.models import ChatBotAssistantThread, OPEANAI_MODEL
from chatbot.assistantDataCreator import get_function
from client.models import Client

logger = logging.getLogger(__name__)

API_KEY = settings.OPENAI_API_KEY
AZURE_API_KEY = settings.AZURE_OPENAI_API_KEY


class OpenAIHandler:
    def __init__(self):
        if settings.USE_AZURE:
            self.client = AzureOpenAI(
                api_key=settings.AZURE_OPENAI_API_KEY,
                api_version=settings.AZURE_OPENAI_API_VERSION,
                azure_endpoint=settings.AZURE_OPENAI_ENDPOINT
            )
            self.model = OPEANAI_MODEL[0]  # model pro Azure
        else:
            self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
            self.model = OPEANAI_MODEL[1]  # model pro OpenAI

    def get_or_create_thread(self, user, client, stat_id=None):
        filters = {"user": user, "client": client, "model": self.model}
        if stat_id:
            filters["stat_id"] = stat_id

        thread = ChatBotAssistantThread.objects.filter(**filters).first()

        if not thread:
            thread_obj = self.client.beta.threads.create()
            thread = ChatBotAssistantThread.objects.create(
                user=user,
                client=client,
                stat_id=stat_id,
                thread_id=thread_obj.id,
                model=self.model
            )
        return thread

    def reset_thread(self, client, user, stat=None):
        stock_thread = ChatBotAssistantThread.objects.filter(
            user=user,
            client=client,
            stat_id=stat,
            model=self.model
        ).order_by("-token_count").first()

        if stock_thread:
            stock_thread.token_count = 0
            stock_thread.thread_id = self.client.beta.threads.create().id
            stock_thread.save(update_fields=['thread_id', 'token_count'])

    def cancel_active_runs(self, thread_id, timeout=10):
        runs = self.client.beta.threads.runs.list(thread_id=thread_id).data
        active = [r for r in runs if r.status in ["queued", "in_progress", "requires_action"]]

        for run in active:
            logger.info(f"Ruším run {run.id} se statusem {run.status}")
            try:
                self.client.beta.threads.runs.cancel(thread_id=thread_id, run_id=run.id)
            except Exception as e:
                if "Cannot cancel run" not in str(e):
                    raise

            for i in range(timeout * 2):
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

    def create_run(self, assistant_id, thread_id):
        return self.client.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=assistant_id
        )

    def wait_for_completion(self, thread_id, run_id, client_id, user, timeout=90):
        for i in range(timeout):
            status = self.client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run_id)

            if status.status == "completed":
                return True
            elif status.status == "failed":
                raise Exception(status.last_error.message)
            elif status.status == "requires_action":
                calls = status.required_action.submit_tool_outputs.tool_calls
                self._handle_tool_calls(calls, client_id, run_id, user, thread_id)

            # Exponential backoff pro méně časté dotazy
            sleep_time = 1 if i < 10 else min(5, (i // 10))
            time.sleep(sleep_time)
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
        if not messages.data:
            raise Exception("Vlákno neobsahuje žádné odpovědi.")

        latest = messages.data[0]
        if not latest.content:
            raise Exception("Poslední zpráva neobsahuje žádný obsah.")

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

    def get_thread_messages(self, user, client, model):
        thread = ChatBotAssistantThread.objects.filter(
            user=user,
            client=client,
            stat_id__isnull=True,
            model=model
        ).order_by("-token_count").first()

        if not thread:
            thread = ChatBotAssistantThread.objects.create(
                user=user,
                client=client,
                stat_id=None,
                model=model
            )
        return self.client.beta.threads.messages.list(thread_id=thread.thread_id)

    def run_prompt(self, user, client, prompt, assistant_id, stat_id=None):
        lock_key = f"stat_lock_{user.id}_{client.id}_{stat_id}"
        if cache.get(lock_key):
            raise Exception("Statistika již běží, zkus to za chvíli.")

        cache.set(lock_key, True, timeout=90)  # lock na 90 sekund

        try:
            thread = self.get_or_create_thread(user, client, stat_id)
            self.cancel_active_runs(thread.thread_id)
            self.send_prompt(thread.thread_id, prompt)
            run = self.create_run(assistant_id, thread.thread_id)
            self.wait_for_completion(thread.thread_id, run.id, client.id, user)
            return self.get_response(thread.thread_id)
        finally:
            cache.delete(lock_key)


class StatisticsView(APIView):
    STAT_PROMPTS = {
        "stockSummary": (
            "Vygeneruj aktuální přehled stavu zásob na skladě. "
            "Rozděl zásoby podle produktů a jejich šarží. "
            "U každého záznamu uveď název produktu, označení šarže, aktuální množství a jednotku. "
            "Zobraz výstup **pouze jako tabulku**. Nepoužívej grafy."
        ),

        "expiringSoon": (
            "Zobraz produkty, kterým končí expirace během následujících 30 dnů. "
            "Uveď název produktu, šarži a datum expirace. "
            "Zobraz **pouze tabulku**. Nepoužívej žádný text ani graf."
        ),

        "operationStats": (
            "Zobraz počet příjmů a výdejů za poslední 3 měsíce. "
            "Rozděl data po týdnech a vykresli **čárový graf se dvěma liniemi** – příjem a výdej. "
            "Osa X: týdny, osa Y: počet operací. Bez dalších textů."
        ),

        "userEfficiency": (
            "Vyhodnoť efektivitu uživatelů za posledních 30 dní podle počtu provedených operací. "
            "Zobraz **sloupcový graf**, kde každý sloupec reprezentuje jednoho uživatele. "
            "Bez popisků nebo shrnutí."
        ),

        "activityTimeline": (
            "Zobraz změny ve skladu za posledních 7 dní – nové operace, úpravy zásob, přesuny a smazání. "
            "Seřaď změny chronologicky a rozděl podle typu. "
            "Výstup zobraz **pouze jako tabulku** nebo seznam. Nepoužívej grafy ani textová shrnutí."
        ),

        "lowStock": (
            "Identifikuj produkty, jejichž množství kleslo pod minimální limit. "
            "Uveď název produktu, aktuální množství, minimální limit a jednotku. "
            "Zobraz výstup **striktně jako tabulku**. Nepřidávej žádné poznámky."
        ),

        "topProducts": (
            "Zobraz produkty s nejvyšším počtem výdejů za posledních 30 dní. "
            "Seřaď sestupně podle počtu výdejů. "
            "Výstup zobraz **pouze jako sloupcový graf**. Nepřidávej text."
        ),

        "monthlyOverview": (
            "Zobraz přehled klíčových údajů za poslední měsíc: počet nových produktů, operací, expirací a přesunů. "
            "Vrať výstup **výhradně jako tabulku se souhrnnými číselnými údaji**. "
            "Nepoužívej grafy ani žádné textové komentáře."
        ),

        "demandForecast": (
            "Na základě historické spotřeby odhadni očekávanou spotřebu jednotlivých produktů na příští měsíc. "
            "Zobraz jako **čárový graf** – každý produkt samostatně, pokud je to proveditelné. "
            "Pokud je produktů příliš, zobraz jen top 10 podle spotřeby."
        ),

        "expiringForecast": (
            "Odhadni počet jednotek, které pravděpodobně expirují během následujícího měsíce. "
            "Rozděl po týdnech a zobraz **výhradně jako sloupcový graf**. "
            "X-osa = týdny, Y-osa = počet expirací. Bez doprovodného textu."
        ),

        "staffUtilization": (
            "Zhodnoť využití pracovníků na základě počtu provedených operací za posledních 30 dní. "
            "Odhadni procentuální vytížení jednotlivých pracovníků. "
            "Zobraz jako **kruhový nebo sloupcový graf** bez jakéhokoliv textového shrnutí."
        ),

        "warehouseHeatmap": (
            "Vytvoř vizuální heatmapu skladu podle zaplněnosti skladových pozic. "
            "Zobraz **výhradně jako graf heatmap**, kde intenzita barvy odpovídá zaplnění. "
            "Nepoužívej žádný doplňující text, kromě popisku, který blok je která pozice (název pozice)."
        ),

        "productMovement": (
            "Zobraz tok produktů za poslední 2 týdny – kolik bylo přijato a kolik vydáno. "
            "Zobraz jako **čárový nebo sloupcový graf se dvěma sériemi**: příjem a výdej. "
            "Bez jakýchkoli komentářů nebo shrnutí."
        )
    }
    ASSISTANT_KEY = 'asst_aa2kW75H12y8OKAg3jcvcYmk'

    def post(self, request):
        user = request.user
        client_id = request.data.get("client")
        stat_id = request.data.get("stat_id")

        if not client_id or not stat_id:
            return JsonResponse({"error": "Chybí client nebo stat_id."}, status=400)

        prompt = self.STAT_PROMPTS.get(stat_id)
        if not prompt:
            return JsonResponse({"error": "Neznámé stat_id."}, status=400)

        try:
            client = get_client_or_404(client_id)
        except ValueError as e:
            return JsonResponse({"error": str(e)}, status=404)

        cache_key = f"stat_cache_{user.id}_{client.id}_{stat_id}"
        cached_response = cache.get(cache_key)
        if cached_response:
            return JsonResponse(cached_response)

        try:
            handler = OpenAIHandler()
            response = handler.run_prompt(user=user, client=client, prompt=prompt, stat_id=stat_id, assistant_id=self.ASSISTANT_KEY)
            cache.set(cache_key, response, timeout=60 * 5)  # cache na 5 minut
            return JsonResponse(response)
        except Exception as e:
            logging.exception("Chyba ve statistice")
            return JsonResponse({"error": str(e)}, status=500)

class ChatbotView(APIView):
    parser_classes = [MultiPartParser, JSONParser]
    ASSISTANT_KEY = 'asst_ym2hrOmYeS2LfXOkP53HdCEn'

    def post(self, request):
        try:
            user = request.user
            client_id = request.data.get("client")
            prompt = request.data.get("input_chat") or request.data.get("prompt")
            file = request.FILES.get("file")

            if not client_id:
                return JsonResponse({"error": "Client ID není vyplněn."}, status=400)

            try:
                client = get_client_or_404(client_id)
            except ValueError as e:
                return JsonResponse({"error": str(e)}, status=404)

            handler = OpenAIHandler()

            # Reset konverzace
            if request.data.get("reset"):
                handler.reset_thread(client, user)
                return JsonResponse({"message": "Vlákno bylo resetováno."})

            # Získání historie zpráv
            if request.data.get("history"):
                raw_messages = handler.get_thread_messages(user, client, handler.model)
                messages = []

                for msg in raw_messages.data:
                    role = msg.role
                    content_item = msg.content[0]
                    content = (
                        content_item.text.value if content_item.type == "text"
                        else "Obrázek nebo jiný obsah"
                    )
                    messages.append({
                        "role": role,
                        "content": content,
                        "created_at": msg.created_at
                    })

                return JsonResponse(list(reversed(messages)), safe=False)

            # Nahraný soubor – převedeme na JSON
            if file:
                try:
                    if file.name.endswith(".csv"):
                        df = pd.read_csv(file)
                    else:
                        df = pd.read_excel(file)
                    file_json = df.to_json(orient="records")
                    prompt = f"Nahraný soubor obsahuje následující data: {file_json}"
                except Exception as e:
                    return JsonResponse({"error": f"Chyba při zpracování souboru: {str(e)}"}, status=400)

            # Zaslání promptu
            if not prompt:
                return JsonResponse({"error": "Chybí vstupní prompt."}, status=400)

            response = handler.run_prompt(
                user=user,
                client=client,
                prompt=prompt,
                assistant_id=self.ASSISTANT_KEY
            )
            return JsonResponse(response)

        except Exception as e:
            logging.getLogger("django").error(f"Chyba v ChatbotView: {str(e)}")
            return JsonResponse({"error": str(e)}, status=500)

def get_client_or_404(client_id):
    client = Client.objects.filter(id=client_id).first()
    if not client:
        raise ValueError("Klient neexistuje.")
    return client