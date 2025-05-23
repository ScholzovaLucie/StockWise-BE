# Generated by Django 4.2.17 on 2025-01-09 15:56

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('group', '0001_initial'),
        ('user', '0001_initial'),
        ('operation', '0001_initial'),
    ]

    operations = [
        migrations.RenameField(
            model_name='operation',
            old_name='timestamp',
            new_name='created_at',
        ),
        migrations.RemoveField(
            model_name='operation',
            name='group',
        ),
        migrations.RemoveField(
            model_name='operation',
            name='quantity',
        ),
        migrations.AddField(
            model_name='operation',
            name='description',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='operation',
            name='groups',
            field=models.ManyToManyField(related_name='operations', to='group.group'),
        ),
        migrations.AddField(
            model_name='operation',
            name='status',
            field=models.CharField(choices=[('CREATED', 'Vytvořeno'), ('IN_PROGRESS', 'Probíhá'), ('COMPLETED', 'Dokončeno'), ('CANCELLED', 'Zrušeno')], default='CREATED', max_length=15),
        ),
        migrations.AddField(
            model_name='operation',
            name='updated_at',
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AlterField(
            model_name='operation',
            name='type',
            field=models.CharField(choices=[('IN', 'Příjem'), ('OUT', 'Výdej'), ('MOVE', 'Přesun')], max_length=10),
        ),
        migrations.AlterField(
            model_name='operation',
            name='user',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='user.user'),
        ),
    ]
