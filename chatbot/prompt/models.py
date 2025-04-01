# -*- coding: UTF-8 -*-
from django.db import models


class Prompt(models.Model):
    text = models.CharField(max_length=250, blank=False, null=False)
    default = models.BooleanField(default=False, blank=False, null=False)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        super(Prompt, self).save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        super(Prompt, self).delete()
