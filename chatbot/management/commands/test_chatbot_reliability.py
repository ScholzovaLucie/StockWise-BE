import re
import csv

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

from chatbot.views import OpenAIHandler, ChatbotView
from client.models import Client
from position.models import Position
from product.models import Product

RUNS = 100
ASSISTANT_KEY = ChatbotView.ASSISTANT_KEY


class Command(BaseCommand):
    help = "Otestuje spolehlivost chatbotu podle daného typu testu (pozice/produkt)"

    def add_arguments(self, parser):
        parser.add_argument(
            "test_type",
            choices=["pozice", "produkt"],
            help="Typ testu: 'pozice' nebo 'produkt'"
        )

    def handle(self, *args, **options):
        test_type = options["test_type"]
        handler = OpenAIHandler()
        user = get_user_model().objects.first()
        client = Client.objects.first()

        if test_type == "pozice":
            prompt = "Jaká je neobsazenější pozice a kolik je na ní krabic. Odpověz jednou větou."
            target, expected = self.get_position_data()
            self.stdout.write(f"❗ Nejvíc krabic je na pozici: {target} ({expected} ks)")
            match_func = lambda answer: (
                str(expected) in answer and
                bool(re.search(re.escape(target), answer, re.IGNORECASE))
            )
        else:  # produkt
            prompt = "Vypiš seznam produktů pro klienta id 1. Vypiš name produktu? Odpověz jako seznam názvů oddělený čárkami."
            expected_set = set(Product.objects.filter(client=client).values_list("name", flat=True))
            self.stdout.write(f"📦 Reálné produkty klienta: {', '.join(expected_set)}")
            match_func = lambda answer: set(map(str.lower, map(str.strip, answer.split(",")))) == set(p.lower() for p in expected_set)

        csv_path = f"chatbot_results_{test_type}.csv"
        self.run_test(handler, user, client, prompt, match_func, csv_path)

    def run_test(self, handler, user, client, prompt, match_func, csv_path):
        with open(csv_path, "w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=["run", "actual", "is_correct"])
            writer.writeheader()

            for i in range(RUNS):
                self.stdout.write(f"Run {i + 1}/{RUNS}...")
                try:
                    response = handler.run_prompt(
                        user=user,
                        client=client,
                        prompt=prompt,
                        assistant_id=ASSISTANT_KEY
                    )
                    answer = response.get("content", "").strip()
                    correct = match_func(answer)
                    writer.writerow({
                        "run": i + 1,
                        "actual": answer,
                        "is_correct": correct
                    })

                except Exception as e:
                    self.stderr.write(f"❌ Chyba při runu {i + 1}: {str(e)}")

        self.stdout.write(f"✅ Testování dokončeno. Výsledky uloženy do: {csv_path}")

    def get_position_data(self):
        positions = Position.objects.prefetch_related("boxes").filter(boxes__isnull=False)
        if not positions.exists():
            raise ValueError("Žádné pozice s krabicemi ve skladu neexistují.")
        best = max(positions, key=lambda p: p.boxes.count())
        return best.code, best.boxes.count()