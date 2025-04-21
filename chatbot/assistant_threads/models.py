# -*- coding: UTF-8 -*-
from django.db import models

from django.conf import settings
from django.utils.translation import gettext_lazy as _


OPEANAI_MODEL = (
    ('azure', 'Azure'),
    ('opeanai', 'Opeanai'),
)


class ChatBotAssistantThread(models.Model):
    thread_id = models.CharField(_('Thread ID'), max_length=250, unique=True, null=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name=_('User'), null=False, on_delete=models.CASCADE)
    client = models.ForeignKey('client.Client', verbose_name=_('Client'), related_name='client', blank=True, null=True, on_delete=models.CASCADE)
    token_count = models.IntegerField(_('Token Count'), default=0)
    absolut_token_count = models.IntegerField(_('Absolute Token'), default=0)
    stat_id = models.CharField(max_length=50, null=True, blank=True)
    model = models.CharField(max_length=50, null=True, blank=True, choices=OPEANAI_MODEL, default='opeanai')

    def __str__(self):
        return "%s" % (self.thread_id)

    def save(self, *args, **kwargs):
        super(ChatBotAssistantThread, self).save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        super(ChatBotAssistantThread, self).delete()