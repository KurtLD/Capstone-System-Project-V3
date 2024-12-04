# A_FAQs/urls.py

from django.urls import path
from . import views

# URL patterns for the A_FAQs app
urlpatterns = [
    # URL pattern for the FAQ list view
    path('', views.faq_list, name='faq_list'),
    # URL pattern for the FAQ category view
    path('category/<int:category_id>/', views.faq_category, name='faq_category'),
    path('add-review', views.add_review, name='add_review'),
    path('review/<int:review_id>/vote/', views.review_helpful_vote, name='review_helpful_vote'),
]