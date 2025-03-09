from django.db import models
from django.contrib.auth import get_user_model
import json

class UserDashboardConfig(models.Model):
    user = models.OneToOneField('user.User', on_delete=models.CASCADE)
    config = models.JSONField(default=dict)  

    def set_widgets(self, widgets):
        """Uloží nové nastavení widgetů."""
        self.config = json.dumps(widgets)
        self.save()

    def get_widgets(self):
        """Vrátí seznam uložených widgetů uživatele."""
        return json.loads(self.config) if self.config else []