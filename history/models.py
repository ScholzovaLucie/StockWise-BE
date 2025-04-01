from django.db import models
from django.utils.timezone import now

from django.db import models
from django.utils.timezone import now

class History(models.Model):
    TYPE_CHOICES = [
        ("operation", "Operace"),
        ("product", "Produkt"),
        ("batch", "Šarže"),
        ("group", "Skupina"),
        ("position", "Pozice"),
    ]

    type = models.CharField(max_length=20, choices=TYPE_CHOICES)  # 📂 Kategorie změny
    related_id = models.PositiveIntegerField()  # 🔗 ID objektu, na který se vztahuje
    description = models.TextField()  # 📝 Popis změny
    timestamp = models.DateTimeField(default=now)  # 🕒 Čas změny
    user = models.ForeignKey("user.User", on_delete=models.SET_NULL, null=True, blank=True)  # 👤 Kdo změnu provedl

    # ✅ Indexy pro rychlejší dotazy
    class Meta:
        indexes = [
            models.Index(fields=["type"]),
            models.Index(fields=["timestamp"]),
        ]
        ordering = ["-timestamp"]  # Nejnovější záznamy první

    def __str__(self):
        return f"{self.type}: {self.description} ({self.timestamp})"