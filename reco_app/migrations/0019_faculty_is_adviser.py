# Generated by Django 5.1 on 2024-10-29 05:01

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reco_app', '0018_faculty_is_available_faculty_is_capstone_teacher'),
    ]

    operations = [
        migrations.AddField(
            model_name='faculty',
            name='is_adviser',
            field=models.BooleanField(default=False),
        ),
    ]
