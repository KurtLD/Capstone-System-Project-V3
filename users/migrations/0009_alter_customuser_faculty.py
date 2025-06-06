# Generated by Django 5.1 on 2024-08-14 07:59

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reco_app', '0012_faculty_custom_user'),
        ('users', '0008_alter_customuser_is_active'),
    ]

    operations = [
        migrations.AlterField(
            model_name='customuser',
            name='faculty',
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='custom_user_profile', to='reco_app.faculty'),
        ),
    ]
