# Generated by Django 4.2.19 on 2025-02-17 10:45

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('box', '0004_alter_box_position'),
    ]

    operations = [
        migrations.AlterField(
            model_name='box',
            name='depth',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
        migrations.AlterField(
            model_name='box',
            name='height',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
        migrations.AlterField(
            model_name='box',
            name='weight',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
        migrations.AlterField(
            model_name='box',
            name='width',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
    ]
