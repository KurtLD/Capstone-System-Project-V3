# Generated by Django 5.1 on 2024-10-04 07:28

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('scheduler_app', '0008_schedule_is_locked'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='schedule',
            name='is_locked',
        ),
    ]