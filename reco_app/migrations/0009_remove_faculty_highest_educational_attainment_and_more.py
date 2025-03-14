# Generated by Django 5.1 on 2024-08-14 00:26

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reco_app', '0008_faculty_highest_degree_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='faculty',
            name='highest_educational_attainment',
        ),
        migrations.RemoveField(
            model_name='faculty',
            name='user',
        ),
        migrations.AlterField(
            model_name='faculty',
            name='expertise',
            field=models.ManyToManyField(blank=True, to='reco_app.expertise'),
        ),
        migrations.AlterField(
            model_name='faculty',
            name='highest_degree',
            field=models.CharField(max_length=100),
        ),
        migrations.AlterField(
            model_name='faculty',
            name='name',
            field=models.CharField(max_length=150),
        ),
    ]
