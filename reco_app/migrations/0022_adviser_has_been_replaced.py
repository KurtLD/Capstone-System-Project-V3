# Generated by Django 5.1 on 2024-11-15 13:31

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reco_app', '0021_adviser_accepted_adviser_declined'),
    ]

    operations = [
        migrations.AddField(
            model_name='adviser',
            name='has_been_replaced',
            field=models.BooleanField(default=False),
        ),
    ]
