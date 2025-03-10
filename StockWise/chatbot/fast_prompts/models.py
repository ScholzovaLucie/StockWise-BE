# -*- coding: UTF-8 -*-
from django.db import models

from django.conf import settings
from django.utils.translation import gettext_lazy as _


class FastPrompts(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name=_('User'), null=False, on_delete=models.CASCADE)
    client = models.ForeignKey('client.Client', verbose_name=_('Client'), related_name='%(class)s_client', blank=True, null=True, on_delete=models.CASCADE)
    prompts = models.ManyToManyField('Prompt', blank=True)

    def save(self, *args, **kwargs):
        super(FastPrompts, self).save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        super(FastPrompts, self).delete()
