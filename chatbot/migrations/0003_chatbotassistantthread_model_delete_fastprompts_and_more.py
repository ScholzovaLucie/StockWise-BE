# Generated by Django 4.2.20 on 2025-04-15 17:50

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('chatbot', '0002_chatbotassistantthread_stat_id'),
    ]

    operations = [
        migrations.DeleteModel(
            name='FastPrompts',
        ),
        migrations.DeleteModel(
            name='Prompt',
        ),
    ]
