import csv
from django.core.management.base import BaseCommand
from product.models import Product

class Command(BaseCommand):
    help = "Zkontroluje, zda odpověď obsahuje kompletní seznam produktů pro klienta"

    def add_arguments(self, parser):
        parser.add_argument("input_csv", type=str, help="Cesta ke vstupnímu CSV souboru")
        parser.add_argument("output_csv", type=str, help="Cesta k výstupnímu CSV souboru")

    def handle(self, *args, **options):
        input_path = options["input_csv"]
        output_path = options["output_csv"]

        produkty_db = set(Product.objects.filter(client_id=1).values_list("name", flat=True))

        with open(input_path, newline='', encoding='utf-8') as infile, \
             open(output_path, 'w', newline='', encoding='utf-8') as outfile:

            reader = csv.DictReader(infile, delimiter=';')
            fieldnames = reader.fieldnames + ["vsechny_produkty_existuji", "pocet" ,"chybejici", "pocet_actual", "missing_count"]
            writer = csv.DictWriter(outfile, fieldnames=fieldnames, delimiter=';')
            writer.writeheader()

            for row in reader:
                odpoved = row["actual"]
                row["vsechny_produkty_existuji"] = "NEZNÁMO"
                row["chybejici"] = ""
                produkty_text = odpoved

                if "Seznam produktů pro klienta ID 1:" in odpoved:
                    produkty_text = odpoved.split("Seznam produktů pro klienta ID 1:")[1]

                produkty_v_odpovedi = [p.strip() for p in produkty_text.split(",") if p.strip()]
                chybejici = [p for p in produkty_db if p not in produkty_v_odpovedi]

                row["vsechny_produkty_existuji"] = "PRAVDA" if not chybejici else "NEPRAVDA"
                row["chybejici"] = ", ".join(chybejici)
                row['pocet'] = len(produkty_v_odpovedi)
                row["pocet_actual"] = len(produkty_db)
                row["missing_count"] = len(chybejici)


                writer.writerow(row)

        self.stdout.write(self.style.SUCCESS(f"Výstupní CSV bylo uloženo do: {output_path}"))