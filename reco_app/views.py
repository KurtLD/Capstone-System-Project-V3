from django.shortcuts import render, get_object_or_404, redirect
from .models import Faculty, Expertise, Adviser
from users.models import AuditTrail, SchoolYear, Notif, UserNotif
from scheduler_app.models import GroupInfoTH
from .forms import FacultyForm, DeleteFacultyForm, TitleInputForm, AdviserForm
from django.views.decorators.http import require_POST
from django.db.models import Q
from django.http import JsonResponse
from django.db.models import Count
from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required
import spacy
from collections import Counter
from spacy.lang.en.stop_words import STOP_WORDS
from spacy.tokens import Token
import logging
from django.http import HttpResponse
from scheduler_app.models import GroupInfoPOD
import json
from django.urls import reverse
from .my_dictionary import IMPORTANT_TERMS, EXPERTISE_SYNONYMS, EXPERTISE_DICTIONARY
from django.db.models.functions import Lower
from urllib.parse import urlencode


# Load the spaCy model
nlp = spacy.load("en_core_web_lg")

logger = logging.getLogger(__name__)

# Extract keywords including multi-word terms
# def extract_keywords(title):
#     doc = nlp(title)
#     keywords = set()
#     skip_next = False

#     # Loop through tokens in the document
#     for token in doc:
#         if skip_next:
#             skip_next = False
#             continue

#         # Handle multi-word terms explicitly
#         if token.text.lower() == 'machine' and token.nbor(1).text.lower() == 'learning':
#             keywords.add('machine learning')
#             skip_next = True
#         elif token.text.lower() == 'artificial' and token.nbor(1).text.lower() == 'intelligence':
#             keywords.add('artificial intelligence')
#             skip_next = True
#         elif token.text.lower() == 'deep' and token.nbor(1).text.lower() == 'learning':
#             keywords.add('deep learning')
#             skip_next = True
#         elif token.text.lower() == 'neural' and token.nbor(1).text.lower() == 'networks':
#             keywords.add('neural networks')
#             skip_next = True
#         elif token.text.lower() == 'neural' and token.nbor(1).text.lower() == 'network':
#             keywords.add('neural networks')
#             skip_next = True
#         elif token.text.lower() == 'natural' and token.nbor(1).text.lower() == 'language' and token.nbor(2).text.lower() == 'processing':
#             keywords.add('natural language processing')
#             skip_next = True
#         elif token.text.lower() == 'support' and token.nbor(1).text.lower() == 'vector' and token.nbor(2).text.lower() == 'machines':
#             keywords.add('support vector machines')
#             skip_next = True
#         elif token.text.lower() == 'reinforcement' and token.nbor(1).text.lower() == 'learning':
#             keywords.add('reinforcement learning')
#             skip_next = True
#         elif token.text.lower() == 'computer' and token.nbor(1).text.lower() == 'vision':
#             keywords.add('computer vision')
#             skip_next = True
#         elif token.text.lower() == 'predictive' and token.nbor(1).text.lower() == 'analytics':
#             keywords.add('predictive analytics')
#             skip_next = True
#         elif token.text.lower() == 'data' and token.nbor(1).text.lower() == 'science':
#             keywords.add('data science')
#             skip_next = True
#         elif token.text.lower() == 'big' and token.nbor(1).text.lower() == 'data':
#             keywords.add('big data')
#             skip_next = True
#         elif token.text.lower() == 'convolutional' and token.nbor(1).text.lower() == 'neural' and token.nbor(2).text.lower() == 'network':
#             keywords.add('convolutional neural network')
#             skip_next = True
#         elif token.text.lower() == 'convolutional' and token.nbor(1).text.lower() == 'neural' and token.nbor(2).text.lower() == 'network':
#             keywords.add('convolutional neural networks')
#             skip_next = True
#         elif token.text.lower() == 'convolutional' and token.nbor(1).text.lower() == 'network':
#             keywords.add('convolutional network')
#             skip_next = True
#         elif token.text.lower() == 'convolutional' and token.nbor(1).text.lower() == 'networks':
#             keywords.add('convolutional networks')
#             skip_next = True

#         # Add additional multi-word handling here as needed

#         # Include single word tokens that are not stop words
#         else:
#             if token.pos_ in ['NOUN', 'PROPN', 'ADJ', 'VERB']:
#                 if token.text.lower() not in STOP_WORDS and len(token.text) > 1:
#                     keywords.add(token.lemma_.lower())

#             # Add any important terms
#             if token.text.upper() in IMPORTANT_TERMS:
#                 keywords.add(token.text.upper())
#     # Handle synonyms by checking against the EXPERTISE_SYNONYMS
#     for keyword in list(keywords):
#         for expertise, synonyms in EXPERTISE_SYNONYMS.items():
#             if keyword in synonyms:
#                 keywords.add(expertise)

#     # Debugging prints
#     print("Extracted keywords:", keywords)

#     return keywords

def extract_keywords(title):
    doc = nlp(title)
    keywords = set()
    skip_next = False

    # Loop through tokens in the document
    for token in doc:
        if skip_next:
            skip_next = False
            continue

        # Handle multi-word terms explicitly
        if token.i + 1 < len(doc):  # Check if the next token exists
            # Multi-word term matching
            if token.text.lower() == 'machine' and token.nbor(1).text.lower() == 'learning':
                keywords.add('machine learning')
                skip_next = True
            elif token.text.lower() == 'artificial' and token.nbor(1).text.lower() == 'intelligence':
                keywords.add('artificial intelligence')
                skip_next = True
            elif token.text.lower() == 'deep' and token.nbor(1).text.lower() == 'learning':
                keywords.add('deep learning')
                skip_next = True
            elif token.text.lower() == 'neural' and token.nbor(1).text.lower() == 'networks':
                keywords.add('neural networks')
                skip_next = True
            elif token.text.lower() == 'natural' and token.nbor(1).text.lower() == 'language' and token.nbor(2).text.lower() == 'processing':
                keywords.add('natural language processing')
                skip_next = True
            elif token.text.lower() == 'support' and token.nbor(1).text.lower() == 'vector' and token.nbor(2).text.lower() == 'machines':
                keywords.add('support vector machines')
                skip_next = True
            elif token.text.lower() == 'reinforcement' and token.nbor(1).text.lower() == 'learning':
                keywords.add('reinforcement learning')
                skip_next = True
            elif token.text.lower() == 'computer' and token.nbor(1).text.lower() == 'vision':
                keywords.add('computer vision')
                skip_next = True
            elif token.text.lower() == 'predictive' and token.nbor(1).text.lower() == 'analytics':
                keywords.add('predictive analytics')
                skip_next = True
            elif token.text.lower() == 'data' and token.nbor(1).text.lower() == 'science':
                keywords.add('data science')
                skip_next = True
            elif token.text.lower() == 'big' and token.nbor(1).text.lower() == 'data':
                keywords.add('big data')
                skip_next = True
            elif token.text.lower() == 'convolutional' and token.nbor(1).text.lower() == 'neural' and token.nbor(2).text.lower() == 'network':
                keywords.add('convolutional neural network')
                skip_next = True

        # Always include single-word tokens that are not stop words or single letters
        if token.pos_ in ['NOUN', 'PROPN', 'ADJ', 'VERB']:
            if token.text.lower() not in STOP_WORDS and len(token.text) > 1:
                keywords.add(token.lemma_.lower())

        # Add any important terms (case-sensitive from the list)
        if token.text.upper() in IMPORTANT_TERMS:
            keywords.add(token.text.upper())

    # Handle synonyms by checking against the EXPERTISE_SYNONYMS
    for keyword in list(keywords):
        for expertise, synonyms in EXPERTISE_SYNONYMS.items():
            if keyword in synonyms:
                keywords.add(expertise)

    # Debugging prints
    print("Extracted keywords:", keywords)

    return keywords


# Match keywords to dictionary expertise and database expertise
def match_expertise_from_dictionary(keywords):
    matched_expertise = set()
    extended_keywords = set(keywords)  # Start with the original keywords

    for expertise, related_keywords in EXPERTISE_DICTIONARY.items():
        for keyword in keywords:
            if keyword in related_keywords:
                matched_expertise.add(expertise)
                # Add all related keywords to the extended list
                extended_keywords.update(related_keywords)

    return matched_expertise, extended_keywords


def filter_and_rank_faculty(request, keywords):

    school_years = SchoolYear.objects.all().order_by('start_year')
    # Get the last added school year in the db
    # last_school_year = SchoolYear.objects.all().order_by('-end_year').first()

    # Get the current active school year
    # current_school_year = SchoolYear.get_active_school_year()
    selected_school_year_id = request.session.get('selected_school_year_id')
    # get the last school year added to the db
    last_school_year = SchoolYear.objects.all().order_by('-end_year').first()

    # Get the selected school year from session or fallback to the active school year
    selected_school_year = ''
    if not selected_school_year_id:
        selected_school_year = last_school_year
        request.session['selected_school_year_id'] = selected_school_year.id  # Set in session
    else:
        # Retrieve the selected school year based on the session
        selected_school_year = SchoolYear.objects.get(id=selected_school_year_id)

    # Fetch all GroupInfoTH records
    group_info_records = GroupInfoTH.objects.filter(school_year=selected_school_year)

    # Calculate the total number of faculties with a master degree
    total_faculties_with_masters = Faculty.objects.filter(has_master_degree=True, is_active=True).count()

    # Determine the adviser limit per faculty
    if total_faculties_with_masters > 0:
        adviser_limit_per_faculty = max(1, group_info_records.count() // total_faculties_with_masters)
    else:
        adviser_limit_per_faculty = 0  # No faculties with master's degree

    faculties = Faculty.objects.filter(has_master_degree=True, is_active=True)
    expertises = Expertise.objects.all()
    ranked_faculty = []
    selected_expertise = set()

    # Match expertise from dictionary and get extended keywords
    matched_expertise_dict, extended_keywords = match_expertise_from_dictionary(keywords)

    print("Keywords:", keywords)  # Debug print for original keywords
    print("Matched expertise from dictionary:", matched_expertise_dict)
    print("Extended keywords:", extended_keywords)  # Debug print for extended keywords

    # Match expertise from database
    for keyword in extended_keywords:  # Use extended keywords for matching
        keyword_lower = keyword.lower()
        for exp in expertises:
            if keyword_lower in exp.name.lower():
                selected_expertise.add(exp)

    # Combine expertise from both dictionary and database
    combined_expertise = selected_expertise.union(matched_expertise_dict)
    print("Selected expertise from database:", selected_expertise)
    print("Combined expertise from dictionary and database:", combined_expertise)  # Debug print

    for faculty in faculties:
        expertise_list = faculty.expertise.all()
        expertise_set = set(expertise_list)

        match_score = 0
        faculty_matched_expertise = set()

        for keyword in extended_keywords:  # Use extended keywords for faculty matching
            keyword_lower = keyword.lower()
            for expertise in expertise_set:
                if keyword_lower in expertise.name.lower():
                    if expertise not in faculty_matched_expertise:
                        match_score += 1
                        faculty_matched_expertise.add(expertise)

        if match_score > 0:
            advisee_count = faculty.advisee_count()

            # Only include faculties that haven't exceeded the advisee limit
            if adviser_limit_per_faculty == 0 or advisee_count < adviser_limit_per_faculty:
                years_of_teaching = faculty.years_of_teaching
                expertise_count = len(expertise_set)
                ranked_faculty.append((faculty, match_score, years_of_teaching, expertise_count, advisee_count))

    print("Ranked faculty after matching:", ranked_faculty)  # Debug print for ranked faculty before sorting

    if not ranked_faculty:
        for faculty in faculties:
            expertise_set = set(faculty.expertise.all())
            years_of_teaching = faculty.years_of_teaching
            expertise_count = len(expertise_set)
            advisee_count = faculty.advisee_count()

            if adviser_limit_per_faculty == 0 or advisee_count < adviser_limit_per_faculty:
                ranked_faculty.append((faculty, 0, years_of_teaching, expertise_count, advisee_count))

    # Sort by match score, then by years of teaching, expertise count, and lastly by advisee count
    ranked_faculty.sort(key=lambda x: (x[1], x[2], x[3], -x[4]), reverse=True)

    print("Ranked faculty after sorting:", ranked_faculty)  # Debug print for ranked faculty after sorting

    ranked_faculty = [(faculty, score) for faculty, score, _, _, _ in ranked_faculty]

    return ranked_faculty, list(selected_expertise), adviser_limit_per_faculty

# def filter_and_rank_faculty(keywords):
#     # Fetch all GroupInfoTH records
#     group_info_records = GroupInfoTH.objects.all()

#     # Calculate the total number of faculties with a master degree
#     total_faculties_with_masters = Faculty.objects.filter(has_master_degree=True, is_active=True).count()

#     # Determine the adviser limit per faculty
#     if total_faculties_with_masters > 0:
#         adviser_limit_per_faculty = max(1, group_info_records.count() // total_faculties_with_masters)
#     else:
#         adviser_limit_per_faculty = 0  # No faculties with master's degree

#     faculties = Faculty.objects.filter(has_master_degree=True, is_active=True)
#     expertises = Expertise.objects.all()
#     ranked_faculty = []
#     selected_expertise = set()

#     # Match expertise from dictionary and get extended keywords
#     matched_expertise_dict, extended_keywords = match_expertise_from_dictionary(keywords)

#     print("Keywords:", keywords)  # Debug print for original keywords
#     print("Matched expertise from dictionary:", matched_expertise_dict)
#     print("Extended keywords:", extended_keywords)  # Debug print for extended keywords
    

#     # Match expertise from database
#     for keyword in extended_keywords:  # Use extended keywords for matching
#         keyword_lower = keyword.lower()
#         for exp in expertises:
#             if keyword_lower in exp.name.lower():
#                 selected_expertise.add(exp)

#     # Combine expertise from both dictionary and database
#     combined_expertise = selected_expertise.union(matched_expertise_dict)
#     print("Selected expertise from database:", selected_expertise)

#     for faculty in faculties:
#         expertise_list = faculty.expertise.all()
#         expertise_set = set(expertise_list)

#         match_score = 0
#         faculty_matched_expertise = set()

#         for keyword in extended_keywords:  # Use extended keywords for faculty matching
#             keyword_lower = keyword.lower()
#             for expertise in expertise_set:
#                 if keyword_lower in expertise.name.lower():
#                     if expertise not in faculty_matched_expertise:
#                         match_score += 1
#                         faculty_matched_expertise.add(expertise)

#         if match_score > 0:
#             advisee_count = faculty.advisee_count()

#             # Only include faculties that haven't exceeded the advisee limit
#             if adviser_limit_per_faculty == 0 or advisee_count < adviser_limit_per_faculty:
#                 years_of_teaching = faculty.years_of_teaching
#                 expertise_count = len(expertise_set)
#                 is_capstone_teacher = faculty.is_capstone_teacher
#                 ranked_faculty.append((faculty, match_score, is_capstone_teacher, years_of_teaching, expertise_count, advisee_count))

#     # Fallback if no faculties match expertise
#     if not ranked_faculty:
#         for faculty in faculties:
#             expertise_set = set(faculty.expertise.all())
#             years_of_teaching = faculty.years_of_teaching
#             expertise_count = len(expertise_set)
#             advisee_count = faculty.advisee_count()
#             is_capstone_teacher = faculty.is_capstone_teacher

#             if adviser_limit_per_faculty == 0 or advisee_count < adviser_limit_per_faculty:
#                 ranked_faculty.append((faculty, 0, is_capstone_teacher, years_of_teaching, expertise_count, advisee_count))

#     # Sort by match score, then by is_capstone_teacher, years of teaching, expertise count, and lastly by advisee count
#     ranked_faculty.sort(key=lambda x: (x[1], x[2], x[3], x[4], -x[5]), reverse=True)

#     # Simplify ranked faculty list for output
#     ranked_faculty = [(faculty, score) for faculty, score, _, _, _, _ in ranked_faculty]

#     return ranked_faculty, list(selected_expertise), adviser_limit_per_faculty


@login_required
def recommend_faculty(request):
    success_message = None
    school_years = SchoolYear.objects.all().order_by('start_year')
    # Get the last added school year in the db
    # last_school_year = SchoolYear.objects.all().order_by('-end_year').first()

    # Get the current active school year
    # current_school_year = SchoolYear.get_active_school_year()
    selected_school_year_id = request.session.get('selected_school_year_id')
    # get the last school year added to the db
    last_school_year = SchoolYear.objects.all().order_by('-end_year').first()

    # Get the selected school year from session or fallback to the active school year
    selected_school_year = ''
    if not selected_school_year_id:
        selected_school_year = last_school_year
        request.session['selected_school_year_id'] = selected_school_year.id  # Set in session
    else:
        # Retrieve the selected school year based on the session
        selected_school_year = SchoolYear.objects.get(id=selected_school_year_id)

    # Check if the active school year is same as the last added school year
    if selected_school_year != last_school_year:
        return HttpResponse("Oops, you are no longer allowed to access this page.")

    if request.method == 'POST':
        form = TitleInputForm(request.POST)
        if form.is_valid():
            title = form.cleaned_data['title']
            keywords = extract_keywords(title)

            # Fetch recommended faculty and their scores
            ranked_faculty, selected_expertise, adviser_limit_per_faculty = filter_and_rank_faculty(request, keywords)

            # Create a set of needed expertise names for quick lookup
            needed_expertise_names = set(exp.name for exp in selected_expertise)

            # Prepare faculty scores with expertise (either filtered or all)
            faculty_scores = []
            for index, (faculty, score) in enumerate(ranked_faculty):
                if needed_expertise_names:
                    filtered_expertise = [exp.name for exp in faculty.expertise.all() if exp.name in needed_expertise_names]
                else:
                    filtered_expertise = [exp.name for exp in faculty.expertise.all()]

                # Get the advisee count
                advisee_count = faculty.advisee_count()

                # Append to faculty_scores, including advisee_count
                faculty_scores.append((index + 1, faculty, filtered_expertise, faculty.years_of_teaching, score, advisee_count))

            # Ensure that the list has at least 3 faculty members
            if len(faculty_scores) < 3:
                remaining_faculties = Faculty.objects.filter(is_active=True).exclude(id__in=[faculty.id for _, faculty, _, _, _, _ in faculty_scores])
                for faculty in remaining_faculties:
                    filtered_expertise = [exp.name for exp in faculty.expertise.all() if exp.name in needed_expertise_names]
                    years_of_teaching = faculty.years_of_teaching
                    advisee_count = faculty.advisee_count()  # Get advisee count for remaining faculties
                    
                    # Append faculty with default score of 0 for those not initially matched
                    faculty_scores.append((len(faculty_scores) + 1, faculty, filtered_expertise, years_of_teaching, 0, advisee_count))  # use len to maintain the index correctly
                    
                    # Break loop when at least 3 faculties are listed
                    if len(faculty_scores) >= 3:
                        break

            # Sort faculty scores, including those added based on general criteria
            faculty_scores.sort(key=lambda x: (x[4], x[3], len(x[2]), -x[5]), reverse=True)  # Sorting by advisee_count as the last parameter
            top_faculty = faculty_scores[0][1]
            print("top_faculty: ", top_faculty)

            # Check if the title has an assigned adviser
            try:
                # Check if there's an adviser with the title where declined is False
                adviser = Adviser.objects.get(approved_title__iexact=title, declined=False)

                # If found, proceed with the existing behavior
                return render(request, 'admin/reco_app/adviser_info.html', {
                    'adviser': adviser.faculty,
                    'highlighted_title': title,
                    'all_titles': Adviser.objects.filter(faculty=adviser.faculty),
                    'selected_school_year': selected_school_year,
                    'last_school_year': last_school_year,
                    'school_years': school_years,
                })
            except Adviser.DoesNotExist:
                # Handle case where no adviser with declined=False exists
                adviser = Adviser.objects.filter(approved_title__iexact=title, declined=True).first()

                if adviser:
                    # If a declined adviser exists, redirect to the recommendation page
                    return redirect('recommend_faculty_again', adviser_id=adviser.id)

            # If no adviser at all is found, handle it here
            print("title is not in the db")
            group_info_options = GroupInfoTH.objects.filter(school_year=selected_school_year)

            # Initialize a list to store group names
            group_names_list = []
            members_list = []
            # Fetch all records in the Adviser model for the current school year
            existing_advisers = Adviser.objects.filter(school_year=selected_school_year)

            # Create a set to store all existing members from the Adviser model
            existing_members_set = set()

            # Extract individual members from the existing adviser groups
            for adviser in existing_advisers:
                for member in adviser.group_name.split('<br>'):
                    member = member.strip()  # Remove any whitespace
                    if member:  # Ensure non-empty strings
                        existing_members_set.add(member)

            valid_member1 = None
            valid_member2 = None
            valid_member3 = None
            # Iterate through group_info_options to validate and add members
            for group_info in group_info_options:
                # Construct the group name
                group_name = f"{group_info.member1}<br>{group_info.member2}<br>{group_info.member3}"

                # Check if the group_name already exists in the Adviser model
                group_exists = Adviser.objects.filter(group_name=group_name, school_year=selected_school_year).exists()

                # Validate and add non-None, non-existing members to the list
                if group_info.member1 and group_info.member1.strip() not in existing_members_set:
                        members_list.append(group_info.member1.strip())
                        valid_member1 = group_info.member1.strip()

                if group_info.member2 and group_info.member2.strip() not in existing_members_set:
                        members_list.append(group_info.member2.strip())
                        valid_member2 = group_info.member2.strip()

                if group_info.member3 and group_info.member3.strip() not in existing_members_set:
                        members_list.append(group_info.member3.strip())
                        valid_member3 = group_info.member3.strip()


            # Log the group names for debugging
            # members_list = list(set(members_list))
            # for name in members_list:
            #     print("members_list: ", members_list)


            # for name in existing_members_set:
            #     print("existing_members_set: ", existing_members_set)

            # Render the recommendation results page
            return render(request, 'admin/reco_app/recommendation_results.html', {
                'title': title,
                'needed_expertise': selected_expertise if selected_expertise else [],
                'faculty_scores': faculty_scores,
                'success_message': success_message,
                'keywords': keywords,  # Add keywords to the context
                'group_names_list': group_names_list,  # Pass group_info options to template
                'members_list': json.dumps(members_list),
                # 'current_school_year': current_school_year,
                'selected_school_year': selected_school_year,
                'last_school_year': last_school_year,
                'school_years': school_years,
                'adviser_limit_per_faculty': adviser_limit_per_faculty ,
                'existing_members_set': json.dumps(list(existing_members_set)),  # Pass existing members as a list
                # 'member1': group_info.member1 if group_info else None,
                # 'member2': group_info.member2 if group_info else None,
                # 'member3': group_info.member3 if group_info else None,
                'member1': valid_member1,
                'member2': valid_member2,
                'member3': valid_member3,
            })

    else:
        form = TitleInputForm()

    return render(request, 'admin/reco_app/recommend_faculty.html', {
        'form': form,
        # 'current_school_year': current_school_year,
        'selected_school_year': selected_school_year,
        'last_school_year': last_school_year,
        'school_years': school_years
    })


# @login_required
# def recommend_faculty(request):
#     success_message = None
#     school_years = SchoolYear.objects.all().order_by('start_year')
#     last_school_year = SchoolYear.objects.all().order_by('-end_year').first()
#     current_school_year = SchoolYear.get_active_school_year()

#     if current_school_year != last_school_year:
#         return HttpResponse("Oops, you are no longer allowed to access this page.")

#     if request.method == 'POST':
#         form = TitleInputForm(request.POST)
#         if form.is_valid():
#             title = form.cleaned_data['title']
#             keywords = extract_keywords(title)

#             # Fetch recommended faculty and their scores
#             ranked_faculty, selected_expertise, adviser_limit_per_faculty = filter_and_rank_faculty(keywords)
#             needed_expertise_names = set(exp.name for exp in selected_expertise)

#             # Prepare faculty scores with expertise (either filtered or all)
#             faculty_scores = []
#             for index, (faculty, score) in enumerate(ranked_faculty):
#                 filtered_expertise = [exp.name for exp in faculty.expertise.all() if exp.name in needed_expertise_names] if needed_expertise_names else [exp.name for exp in faculty.expertise.all()]
#                 advisee_count = faculty.advisee_count()

#                 # Add is_capstone_teacher info to the tuple
#                 faculty_scores.append((index + 1, faculty, filtered_expertise, faculty.years_of_teaching, score, advisee_count, faculty.is_capstone_teacher))

#             # Ensure at least 3 faculty members
#             if len(faculty_scores) < 3:
#                 remaining_faculties = Faculty.objects.filter(is_active=True).exclude(id__in=[faculty.id for _, faculty, _, _, _, _, _ in faculty_scores])
#                 for faculty in remaining_faculties:
#                     filtered_expertise = [exp.name for exp in faculty.expertise.all() if exp.name in needed_expertise_names]
#                     years_of_teaching = faculty.years_of_teaching
#                     advisee_count = faculty.advisee_count()

#                     # Add is_capstone_teacher info with default score of 0
#                     faculty_scores.append((len(faculty_scores) + 1, faculty, filtered_expertise, years_of_teaching, 0, advisee_count, faculty.is_capstone_teacher))

#                     if len(faculty_scores) >= 3:
#                         break

#             # Updated sorting key to prioritize capstone teacher status
#             faculty_scores.sort(key=lambda x: (x[4], x[6], x[3], len(x[2]), -x[5]), reverse=True)  # Sort by score, capstone status, etc.

#             try:
#                 # adviser = Adviser.objects.get(approved_title=title)
#                 adviser = Adviser.objects.get(approved_title__iexact=title)
#                 return render(request, 'admin/reco_app/adviser_info.html', {
#                     'adviser': adviser.faculty,
#                     'highlighted_title': title,
#                     'all_titles': Adviser.objects.filter(faculty=adviser.faculty),
#                     'current_school_year': current_school_year,
#                     'last_school_year': last_school_year,
#                     'school_years': school_years,

#                 })
#             except Adviser.DoesNotExist:
#                 group_info_options = GroupInfoTH.objects.all()
#                 group_names_list = [
#                     group_info for group_info in group_info_options
#                     if not Adviser.objects.filter(group_name=f"{group_info.member1}<br>{group_info.member2}<br>{group_info.member3}").exists()
#                 ]

#                 return render(request, 'admin/reco_app/recommendation_results.html', {
#                     'title': title,
#                     'needed_expertise': selected_expertise if selected_expertise else [],
#                     'faculty_scores': faculty_scores,
#                     'success_message': success_message,
#                     'keywords': keywords,
#                     'group_names_list': group_names_list,
#                     'current_school_year': current_school_year,
#                     'last_school_year': last_school_year,
#                     'school_years': school_years,
#                     'adviser_limit_per_faculty': adviser_limit_per_faculty 
#                 })
#     else:
#         form = TitleInputForm()

#     return render(request, 'admin/reco_app/recommend_faculty.html', {
#         'form': form,
#         'current_school_year': current_school_year,
#         'last_school_year': last_school_year,
#         'school_years': school_years
#     })

def clean_title(title):
    """
    Custom function to clean and validate the title.
    """
    if not isinstance(title, str):
        raise ValueError("Title must be a string.")
    if len(title.strip()) < 5:
        raise ValueError("Title must be at least 5 characters long.")
    return title.strip()  # Strip leading/trailing whitespace


# @login_required
# def recommend_faculty_again(request, adviser_id):
#     success_message = None
#     school_years = SchoolYear.objects.all().order_by('start_year')
#     # Get the last added school year in the db
#     # last_school_year = SchoolYear.objects.all().order_by('-end_year').first()

#     # Get the current active school year
#     # current_school_year = SchoolYear.get_active_school_year()
#     selected_school_year_id = request.session.get('selected_school_year_id')
#     # get the last school year added to the db
#     last_school_year = SchoolYear.objects.all().order_by('-end_year').first()

#     # Get the selected school year from session or fallback to the active school year
#     selected_school_year = ''
#     if not selected_school_year_id:
#         selected_school_year = last_school_year
#         request.session['selected_school_year_id'] = selected_school_year.id  # Set in session
#     else:
#         # Retrieve the selected school year based on the session
#         selected_school_year = SchoolYear.objects.get(id=selected_school_year_id)

#     # Check if the active school year is same as the last added school year
#     if selected_school_year != last_school_year:
#         return HttpResponse("Oops, you are no longer allowed to access this page.")

#     try:
#         adviser = Adviser.objects.get(id=adviser_id)
#         if adviser:
#             title = adviser.approved_title  # Access the title directly from the model
#             try:
#                 title = clean_title(title)  # Use the custom cleaning function
#                 print(f"Cleaned Title: {title}")
#             except ValueError as e:
#                 print(f"Error cleaning title: {e}")

#             keywords = extract_keywords(title)

#             # Fetch recommended faculty and their scores
#             ranked_faculty, selected_expertise, adviser_limit_per_faculty = filter_and_rank_faculty(request, keywords)

#             # Create a set of needed expertise names for quick lookup
#             needed_expertise_names = set(exp.name for exp in selected_expertise)

#             # Prepare faculty scores with expertise (either filtered or all)
#             faculty_scores = []
#             for index, (faculty, score) in enumerate(ranked_faculty):
#                 # Check if the faculty already exists in the Adviser model with the same title and declined = True
#                 if Adviser.objects.filter(faculty=faculty, approved_title=title, declined=True).exists():
#                     continue  # Skip this faculty if they have declined the title

#                 # Filter expertise based on selected expertise
#                 if needed_expertise_names:
#                     filtered_expertise = [exp.name for exp in faculty.expertise.all() if exp.name in needed_expertise_names]
#                 else:
#                     filtered_expertise = [exp.name for exp in faculty.expertise.all()]

#                 # Get the advisee count
#                 advisee_count = faculty.advisee_count()

#                 # Append to faculty_scores, including advisee_count
#                 faculty_scores.append((faculty, filtered_expertise, faculty.years_of_teaching, score, advisee_count))

#             # Ensure that the list has at least 3 faculty members
#             if len(faculty_scores) < 3:
#                 remaining_faculties = Faculty.objects.filter(is_active=True).exclude(id__in=[faculty.id for faculty, _, _, _, _ in faculty_scores])
#                 for faculty in remaining_faculties:
#                     if Adviser.objects.filter(faculty=faculty, approved_title=title, declined=True).exists():
#                         continue  # Skip if this faculty has declined

#                     filtered_expertise = [exp.name for exp in faculty.expertise.all() if exp.name in needed_expertise_names]
#                     years_of_teaching = faculty.years_of_teaching
#                     advisee_count = faculty.advisee_count()  # Get advisee count for remaining faculties
                    
#                     # Append faculty with default score of 0 for those not initially matched
#                     faculty_scores.append((faculty, filtered_expertise, years_of_teaching, 0, advisee_count))  # use len to maintain the index correctly
                    
#                     # Break loop when at least 3 faculties are listed
#                     if len(faculty_scores) >= 3:
#                         break

#             # Recalculate the index after filtering
#             faculty_scores = [(index + 1, faculty, filtered_expertise, years_of_teaching, score, advisee_count)
#                               for index, (faculty, filtered_expertise, years_of_teaching, score, advisee_count) in enumerate(faculty_scores)]

#             # Sort faculty scores, including those added based on general criteria
#             faculty_scores.sort(key=lambda x: (x[4], x[3], len(x[2]), -x[5]), reverse=True)  # Sorting by advisee_count as the last parameter

#             group_info_options = GroupInfoTH.objects.filter(school_year=selected_school_year)

#             # Initialize a list to store group names
#             # group_names_list = []
#             # for group_info in group_info_options:
#             #     # Construct the group name
#             #     group_name = f"{group_info.member1}<br>{group_info.member2}<br>{group_info.member3}"
                    
#             #     # Check if the group_name already exists in the Adviser model
#             #     group_exists = Adviser.objects.filter(group_name=group_name).exists()
                    
#             #     if not group_exists:
#             #         # Append the group name to the list if it doesn't exist
#             #         group_names_list.append(group_info)
#             members = adviser.group_name.split('<br>')
#             members = [member.strip() for member in members]

#             # Fill with None or empty strings if fewer than 3 members are present
#             member1, member2, member3 = (members + [None] * 3)[:3]

#             return render(request, 'admin/reco_app/recommendation_results.html', {
#                 'title': title,
#                 'needed_expertise': selected_expertise if selected_expertise else [],
#                 'faculty_scores': faculty_scores,
#                 'success_message': success_message,
#                 'keywords': keywords,  # Add keywords to the context
#                 # 'group_names_list': group_names_list,  # Pass group_info options to template
#                 # 'current_school_year': current_school_year,
#                 'selected_school_year': selected_school_year,
#                 'last_school_year': last_school_year,
#                 'school_years': school_years,
#                 'adviser_limit_per_faculty': adviser_limit_per_faculty,
#                 'member1': member1,
#                 'member2': member2,
#                 'member3': member3 
#             })
#     except Adviser.DoesNotExist:
#         messages.error(request, "Adviser not found.")
@login_required
def recommend_faculty_again(request, adviser_id):
    success_message = None
    school_years = SchoolYear.objects.all().order_by('start_year')
    selected_school_year_id = request.session.get('selected_school_year_id')
    last_school_year = SchoolYear.objects.all().order_by('-end_year').first()

    # Get the selected school year from session or fallback to the last school year
    if not selected_school_year_id:
        selected_school_year = last_school_year
        request.session['selected_school_year_id'] = selected_school_year.id
    else:
        selected_school_year = SchoolYear.objects.get(id=selected_school_year_id)

    # Check if the selected school year is the last added school year
    if selected_school_year != last_school_year:
        return HttpResponse("Oops, you are no longer allowed to access this page.")

    try:
        adviser = Adviser.objects.get(id=adviser_id)
        title = adviser.approved_title

        # Check if the title already exists with declined=False and accepted=False
        if Adviser.objects.filter(approved_title=title, declined=False, accepted=False).exists():
            # Prepare the message
            error_message = f"Cannot recommend again since there is already a new recommended adviser for that title that needs to be confirmed."

            # Encode the message in the URL
            query_params = urlencode({'error_message': error_message})
            return redirect(f"{reverse('adviser_list')}?{query_params}")


        try:
            title = clean_title(title)
        except ValueError as e:
            print(f"Error cleaning title: {e}")

        # # Check if the title already exists with declined=False and accepted=False
        # if Adviser.objects.filter(approved_title=title, declined=False, accepted=False).exists():
        #     # Prepare the message
        #     error_message = f"Cannot recommend again since there is already a new recommended adviser for this title '{title}' that needs to be confirmed."

        #     # Encode the message in the URL
        #     query_params = urlencode({'error_message': error_message})
        #     return redirect(f"{reverse('adviser_list')}?{query_params}")

        keywords = extract_keywords(title)
        ranked_faculty, selected_expertise, adviser_limit_per_faculty = filter_and_rank_faculty(request, keywords)
        needed_expertise_names = set(exp.name for exp in selected_expertise)

        # Prepare faculty scores
        faculty_scores = []
        for index, (faculty, score) in enumerate(ranked_faculty):
            if Adviser.objects.filter(faculty=faculty, approved_title=title, declined=True).exists():
                continue

            filtered_expertise = [exp.name for exp in faculty.expertise.all() 
                               if exp.name in needed_expertise_names] if needed_expertise_names else [
                               exp.name for exp in faculty.expertise.all()]
            
            advisee_count = faculty.advisee_count()
            faculty_scores.append((faculty, filtered_expertise, faculty.years_of_teaching, score, advisee_count))

        # Ensure minimum of 3 faculty members
        if len(faculty_scores) < 3:
            remaining_faculties = Faculty.objects.filter(is_active=True).exclude(
                id__in=[faculty.id for faculty, _, _, _, _ in faculty_scores]
            )
            for faculty in remaining_faculties:
                if Adviser.objects.filter(faculty=faculty, approved_title=title, declined=True).exists():
                    continue

                filtered_expertise = [exp.name for exp in faculty.expertise.all() 
                                   if exp.name in needed_expertise_names]
                faculty_scores.append((
                    faculty,
                    filtered_expertise,
                    faculty.years_of_teaching,
                    0,
                    faculty.advisee_count()
                ))
                if len(faculty_scores) >= 3:
                    break

        # Add indices and sort
        faculty_scores = [(index + 1, faculty, filtered_expertise, years_of_teaching, score, advisee_count)
                         for index, (faculty, filtered_expertise, years_of_teaching, score, advisee_count) 
                         in enumerate(faculty_scores)]
        faculty_scores.sort(key=lambda x: (x[4], x[3], len(x[2]), -x[5]), reverse=True)

        # Get members list and existing members
        members_list = []
        existing_members_set = set()
        
        # Get existing members
        existing_advisers = Adviser.objects.filter(school_year=selected_school_year)
        for existing_adviser in existing_advisers:
            for member in existing_adviser.group_name.split('<br>'):
                member = member.strip()
                if member:
                    existing_members_set.add(member)

        # Get current members from declined adviser
        members = adviser.group_name.split('<br>')
        members = [member.strip() for member in members]
        
        # Add members to members_list if not in existing_members_set
        for member in members:
            if member and member not in existing_members_set:
                members_list.append(member)

        # Get additional members from group_info_options
        group_info_options = GroupInfoTH.objects.filter(school_year=selected_school_year)
        for group_info in group_info_options:
            for member in [group_info.member1, group_info.member2, group_info.member3]:
                if member and member.strip() not in existing_members_set:
                    members_list.append(member.strip())

        # Remove duplicates while preserving order
        members_list = list(dict.fromkeys(members_list))

        # Get the current members
        member1, member2, member3 = (members + [None] * 3)[:3]

        return render(request, 'admin/reco_app/recommendation_results.html', {
            'title': title,
            'needed_expertise': selected_expertise if selected_expertise else [],
            'faculty_scores': faculty_scores,
            'success_message': success_message,
            'keywords': keywords,
            'selected_school_year': selected_school_year,
            'last_school_year': last_school_year,
            'school_years': school_years,
            'adviser_limit_per_faculty': adviser_limit_per_faculty,
            'member1': member1,
            'member2': member2,
            'member3': member3,
            'members_list': json.dumps(members_list),
            'existing_members_set': json.dumps(list(existing_members_set))
        })

    except Adviser.DoesNotExist:
        messages.error(request, "Adviser not found.")
        return redirect('adviser_list')

@login_required
def home(request):
    return render(request, 'base.html')

@login_required
def add_faculty(request):
    if request.method == 'POST':
        form = FacultyForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('faculty_list')
    else:
        form = FacultyForm()

    return render(request, 'admin/reco_app/add_faculty.html', {'form': form})

@login_required
def update_faculty(request, faculty_id):
    faculty = get_object_or_404(Faculty, id=faculty_id)
    if request.method == 'POST':
        form = FacultyForm(request.POST, instance=faculty)
        if form.is_valid():
            form.save()
            
            # Log the action in AuditTrail
            AuditTrail.objects.create(
                user=request.user,
                action=f"Updated Faculty: {faculty.name}",
                ip_address=request.META.get('REMOTE_ADDR')
            )
            
            return redirect('faculty_list')
    else:
        form = FacultyForm(instance=faculty)
    return render(request, 'admin/reco_app/update_faculty.html', {'form': form})

# @login_required
# def adviser_list(request):
#     school_years = SchoolYear.objects.all().order_by('start_year')
#     # get the last school year added to the db
#     last_school_year = SchoolYear.objects.all().order_by('-end_year').first()
#     # get the current school year
#     current_school_year = SchoolYear.get_active_school_year()

#     count = GroupInfoPOD.objects.filter(school_year=current_school_year).count()


#     query = request.GET.get('q')
#     if query:
#         advisers = Adviser.objects.filter(faculty__name__icontains=query, school_year=current_school_year)
#     else:
#         advisers = Adviser.objects.filter(school_year=current_school_year)

#     # Ensure the queryset is ordered
#     advisers = advisers.order_by('id')

#     paginator = Paginator(advisers, 10)  # Show 10 advisers per page
#     page_number = request.GET.get('page')
#     page_obj = paginator.get_page(page_number)

#     return render(request, 'admin/reco_app/adviser_list.html', {
#         'page_obj': page_obj, 
#         'query': query,
#         'current_school_year': current_school_year,
#         'last_school_year': last_school_year,
#         'school_years': school_years,
#         'count': count
#         })

@login_required
def adviser_list(request):
    school_years = SchoolYear.objects.all().order_by('start_year')
    # Get the last school year added to the db
    # last_school_year = SchoolYear.objects.all().order_by('-end_year').first()
    # Get the current school year
    # current_school_year = SchoolYear.get_active_school_year()
    selected_school_year_id = request.session.get('selected_school_year_id')
    # get the last school year added to the db
    last_school_year = SchoolYear.objects.all().order_by('-end_year').first()

    # Get the selected school year from session or fallback to the active school year
    selected_school_year = ''
    if not selected_school_year_id:
        selected_school_year = last_school_year
        request.session['selected_school_year_id'] = selected_school_year.id  # Set in session
    else:
        # Retrieve the selected school year based on the session
        selected_school_year = SchoolYear.objects.get(id=selected_school_year_id)

    count = GroupInfoPOD.objects.filter(school_year=selected_school_year).count()

    query = request.GET.get('q')  # For the search input
    filter_status = request.GET.get('filter_status', 'all')  # Default to "all"

    # Start building the queryset
    advisers = Adviser.objects.filter(school_year=selected_school_year)

    # Apply the search filter if a query is provided
    if query:
        advisers = advisers.filter(faculty__name__icontains=query)

    # Apply the dropdown filter
    if filter_status == 'declined':
        advisers = advisers.filter(declined=True, has_been_replaced=False)
    elif filter_status == 'accepted':
        advisers = advisers.filter(accepted=True)
    elif filter_status == 'replaced':
        advisers = advisers.filter(declined=True, has_been_replaced=True)
    # "All" does not require additional filtering

    # Ensure the queryset is ordered
    advisers = advisers.order_by('-id')

    # Paginate the results
    paginator = Paginator(advisers, 10)  # Show 10 advisers per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    error_message = request.GET.get('error_message', None)

    return render(request, 'admin/reco_app/adviser_list.html', {
        'page_obj': page_obj, 
        'query': query,
        'filter_status': filter_status,  # Pass the selected filter to the template
        # 'current_school_year': current_school_year,
        'selected_school_year': selected_school_year,
        'last_school_year': last_school_year,
        'school_years': school_years,
        'count': count,
        'error_message': error_message
    })



@login_required
@require_POST
def update_adviser(request, title_id):
    adviser = get_object_or_404(Adviser, id=title_id)
    form = AdviserForm(request.POST, instance=adviser)
    if form.is_valid():
        form.save()
        
        # Log the action in AuditTrail
        AuditTrail.objects.create(
            user=request.user,
            action=f"Updated Adviser: {adviser.faculty.name}, Title: {adviser.approved_title}",
            ip_address=request.META.get('REMOTE_ADDR')
        )
        
        return JsonResponse({'success': True})
    else:
        return JsonResponse({'success': False, 'errors': form.errors}, status=400)

@login_required
def update_adviser2(request, title_id):
    adviser = get_object_or_404(Adviser, id=title_id)
    if request.method == 'POST':
        form = AdviserForm(request.POST, instance=adviser)
        if form.is_valid():
            form.save()
            
            # Log the action in AuditTrail
            AuditTrail.objects.create(
                user=request.user,
                action=f"Updated Adviser: {adviser.faculty.name}, Title: {adviser.approved_title}",
                ip_address=request.META.get('REMOTE_ADDR')
            )
            
            return redirect('adviser_info', title_id=title_id)
    else:
        form = AdviserForm(instance=adviser)
    return render(request, 'admin/reco_app/update_adviser2.html', {'form': form, 'adviser': adviser})


@login_required
def disable_faculty(request, pk):
    faculty = get_object_or_404(Faculty, pk=pk)
    faculty.is_active = False  # Set is_active to False
    faculty.save()

    # Log the action in AuditTrail
    AuditTrail.objects.create(
        user=request.user,
        action=f"Disabled Faculty: {faculty.name}",
        ip_address=request.META.get('REMOTE_ADDR')
    )

    return redirect('faculty_list')

@login_required
def disabled_faculty_list(request):
    school_years = SchoolYear.objects.all().order_by('start_year')
    # get the last school year added to the db
    # last_school_year = SchoolYear.objects.all().order_by('-end_year').first()
    # get the current school year
    # current_school_year = SchoolYear.get_active_school_year()
    selected_school_year_id = request.session.get('selected_school_year_id')
    # get the last school year added to the db
    last_school_year = SchoolYear.objects.all().order_by('-end_year').first()

    # Get the selected school year from session or fallback to the active school year
    selected_school_year = ''
    if not selected_school_year_id:
        selected_school_year = last_school_year
        request.session['selected_school_year_id'] = selected_school_year.id  # Set in session
    else:
        # Retrieve the selected school year based on the session
        selected_school_year = SchoolYear.objects.get(id=selected_school_year_id)

    disabled_faculty = Faculty.objects.filter(is_active=False)  # Filter applied
    paginator = Paginator(disabled_faculty, 10)  # Show 10 faculty members per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'admin/reco_app/disabled_faculty_list.html', 
        {'page_obj': page_obj,
        # 'current_school_year': current_school_year,
        'selected_school_year': selected_school_year,
        'last_school_year': last_school_year,
        'school_years': school_years
        })

@login_required
def enable_faculty(request, pk):
    faculty = get_object_or_404(Faculty, pk=pk)
    faculty.is_active = True  # Set is_active to True
    faculty.save()

    # Log the action in AuditTrail
    AuditTrail.objects.create(
        user=request.user,
        action=f"Enabled Faculty: {faculty.name}",
        ip_address=request.META.get('REMOTE_ADDR')
    )

    return redirect('disabled_faculty_list')

@login_required
def faculty_list(request):
    school_years = SchoolYear.objects.all().order_by('start_year')
    # get the last school year added to the db
    # last_school_year = SchoolYear.objects.all().order_by('-end_year').first()
    # get the current school year
    # current_school_year = SchoolYear.get_active_school_year()
    selected_school_year_id = request.session.get('selected_school_year_id')
    # get the last school year added to the db
    last_school_year = SchoolYear.objects.all().order_by('-end_year').first()

    # Get the selected school year from session or fallback to the active school year
    selected_school_year = ''
    if not selected_school_year_id:
        selected_school_year = last_school_year
        request.session['selected_school_year_id'] = selected_school_year.id  # Set in session
    else:
        # Retrieve the selected school year based on the session
        selected_school_year = SchoolYear.objects.get(id=selected_school_year_id)

    query = request.GET.get('q', '')
    active_faculty = Faculty.objects.filter(is_active=True, name__icontains=query).order_by('-years_of_teaching')
    
    paginator = Paginator(active_faculty, 10)  # Show 10 faculty members per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'admin/reco_app/faculty_list.html', 
        {'page_obj': page_obj, 
        'query': query,
        # 'current_school_year': current_school_year,
        'selected_school_year': selected_school_year,
        'last_school_year': last_school_year,
        'school_years': school_years
        })

# @require_POST
# @login_required
# def save_adviser(request):
#     school_years = SchoolYear.objects.all().order_by('start_year')
#     # get the last school year added to the db
#     last_school_year = SchoolYear.objects.all().order_by('-end_year').first()
#     # get the current school year
#     current_school_year = SchoolYear.get_active_school_year()

#     # Retrieve data from POST request
#     faculty_id = request.POST.get('faculty_id')
#     approved_title = request.POST.get('approved_title')
#     group_info1 = request.POST.get('group_info1')
#     group_info2 = request.POST.get('group_info2')
#     group_info3 = request.POST.get('group_info3')
#     group_info_name = f"{group_info1}<br>{group_info2}<br>{group_info3}"
#     # group_info_id = request.POST.get('group_info')
#     print("group_info_name: ", group_info_name)
#     # current_school_year = SchoolYear.get_active_school_year()


#     # Removed the commented-out group_info_id part if it's not in use
#     if not faculty_id or not approved_title:
#         return JsonResponse({'status': 'error', 'message': 'Missing data'}, status=400)

#     # Check that the required fields are in the request and log errors if needed.
#     try:
#         # Ensure the Faculty object is retrieved correctly.
#         faculty = Faculty.objects.get(id=faculty_id)

#         # Create the adviser with group_name.
#         adviser = Adviser.objects.create(
#             faculty=faculty,
#             approved_title=approved_title,
#             group_name=group_info_name,
#             school_year=current_school_year
#         )

#         # Handle previously declined adviser, if applicable.
#         try:
#             adviser_from_db = Adviser.objects.get(approved_title=approved_title, declined=True)
#             adviser_from_db.has_been_replaced = True
#             adviser_from_db.save()
#         except Adviser.DoesNotExist:
#             pass  # No declined adviser found, so no action needed.

#         # Audit Trail Entry
#         AuditTrail.objects.create(
#             user=request.user,
#             action=f"Recommend Adviser: {faculty.name}<br> Title: {approved_title}<br> For group:<br> {group_info_name}",
#             ip_address=request.META.get('REMOTE_ADDR')
#         )

#         return JsonResponse({
#             'status': 'success',
#             'adviser_id': adviser.id,
#             'group_name': group_info_name,
#         })

#     except Faculty.DoesNotExist:
#         logger.error(f'Faculty with ID {faculty_id} does not exist.')
#         return JsonResponse({'status': 'error', 'message': 'Faculty not found'}, status=404)
#     except ValueError as e:
#         logger.error(f'ValueError: {e}')
#         return JsonResponse({'status': 'error', 'message': 'Invalid ID format'}, status=400)
#     except Exception as e:
#         logger.error(f'An unexpected error occurred: {e}')
#         return JsonResponse({'status': 'error', 'message': 'An error occurred'}, status=500)

@require_POST
@login_required
def save_adviser(request):
    school_years = SchoolYear.objects.all().order_by('start_year')
    # Get the last school year added to the DB
    # last_school_year = SchoolYear.objects.all().order_by('-end_year').first()
    # Get the current school year
    # current_school_year = SchoolYear.get_active_school_year()
    selected_school_year_id = request.session.get('selected_school_year_id')
    # get the last school year added to the db
    last_school_year = SchoolYear.objects.all().order_by('-end_year').first()

    # Get the selected school year from session or fallback to the active school year
    selected_school_year = ''
    if not selected_school_year_id:
        selected_school_year = last_school_year
        request.session['selected_school_year_id'] = selected_school_year.id  # Set in session
    else:
        # Retrieve the selected school year based on the session
        selected_school_year = SchoolYear.objects.get(id=selected_school_year_id)

    # Retrieve data from POST request
    faculty_id = request.POST.get('faculty_id')
    approved_title = request.POST.get('approved_title')
    group_info1 = request.POST.get('group_info1')
    group_info2 = request.POST.get('group_info2')
    group_info3 = request.POST.get('group_info3', None)
    group_info_name = f"{group_info1}<br>{group_info2}<br>{group_info3}"

    print("group_info_name: ", group_info_name)

    if not faculty_id or not approved_title:
        return JsonResponse({'status': 'error', 'message': 'Missing data'}, status=400)

    # Check that the required fields are in the request and log errors if needed.
    try:
        # Ensure the Faculty object is retrieved correctly.
        faculty = Faculty.objects.get(id=faculty_id)

        # Create the adviser with group_name.
        adviser = Adviser.objects.create(
            faculty=faculty,
            approved_title=approved_title,
            group_name=group_info_name,
            school_year=selected_school_year,
            notif=f"You have been recommended as an adviser for the capstone project titled: <br>'{approved_title}'<br> for group:<br> {group_info_name}"
        )

        # Handle previously declined adviser, if applicable.
        try:
            # adviser_from_db = Adviser.objects.get(approved_title=approved_title, declined=True)
            # adviser_from_db.has_been_replaced = True
            # adviser_from_db.save()
            adviser_from_db = Adviser.objects.filter(
                Q(approved_title=approved_title, declined=True) |
                Q(faculty=faculty, approved_title=approved_title, declined=True, has_been_replaced=True)
            ).first()  # Use first() instead of get() to avoid MultipleObjectsReturned error

            if adviser_from_db:
                adviser_from_db.has_been_replaced = True
                adviser_from_db.save()
        except Adviser.DoesNotExist:
            pass  # No declined adviser found, so no action needed.

        # Audit Trail Entry
        AuditTrail.objects.create(
            user=request.user,
            action=f"Recommend Adviser: {faculty.name}<br> Title: {approved_title}<br> For group:<br> {group_info_name}",
            ip_address=request.META.get('REMOTE_ADDR')
        )

        # creating a notif
        notif = Notif.objects.create(
            created_by=request.user,
            notif=f"You have been recommended as an adviser for the capstone project titled: <br>'{approved_title}'",
            personal_notif=True,
            category="Recommender"
        )

        # Associate this notification with the specific user (faculty)
        UserNotif.objects.create(
            user=faculty.custom_user,  # Assuming `faculty.user` links to the User model
            notif=notif
        )

        # Redirect to the adviser list page after saving
        return redirect(reverse('adviser_list'))

    except Faculty.DoesNotExist:
        logger.error(f'Faculty with ID {faculty_id} does not exist.')
        return JsonResponse({'status': 'error', 'message': 'Faculty not found'}, status=404)
    except ValueError as e:
        logger.error(f'ValueError: {e}')
        return JsonResponse({'status': 'error', 'message': 'Invalid ID format'}, status=400)
    except Exception as e:
        logger.error(f'An unexpected error occurred: {e}')
        return JsonResponse({'status': 'error', 'message': 'An error occurred'}, status=500)

@login_required
def delete_adviser(request, adviser_id):
    adviser = get_object_or_404(Adviser, id=adviser_id)
    adviser_name = adviser.faculty.name
    adviser_title = adviser.approved_title
    adviser.delete()

    # Get the current active school year
    active_school_year = SchoolYear.get_active_school_year()
    names = adviser.group_name.split('<br>')
    member1 = names[0] if len(names) > 0 else None
    member2 = names[1] if len(names) > 1 else None
    member3 = names[2] if len(names) > 2 else None

    groups = GroupInfoPOD.objects.filter(member1=member1, member2=member2, member3=member3, school_year=active_school_year).exists()
    if groups:
        GroupInfoPOD.objects.filter(member1=member1, member2=member2, member3=member3, school_year=active_school_year).delete()

    # Log the action in AuditTrail
    AuditTrail.objects.create(
        user=request.user,
        action=f"Deleted Adviser: {adviser_name}<br>Title: {adviser_title}",
        ip_address=request.META.get('REMOTE_ADDR')
    )

    return redirect('adviser_list')


@login_required
def adviser_info(request, title_id):
    school_years = SchoolYear.objects.all().order_by('start_year')
    # get the last school year added to the db
    # last_school_year = SchoolYear.objects.all().order_by('-end_year').first()
    # get the current school year
    # current_school_year = SchoolYear.get_active_school_year()
    selected_school_year_id = request.session.get('selected_school_year_id')
    # get the last school year added to the db
    last_school_year = SchoolYear.objects.all().order_by('-end_year').first()

    # Get the selected school year from session or fallback to the active school year
    selected_school_year = ''
    if not selected_school_year_id:
        selected_school_year = last_school_year
        request.session['selected_school_year_id'] = selected_school_year.id  # Set in session
    else:
        # Retrieve the selected school year based on the session
        selected_school_year = SchoolYear.objects.get(id=selected_school_year_id)


    adviser = get_object_or_404(Adviser, id=title_id)
    all_titles = Adviser.objects.filter(faculty=adviser.faculty)
    highlighted_title = adviser.approved_title

    return render(request, 'admin/reco_app/adviser_info.html', {
        'adviser': adviser.faculty,
        'highlighted_title': highlighted_title,
        'all_titles': all_titles,
        # 'current_school_year': current_school_year,
        'selected_school_year': selected_school_year,
        'last_school_year': last_school_year,
        'school_years': school_years
    })

def get_faculty(request):
    school_years = SchoolYear.objects.all().order_by('start_year')
    # get the last school year added to the db
    # last_school_year = SchoolYear.objects.all().order_by('-end_year').first()
    # get the current school year
    # current_school_year = SchoolYear.get_active_school_year()
    selected_school_year_id = request.session.get('selected_school_year_id')
    # get the last school year added to the db
    last_school_year = SchoolYear.objects.all().order_by('-end_year').first()

    # Get the selected school year from session or fallback to the active school year
    selected_school_year = ''
    if not selected_school_year_id:
        selected_school_year = last_school_year
        request.session['selected_school_year_id'] = selected_school_year.id  # Set in session
    else:
        # Retrieve the selected school year based on the session
        selected_school_year = SchoolYear.objects.get(id=selected_school_year_id)

    faculties = Faculty.objects.all().values('id', 'name')
    return JsonResponse(list(faculties), safe=False)

def get_group_members(request):
    school_years = SchoolYear.objects.all().order_by('start_year')
    # get the last school year added to the db
    # last_school_year = SchoolYear.objects.all().order_by('-end_year').first()
    # get the current school year
    # current_school_year = SchoolYear.get_active_school_year()
    selected_school_year_id = request.session.get('selected_school_year_id')
    # get the last school year added to the db
    last_school_year = SchoolYear.objects.all().order_by('-end_year').first()

    # Get the selected school year from session or fallback to the active school year
    selected_school_year = ''
    if not selected_school_year_id:
        selected_school_year = last_school_year
        request.session['selected_school_year_id'] = selected_school_year.id  # Set in session
    else:
        # Retrieve the selected school year based on the session
        selected_school_year = SchoolYear.objects.get(id=selected_school_year_id)

    groups = GroupInfoTH.objects.filter(school_year=selected_school_year).values('id', 'member1', 'member2', 'member3')
    return JsonResponse(list(groups), safe=False)

@login_required
def assign_capstone_teacher(request, faculty_id):
    faculty = get_object_or_404(Faculty, pk=faculty_id)
    faculty.is_capstone_teacher = True
    faculty.save()

    # Log the action in AuditTrail
    AuditTrail.objects.create(
        user=request.user,
        action=f"Assigned Capstone Teacher: {faculty.name}",
        ip_address=request.META.get('REMOTE_ADDR')
    )

    return redirect('faculty_list')  # Adjust the redirect as necessary

@login_required
def remove_capstone_teacher(request, faculty_id):
    faculty = get_object_or_404(Faculty, pk=faculty_id)
    faculty.is_capstone_teacher = False
    faculty.save()

    # Log the action in AuditTrail
    AuditTrail.objects.create(
        user=request.user,
        action=f"Unassigned Capstone Teacher: {faculty.name}",
        ip_address=request.META.get('REMOTE_ADDR')
    )

    return redirect('faculty_list')

# def delete_faculty(request, pk):
#     faculty = get_object_or_404(Faculty, pk=pk)
#     faculty.delete()
#     # messages.success(request, "Faculty deleted permanently.")
#     return redirect('disabled_faculty_list')

def delete_faculty(request, pk):
    faculty = get_object_or_404(Faculty, pk=pk)
    # Retrieve the associated CustomUser
    custom_user = faculty.custom_user

    # Delete the Faculty instance
    faculty.delete()

    # Delete the associated CustomUser instance, if it exists
    if custom_user:
        custom_user.delete()

    # Optional: Add a success message
    # messages.success(request, "Faculty and associated user deleted permanently.")

    return redirect('disabled_faculty_list')