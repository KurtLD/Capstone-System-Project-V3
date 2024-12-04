# A_FAQs/admin.py

from django.contrib import admin
from .models import FAQ, FAQCategory, Review

# Register the FAQ model with the admin site
admin.site.register(FAQ)

# Register the FAQCategory model with the admin site
admin.site.register(FAQCategory)

# Register the Review model with the admin site
admin.site.register(Review)