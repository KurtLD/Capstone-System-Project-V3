# Generated by Django 5.1 on 2024-10-29 12:54

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('scheduler_app', '0013_room_alter_schedule_room_alter_schedulefd_room_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='groupinfoth',
            name='member1',
            field=models.CharField(blank=True, default=None, max_length=100, null=True),
        ),
        migrations.AlterField(
            model_name='groupinfoth',
            name='member2',
            field=models.CharField(blank=True, default=None, max_length=100, null=True),
        ),
        migrations.AlterField(
            model_name='groupinfoth',
            name='member3',
            field=models.CharField(blank=True, default=None, max_length=100, null=True),
        ),
    ]
