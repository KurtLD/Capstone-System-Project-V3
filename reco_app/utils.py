import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from .models import Faculty, Adviser
import logging

# Define the expertise mapping
expertise_mapping = {
    "Machine Learning": "Machine Learning",
    "Web Development": "Web Development",
    "Data Analysis": "Data Analysis",
    "Cybersecurity": "Cybersecurity",
    "Mobile Development": "Mobile Development",
    "Game Development": "Game Development",
    "Artificial Intelligence": "Artificial Intelligence",
    "Internet of Things": "Internet of Things",
    "E-commerce": "E-commerce",
    "Healthcare Informatics": "Healthcare Informatics",
    "Educational Technology": "Educational Technology",
    "Financial Technology": "Financial Technology",
    "Smart City Technologies": "Smart City Technologies",
    "Human-Computer Interaction": "Human-Computer Interaction",
    "Agricultural Technology": "Agricultural Technology",
    "Software Engineering": "Software Engineering",
    "Computer Networks": "Computer Networks",
    "Multimedia and Graphics": "Multimedia and Graphics",
    "Database Management and Information Systems": "Database Management and Information Systems",
    "Geographic Information Systems (GIS)": "Geographic Information Systems (GIS)"
}

def normalize_text(text):
    # Convert camel case to space-separated words
    text = re.sub(r'(?<!^)(?=[A-Z])', ' ', text)
    # Convert to lowercase
    text = text.lower()
    return text

def get_needed_expertise_for_title(title):
    # Normalize the title
    normalized_title = normalize_text(title)
    
    # Normalize expertise keys
    normalized_expertise_keys = [normalize_text(key) for key in expertise_mapping.keys()]

    # Use scikit-learn's TfidfVectorizer
    vectorizer = TfidfVectorizer()
    # Vectorize the normalized expertise keys
    key_vectors = vectorizer.fit_transform(normalized_expertise_keys)
    # Vectorize the normalized title
    title_vector = vectorizer.transform([normalized_title])
    
    # Compute cosine similarities
    similarities = cosine_similarity(title_vector, key_vectors).flatten()

    # Check if the maximum similarity score is below a threshold (e.g., 0.1)
    if similarities.max() < 0.1:
        return 'General Expertise'

    # Find the best matching expertise key
    best_match_index = similarities.argmax()
    best_match_key = list(expertise_mapping.keys())[best_match_index]
    
    return expertise_mapping.get(best_match_key, 'General Expertise')

def get_expertise_descriptions():
    faculty_list = Faculty.objects.filter(has_master_degree=True, is_active=True)
    descriptions = []
    for faculty in faculty_list:
        description = []
        if faculty.mobile_web_dev:
            description.append("Mobile and Web Application Development")
        if faculty.database_management:
            description.append("Database Management and Information Systems")
        if faculty.ai_ml:
            description.append("Artificial Intelligence and Machine Learning")
        if faculty.iot:
            description.append("Internet of Things (IoT)")
        if faculty.cybersecurity:
            description.append("Cybersecurity")
        if faculty.gis:
            description.append("Geographic Information Systems (GIS)")
        if faculty.data_analytics:
            description.append("Data Analytics and Business Intelligence")
        if faculty.ecommerce_digital_marketing:
            description.append("E-commerce and Digital Marketing")
        if faculty.educational_technology:
            description.append("Educational Technology")
        if faculty.healthcare_informatics:
            description.append("Healthcare Informatics")
        if faculty.game_development:
            description.append("Game Development")
        if faculty.hci:
            description.append("Human-Computer Interaction")
        if faculty.agricultural_technology:
            description.append("Agricultural Technology")
        if faculty.smart_city_technologies:
            description.append("Smart City Technologies")
        if faculty.fintech:
            description.append("Financial Technology (FinTech)")
        if faculty.computer_networks:
            description.append("Computer Networks")
        if faculty.software_engineering:
            description.append("Software Engineering")
        if faculty.multimedia_graphics:
            description.append("Multimedia and Graphics")

        if description:  # Ensure the description is not empty
            descriptions.append(' '.join(description))
    
    if not descriptions:
        logging.warning("No valid descriptions found. Ensure that the faculty members have expertise fields filled.")
        return [], faculty_list

    return descriptions, faculty_list

def find_top_n_advisers(title, top_n=3, max_matches=10):
    expertise_descriptions, faculty_list = get_expertise_descriptions()

    # Check if descriptions are not empty
    if not expertise_descriptions:
        raise ValueError("No valid descriptions found for faculty members.")

    # Create TF-IDF vectorizer
    vectorizer = TfidfVectorizer()
    tfidf_matrix = vectorizer.fit_transform(expertise_descriptions)

    # Process the title
    query_tfidf = vectorizer.transform([title])

    # Calculate similarities
    similarities = cosine_similarity(query_tfidf, tfidf_matrix).flatten()

    # Check if the maximum similarity score is below a threshold (e.g., 0.1)
    if similarities.max() < 0.1:
        # Set all similarities to 0 to prioritize years of teaching
        similarities = [0] * len(similarities)

    # Combine faculty and their corresponding similarity scores
    scores = list(zip(faculty_list, similarities))

    
    # Convert faculty_list to a list to use the index method
    faculty_list = list(faculty_list)
    
    # Filter out faculty with 4 or more advisees and ensure they have relevant expertise
    eligible_advisers = [
        faculty for faculty, score in scores 
        if Adviser.objects.filter(faculty=faculty).count() < 4 and score > 0
    ]

    # Sort by years of teaching first and then by similarity score in descending order
    eligible_advisers.sort(key=lambda x: (x.years_of_teaching, similarities[faculty_list.index(x)]), reverse=True)

    # Return top n eligible advisers and top max_matches eligible advisers
    return eligible_advisers[:top_n], eligible_advisers[:max_matches]