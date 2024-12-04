# A_FAQs/models.py

from django.db import models
from reco_app.models import Faculty

# Model to represent a category of FAQs
class FAQCategory(models.Model):
    # Name of the category
    name = models.CharField(max_length=255)

    # String representation of the model
    def __str__(self):
        return self.name

# Model to represent an individual FAQ
class FAQ(models.Model):
    # Foreign key to link FAQ to a category
    category = models.ForeignKey(FAQCategory, on_delete=models.CASCADE, related_name='faqs')
    # Question text
    question = models.CharField(max_length=255)
    # Answer text
    answer = models.TextField()

    # String representation of the model
    def __str__(self):
        return self.question

class Review(models.Model):
    user = models.ForeignKey(Faculty, on_delete=models.CASCADE, related_name='reviews')
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user}: {self.text[:50]}"

class ReviewHelpfulVote(models.Model):
    review = models.ForeignKey(Review, on_delete=models.CASCADE, related_name='helpful_votes')
    user = models.ForeignKey(Faculty, on_delete=models.CASCADE)  # Use Faculty instead of User
    vote = models.BooleanField()  # True for helpful, False for not helpful

    class Meta:
        unique_together = ('review', 'user')  # Prevent duplicate votes by the same user on the same review