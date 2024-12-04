# A_FAQs/views.py

from django.shortcuts import render
from .models import FAQ, FAQCategory, Review, ReviewHelpfulVote
from reco_app.models import Faculty
from users.models import CustomUser
from django.contrib.auth.decorators import login_required
from .forms import ReviewForm
from django.shortcuts import get_object_or_404, redirect
from django.http import JsonResponse

# View to list all FAQ categories
# def faq_list(request):
#     reviews = Review.objects.all().order_by('-created_at')
#     review_count = reviews.count()
#     print("review_count:", review_count)
#     # Annotate reviews with helpful counts
#     for review in reviews:
#         review.helpful_count = review.helpful_votes.filter(vote=True).count()
#     categories = FAQCategory.objects.all()
#     return render(request, 'A_FAQs/faq_list.html', {'categories': categories, 'reviews': reviews, 'review_count': review_count})

def faq_list(request):
    user_profile = None
    faculty_member = None

    # Check if the user is authenticated
    if request.user.is_authenticated:
        try:
            # Fetch the CustomUser object associated with the logged-in user
            user_profile = get_object_or_404(CustomUser, id=request.user.id)

            # Fetch the Faculty object associated with the CustomUser
            faculty_member = get_object_or_404(Faculty, custom_user=user_profile)
        except Exception as e:
            # Log the error or handle exceptions (e.g., user might not have a Faculty profile)
            print(f"Error fetching user or faculty profile: {e}")

    # Fetch reviews and count
    reviews = Review.objects.all().order_by('-created_at')
    review_count = reviews.count()
    print("review_count:", review_count)

    # Annotate reviews with helpful counts
    for review in reviews:
        review.helpful_count = review.helpful_votes.filter(vote=True).count()

    # Fetch FAQ categories
    categories = FAQCategory.objects.all()

    return render(request, 'A_FAQs/faq_list.html', {
        'categories': categories,
        'reviews': reviews,
        'review_count': review_count,
        'user_profile': user_profile,  # Optional for context
        'faculty_member': faculty_member  # Optional for context
    })

# View to list all FAQs in a specific category
def faq_category(request, category_id):
    # Get the specific category by ID
    category = FAQCategory.objects.get(id=category_id)
    # Get all FAQs related to this category
    faqs = category.faqs.all()
    # Render the 'faq_category.html' template with the category and its FAQs
    return render(request, 'A_FAQs/faq_category.html', {'category': category, 'faqs': faqs})

@login_required
def add_review(request):
    # Fetch the CustomUser object associated with the logged-in user
    user_profile = get_object_or_404(CustomUser, id=request.user.id)

    # Fetch the Faculty object associated with the CustomUser
    faculty_member = get_object_or_404(Faculty, custom_user=user_profile)
    
    if request.method == 'POST':
        form = ReviewForm(request.POST)
        if form.is_valid():
            print("yes")
            review = form.save(commit=False)
            review.user = faculty_member
            review.save()
            return redirect('faq_list')
        else:
            print("no")
            print(form.errors)  # Add this line

    return redirect('faq_list')

@login_required
def review_helpful_vote(request, review_id):
    # Fetch the CustomUser object associated with the logged-in user
    user_profile = get_object_or_404(CustomUser, id=request.user.id)

    # Fetch the Faculty object associated with the CustomUser
    faculty_member = get_object_or_404(Faculty, custom_user=user_profile)

    if request.method == 'POST':
        review = get_object_or_404(Review, id=review_id)
        vote_value = request.POST.get('vote') == 'yes'

        # Use defaults to set the vote when creating a new ReviewHelpfulVote
        vote, created = ReviewHelpfulVote.objects.get_or_create(
            review=review,
            user=faculty_member,
            defaults={'vote': vote_value}  # Set the default vote value
        )
        
        # If the vote already exists, update the vote
        if not created:
            vote.vote = vote_value
            vote.save()

        # Count the helpful votes
        helpful_count = review.helpful_votes.filter(vote=True).count()

        return redirect('faq_list')

    return JsonResponse({'error': 'Invalid request'}, status=400)