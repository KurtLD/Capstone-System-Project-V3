from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('reco_app', '0012_faculty_custom_user'),
        ('users', '0010_remove_customuser_faculty'),  # Adjust according to your actual dependencies
    ]

    operations = [
        migrations.AlterField(
            model_name='faculty',
            name='custom_user',
            field=models.OneToOneField(
                on_delete=models.CASCADE,
                related_name='faculty_profile',
                to='users.customuser',
                null=True,  # Ensure it aligns with your model requirements
            ),
        ),
    ]

