# Generated by Django 5.1 on 2024-08-13 14:22

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0004_remove_customuser_expertise_and_more'),
    ]

    operations = [
        migrations.RenameField(
            model_name='customuser',
            old_name='highest_educational_attainment',
            new_name='highest_degree',
        ),
    ]