from django.db import migrations, models

def create_initial_faqs(apps, schema_editor):
    FAQ = apps.get_model('A_FAQs', 'FAQ')
    Category = apps.get_model('A_FAQs', 'FAQCategory')
    
    general_category = Category.objects.create(name='General')
    account_category = Category.objects.create(name='Account (Admin, Faculty)')
    tech_support_category = Category.objects.create(name='Tech Support')
    
    faqs = [
        # General FAQs
        {
            'category': general_category,
            'question': 'What is this system about?',
            'answer': 'This system is designed to manage undergraduate capstone projects at EVSU, automating scheduling, adviser selection, and grading processes.'
        },
        {
            'category': general_category,
            'question': 'Who can use this system?',
            'answer': 'The system is intended for use by IT department faculty, students, and administrative staff involved in capstone projects at EVSU.'
        },
        {
            'category': general_category,
            'question': 'What problems does this system solve?',
            'answer': 'It addresses inefficiencies in scheduling, inconsistent adviser assignments, and manual grading challenges.'
        },
        {
            'category': general_category,
            'question': 'Is this system accessible online?',
            'answer': 'Yes, the system is a web-based platform accessible via any modern web browser.'
        },
        {
            'category': general_category,
            'question': 'What are the main features of this system?',
            'answer': 'The main features include automated scheduling, a recommender system for adviser matching, and an automated grading module.'
        },
        # Account (Admin, Faculty) FAQs
        {
            'category': account_category,
            'question': 'How can an admin add new group information?',
            'answer': 'Admins can manually input group data or upload it via an Excel file.'
        },
        {
            'category': account_category,
            'question': 'Can faculty view their assigned schedules?',
            'answer': 'Yes, faculty members can log in to access their assigned schedules and group information.'
        },
        {
            'category': account_category,
            'question': 'How does an admin generate the title hearing schedule?',
            'answer': 'The admin can use the automated scheduling tool, which applies predefined constraints to ensure fairness and efficiency.'
        },
        {
            'category': account_category,
            'question': 'What happens if there are conflicts in scheduling?',
            'answer': 'The system uses constraint satisfaction techniques to resolve conflicts during the scheduling process.'
        },
        {
            'category': account_category,
            'question': 'Can faculty provide feedback on the grading process?',
            'answer': 'Yes, the system allows panel members to input grades and feedback, which are then used to calculate final results.'
        },
        {
            'category': account_category,
            'question': 'What is required for adviser assignment?',
            'answer': 'Admins input the approved project titles, and the system recommends advisers based on expertise and availability.'
        },
        {
            'category': account_category,
            'question': 'Can an adviser be assigned to a project they teach?',
            'answer': 'No, the system ensures that a subject teacher cannot be an adviser for the group they are teaching.'
        },
        {
            'category': account_category,
            'question': 'How does the system ensure fair adviser distribution?',
            'answer': 'The system uses a recommender engine that considers expertise and faculty workload to distribute adviser roles equitably.'
        },
        {
            'category': account_category,
            'question': 'Can an admin update group information after submission?',
            'answer': 'Yes, the admin can modify or update group details as needed.'
        },
        {
            'category': account_category,
            'question': 'Are there training materials available for admins and faculty?',
            'answer': 'Yes, the system includes user guides and documentation for admins and faculty to facilitate usage.'
        },
        # Tech Support FAQs
        {
            'category': tech_support_category,
            'question': 'What should I do if the system shows only one adviser instead of three?',
            'answer': 'If only one adviser is generated, review the input data and ensure it meets the system requirements. Further adjustments may be needed by tech support.'
        },
        {
            'category': tech_support_category,
            'question': 'How do I report a system bug?',
            'answer': 'Contact the IT departments tech support team or submit a report through the feedback feature in the system.'
        },
        {
            'category': tech_support_category,
            'question': 'What browser should I use for optimal performance?',
            'answer': 'Use the latest version of popular browsers such as Chrome, Firefox, or Edge for the best experience.'
        },
        {
            'category': tech_support_category,
            'question': 'What are the hardware requirements for running the system?',
            'answer': 'A minimum of an Intel Core i5 processor, 8GB RAM, and 256GB SSD is recommended for smooth operation.'
        },
        {
            'category': tech_support_category,
            'question': 'What database does the system use?',
            'answer': 'The system uses SQLite as its database, integrated with the Django framework.'
        },
        {
            'category': tech_support_category,
            'question': 'Is there a backup mechanism for the data?',
            'answer': 'Yes, the system includes backup protocols to secure data and prevent loss.'
        },
        {
            'category': tech_support_category,
            'question': 'How do I reset my account password?',
            'answer': 'Use the “Forgot Password” link on the login page to reset your password.'
        },
        {
            'category': tech_support_category,
            'question': 'What do I do if the automated scheduling feature fails?',
            'answer': 'Ensure that all input data is complete and correctly formatted. If the issue persists, contact tech support for assistance.'
        },
        {
            'category': tech_support_category,
            'question': 'Can the system handle simultaneous logins from multiple users?',
            'answer': 'Yes, the system supports concurrent access by multiple users without performance issues.'
        },
        {
            'category': tech_support_category,
            'question': 'What type of technical support is available?',
            'answer': 'Technical support is available via email, phone, or in-person through the IT departments support team.'
        }
    ]
    
    for faq in faqs:
        FAQ.objects.create(**faq)

class Migration(migrations.Migration):

    dependencies = [
        ('A_FAQs', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(create_initial_faqs),
    ]