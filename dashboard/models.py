from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class UserDashboardConfig(models.Model):
    DASHBOARD_TYPES = [
        ("main", "Hlavní dashboard"),
        ("stats", "Statistiky"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="dashboard_configs")
    type = models.CharField(max_length=50, choices=DASHBOARD_TYPES, default="main")
    config = models.JSONField(default=dict)

    class Meta:
        unique_together = ("user", "type")

    def set_widgets(self, widgets):
        """Uloží nové nastavení widgetů."""
        self.config = widgets
        self.save()

    def get_widgets(self):
        """Vrátí uložené widgety uživatele."""
        return self.config or {}