import logging
import random
from collections import defaultdict, deque
from django.shortcuts import render, redirect
from django.contrib import messages
from django.db import transaction
from .models import GroupInfoPOD, Faculty, SchedulePOD, Schedule, Room
from datetime import datetime, timedelta
from users.models import SchoolYear
import re

# Set up logging
logger = logging.getLogger(__name__)

# def normalize_members(members):
#     """Normalize member names for comparison."""
#     return sorted([member.strip().lower() for member in members if member])

def normalize_members(members):
    """
    Normalize member names for comparison.
    Ensures consistent formatting and removes trailing initials like 'A.'.
    """
    def clean_name(name):
        # Remove trailing initials (e.g., 'A.' or 'B.') using regex
        name = re.sub(r'\s+[A-Z]\.$', '', name.strip())
        return name.lower()

    return sorted([clean_name(member) for member in members if member])

# def remove_faculties(excluded_faculty1, excluded_faculty2, members_pod, faculty_bookings, day, slot, faculty_loads):
#     """Select faculties for the given group, avoiding those in the exclusion lists and preferring those with fewer assignments.
#        Ensure the first faculty has a master's degree, highest years of teaching, or highest degree among the three."""
#     prev_panel = []
#     current_school_year = SchoolYear.get_active_school_year()
#     # selected_school_year_id = request.session.get('selected_school_year_id')
#     # # get the last school year added to the db
#     # last_school_year = SchoolYear.objects.all().order_by('-end_year').first()

#     # # Get the selected school year from session or fallback to the active school year
#     # selected_school_year = ''
#     # if not selected_school_year_id:
#     #     selected_school_year = last_school_year
#     #     request.session['selected_school_year_id'] = selected_school_year.id  # Set in session
#     # else:
#     #     # Retrieve the selected school year based on the session
#     #     selected_school_year = SchoolYear.objects.get(id=selected_school_year_id)

#     # # Fetch existing schedules to check for previous panel assignments
#     schedules = Schedule.objects.filter(school_year=current_school_year, has_been_rescheduled=False)

#     for schedule in schedules:
#         members_schedule = schedule.get_members()
#         if normalize_members(members_pod) == normalize_members(members_schedule):
#             prev_panel.extend(schedule.get_faculties_by_members())
#             # Remove excluded faculties from the previous panel
#             prev_panel = [faculty for faculty in prev_panel if faculty not in excluded_faculty1 and faculty not in excluded_faculty2]
#             if len(set(prev_panel)) >= 3:
#                 # Ensure uniqueness and return only the first three
#                 prev_panel = list(set(prev_panel))[:3]
#                 return validate_lead_faculty(prev_panel)  # Apply the new validation

#     # If not enough faculties, fill up with new ones while balancing load
#     available_faculties = Faculty.objects.filter(is_active=True).exclude(
#         id__in=[fac.id for fac in excluded_faculty1 | excluded_faculty2]
#     )
#     sorted_faculties = sorted(available_faculties, key=lambda f: faculty_loads[f.id])  # Sort by current load

#     for faculty in sorted_faculties:
#         # Skip if faculty already has an assignment in the same slot/day
#         if (faculty.id not in faculty_bookings or slot not in faculty_bookings[faculty.id][day]):
#             prev_panel.append(faculty)
#             if len(prev_panel) >= 3:
#                 break

#     return validate_lead_faculty(list(set(prev_panel))[:3])  # Ensure validation of lead faculty

# def remove_faculties(excluded_faculty1, excluded_faculty2, members_pod, faculty_bookings, day, slot, faculty_loads):
#     """
#     Selectively replaces conflicting faculties while retaining the original order as much as possible.
#     Ensures the final panel includes a validated lead faculty, fills up with available faculties
#     to reach three members, and integrates load balancing during selection.
#     """
#     current_school_year = SchoolYear.get_active_school_year()
#     schedules = Schedule.objects.filter(school_year=current_school_year, has_been_rescheduled=False)
#     prev_panel = []

#     # Convert excluded_faculty1 and excluded_faculty2 to sets of IDs
#     excluded_faculty1_ids = {fac.id if hasattr(fac, 'id') else fac for fac in excluded_faculty1}
#     excluded_faculty2_ids = {fac.id if hasattr(fac, 'id') else fac for fac in excluded_faculty2}
#     all_excluded_ids = excluded_faculty1_ids | excluded_faculty2_ids

#     # Step 1: Identify the previous panel for the given members pod
#     for schedule in schedules:
#         members_schedule = schedule.get_members()
#         if normalize_members(members_pod) == normalize_members(members_schedule):
#             prev_panel.extend(schedule.get_faculties_by_members())
#             break

#     # Step 2: Selectively replace conflicting faculties
#     new_panel = []
#     for faculty in prev_panel:
#         faculty_id = faculty.id if hasattr(faculty, 'id') else faculty
#         if faculty_id in all_excluded_ids:
#             # Replace conflicting faculty
#             available_faculties = Faculty.objects.filter(is_active=True).exclude(
#                 id__in=all_excluded_ids | {f.id if hasattr(f, 'id') else f for f in new_panel}
#             )
#             sorted_faculties = sorted(available_faculties, key=lambda f: faculty_loads[f.id])
#             replacement = next(iter(sorted_faculties), None)
#             if replacement:
#                 new_panel.append(replacement)
#         else:
#             # Retain non-conflicting faculty
#             new_panel.append(faculty)

#     # Step 3: Fill up gaps to ensure three members in the panel
#     if len(new_panel) < 3:
#         available_faculties = Faculty.objects.filter(is_active=True).exclude(
#             id__in=all_excluded_ids | {f.id if hasattr(f, 'id') else f for f in new_panel}
#         )
#         sorted_faculties = sorted(available_faculties, key=lambda f: faculty_loads[f.id])

#         for faculty in sorted_faculties:
#             if len(new_panel) < 3:
#                 new_panel.append(faculty)
#             else:
#                 break

#     # Step 4: Validate and finalize the panel with lead faculty criteria
#     final_panel = validate_lead_faculty(new_panel[:3])  # Ensure exactly three members and validate the lead faculty

#     return final_panel

# def remove_faculties(excluded_faculty1, excluded_faculty2, members_pod, faculty_bookings, day, slot, faculty_loads):
#     """
#     Selectively replaces conflicting faculties while retaining the original order as much as possible.
#     Ensures the final panel includes a validated lead faculty, fills up with available faculties
#     to reach three members, and integrates load balancing during selection.
#     """
#     current_school_year = SchoolYear.get_active_school_year()
#     schedules = Schedule.objects.filter(school_year=current_school_year, has_been_rescheduled=False)
#     prev_panel = []

#     # Convert excluded_faculty1 and excluded_faculty2 to sets of IDs
#     excluded_faculty1_ids = {fac.id if hasattr(fac, 'id') else fac for fac in excluded_faculty1}
#     excluded_faculty2_ids = {fac.id if hasattr(fac, 'id') else fac for fac in excluded_faculty2}
#     all_excluded_ids = excluded_faculty1_ids | excluded_faculty2_ids

#     # Step 1: Identify the previous panel for the given members pod
#     for schedule in schedules:
#         members_schedule = schedule.get_members()
#         if normalize_members(members_pod) is in normalize_members(members_schedule):
#             prev_panel.extend(schedule.get_faculties_by_members())
#             print("prev_panel: ", prev_panel)
#             print("members_schedule: ", members_schedule)
#             print("members_pod: ", members_pod)
#             break
#         else:
#             print("did not match")
#             print("prev_panel: ", prev_panel)
#             print("members_schedule: ", members_schedule)
#             print("members_pod: ", members_pod)


#     # Step 2: Replace conflicting faculties while retaining original order
#     new_panel = []
#     for faculty in prev_panel:
#         faculty_id = faculty.id if hasattr(faculty, 'id') else faculty
#         if faculty_id in all_excluded_ids:
#             # Replace conflicting faculty
#             available_faculties = Faculty.objects.filter(is_active=True).exclude(
#                 id__in=all_excluded_ids | {f.id if hasattr(f, 'id') else f for f in new_panel}
#             )
#             sorted_faculties = sorted(available_faculties, key=lambda f: faculty_loads[f.id])
#             replacement = next(iter(sorted_faculties), None)
#             new_panel.append(replacement if replacement else None)
#         else:
#             # Retain non-conflicting faculty
#             new_panel.append(faculty)

#     # Step 3: Fill up gaps to ensure three members in the panel
#     if len(new_panel) < 3:
#         available_faculties = Faculty.objects.filter(is_active=True).exclude(
#             id__in=all_excluded_ids | {f.id if hasattr(f, 'id') else f for f in new_panel}
#         )
#         sorted_faculties = sorted(available_faculties, key=lambda f: faculty_loads[f.id])

#         for faculty in sorted_faculties:
#             if len(new_panel) < 3:
#                 new_panel.append(faculty)
#             else:
#                 break

#     # Ensure no gaps remain in the panel by replacing `None` with additional faculties if needed
#     new_panel = [f for f in new_panel if f]  # Remove any `None` entries
#     while len(new_panel) < 3:
#         available_faculty = Faculty.objects.filter(is_active=True).exclude(
#             id__in={f.id if hasattr(f, 'id') else f for f in new_panel}
#         ).first()
#         if available_faculty:
#             new_panel.append(available_faculty)
#         else:
#             break

#     # Step 4: Validate and finalize the panel with lead faculty criteria while retaining order
#     final_panel = validate_lead_faculty(new_panel[:3])  # Ensure exactly three members and validate the lead faculty

#     return final_panel

def remove_faculties(excluded_faculty1, excluded_faculty2, members_pod, faculty_bookings, day, slot, faculty_loads):
    """
    Selectively replaces conflicting faculties while retaining the original order as much as possible.
    Ensures the final panel includes a validated lead faculty, fills up with available faculties
    to reach three members, and integrates load balancing during selection.
    """
    current_school_year = SchoolYear.get_active_school_year()
    schedules = Schedule.objects.filter(school_year=current_school_year, has_been_rescheduled=False)
    prev_panel = []

    # Convert excluded_faculty1 and excluded_faculty2 to sets of IDs
    excluded_faculty1_ids = {fac.id if hasattr(fac, 'id') else fac for fac in excluded_faculty1}
    excluded_faculty2_ids = {fac.id if hasattr(fac, 'id') else fac for fac in excluded_faculty2}
    all_excluded_ids = excluded_faculty1_ids | excluded_faculty2_ids

    # Step 1: Identify the previous panel for the given members pod
    for schedule in schedules:
        members_schedule = schedule.get_members()
        pod_normalized = set(normalize_members(members_pod))
        schedule_normalized = set(normalize_members(members_schedule))

        if pod_normalized & schedule_normalized:  # Check if any record exists in both sets
            prev_panel.extend(schedule.get_faculties_by_members())
            # print("Match found:")
            # print("prev_panel:", prev_panel)
            # print("members_schedule:", members_schedule)
            # print("members_pod:", members_pod)
            break
        # else:
        #     print("No match found:")
        #     print("prev_panel:", prev_panel)
        #     print("members_schedule:", members_schedule)
        #     print("members_pod:", members_pod)

    # Step 2: Replace conflicting faculties while retaining original order
    new_panel = []
    for faculty in prev_panel:
        faculty_id = faculty.id if hasattr(faculty, 'id') else faculty
        if faculty_id in all_excluded_ids:
            # Replace conflicting faculty
            available_faculties = Faculty.objects.filter(is_active=True).exclude(
                id__in=all_excluded_ids | {f.id if hasattr(f, 'id') else f for f in new_panel}
            )
            sorted_faculties = sorted(available_faculties, key=lambda f: faculty_loads[f.id])
            replacement = next(iter(sorted_faculties), None)
            new_panel.append(replacement if replacement else None)
        else:
            # Retain non-conflicting faculty
            new_panel.append(faculty)

    # Step 3: Fill up gaps to ensure three members in the panel
    if len(new_panel) < 3:
        available_faculties = Faculty.objects.filter(is_active=True).exclude(
            id__in=all_excluded_ids | {f.id if hasattr(f, 'id') else f for f in new_panel}
        )
        sorted_faculties = sorted(available_faculties, key=lambda f: faculty_loads[f.id])

        for faculty in sorted_faculties:
            if len(new_panel) < 3:
                new_panel.append(faculty)
            else:
                break

    # Ensure no gaps remain in the panel by replacing `None` with additional faculties if needed
    new_panel = [f for f in new_panel if f]  # Remove any `None` entries
    while len(new_panel) < 3:
        available_faculty = Faculty.objects.filter(is_active=True).exclude(
            id__in={f.id if hasattr(f, 'id') else f for f in new_panel}
        ).first()
        if available_faculty:
            new_panel.append(available_faculty)
        else:
            break

    # Step 4: Validate and finalize the panel with lead faculty criteria while retaining order
    final_panel = validate_lead_faculty(new_panel[:3])  # Ensure exactly three members and validate the lead faculty

    return final_panel



def validate_lead_faculty(panel):
    """Ensure the lead faculty (first in list) has a master’s degree, highest years of teaching, or highest degree.
       Retain original order when criteria are equal."""
    if not panel:
        return panel

    # Create a mapping for highest degree to a numeric scale
    degree_order = {
        "Doctor of Philosophy (PhD)": 5,
        "Doctor of Education (EdD)": 5,
        "Specialist Degree (EdS)": 4,
        "Professional Doctorates": 4,
        "Master's": 3,
        "Bachelor's": 2,
        "None": 0  # Assuming "None" if no degree is provided
    }

    # Save the original order for fallback sorting
    indexed_panel = [(i, f) for i, f in enumerate(panel)]

    # Sort with fallback to original order
    indexed_panel.sort(key=lambda x: (
        not x[1].has_master_degree,  # Faculty with master's degree should come first
        -x[1].years_of_teaching,    # Faculty with highest teaching years next
        -degree_order.get(x[1].highest_degree, 0),  # Convert degree string to numeric value, default to 0 if not found
        x[0]                        # Retain original order in case of ties
    ))

    # Extract the sorted faculty members
    sorted_panel = [item[1] for item in indexed_panel]
    return sorted_panel


# def generate_schedulePOD(request, start_date):
#     try:
#         logger.info("Starting schedule generation...")

#         # current_school_year = SchoolYear.get_active_school_year()
#         selected_school_year_id = request.session.get('selected_school_year_id')
#         # get the last school year added to the db
#         last_school_year = SchoolYear.objects.all().order_by('-end_year').first()

#         # Get the selected school year from session or fallback to the active school year
#         selected_school_year = ''
#         if not selected_school_year_id:
#             selected_school_year = last_school_year
#             request.session['selected_school_year_id'] = selected_school_year.id  # Set in session
#         else:
#             # Retrieve the selected school year based on the session
#             selected_school_year = SchoolYear.objects.get(id=selected_school_year_id)

#         # Clear existing schedules
#         SchedulePOD.objects.filter(school_year=selected_school_year).delete()
#         logger.debug("Existing schedules cleared.")

#         groups = list(GroupInfoPOD.objects.filter(school_year=selected_school_year))
#         random.shuffle(groups)
#         logger.debug(f"Fetched {len(groups)} groups for scheduling.")
        
#         faculties = list(Faculty.objects.filter(is_active=True))
#         logger.debug(f"Loaded {len(faculties)} active faculties.")

#         # Initialize assignment tracking
#         faculty_loads = defaultdict(int)  # Track total assignments per faculty
#         daily_loads = defaultdict(lambda: defaultdict(int))  # Track daily loads to balance within each day
#         time_slots = ['8AM-9:30AM', '9:30AM-11AM', '12PM-01:30PM', '1:30PM-3PM', '3PM-4:30PM', '4:30PM-5PM', '5PM-6:30PM']
#         rooms = Room.objects.all().order_by("status")

#         assignments = []
#         faculty_bookings = defaultdict(lambda: defaultdict(set))  # faculty_id -> day -> slot
#         conflict_groups = deque(groups)

#         day_offset = 0
#         actual_day_counter = 0  # Track actual scheduling days

#         while conflict_groups:
#             # Calculate the current date
#             current_date = start_date + timedelta(days=day_offset)

#             # Skip weekends
#             if current_date.weekday() in (5, 6):  # Skip Saturday and Sunday
#                 day_offset += 1
#                 continue

#             # Adjust for Monday's first time slot skip
#             slots_to_schedule = time_slots if current_date.weekday() != 0 else time_slots[1:]

#             assigned_today = False

#             for slot in slots_to_schedule:
#                 for room in rooms:
#                     for _ in range(len(conflict_groups)):
#                         group = conflict_groups.popleft()
#                         excluded_faculty1 = {group.capstone_teacher}
#                         excluded_faculty2 = {group.adviser}
#                         members_pod = group.get_members()

#                         assigned_faculty = remove_faculties(
#                             excluded_faculty1, excluded_faculty2, members_pod, 
#                             faculty_bookings, current_date.strftime('%B %d, %Y'), slot, faculty_loads
#                         )

#                         # print("assigned_faculty: ", assigned_faculty)

#                         # Ensure at least one faculty has a master's degree
#                         if not any(faculty.has_master_degree for faculty in assigned_faculty):
#                             logger.warning(f"Group {group} cannot be assigned due to lack of master's degree.")
#                             conflict_groups.append(group)
#                             continue

#                         # Check for duplicate faculty assignments
#                         if len(set(f.id for f in assigned_faculty)) < 3:
#                             logger.warning(f"Group {group} cannot be assigned due to duplicate faculty assignments.")
#                             conflict_groups.append(group)
#                             continue

#                         # Check for double booking conflicts
#                         if any(slot in faculty_bookings[faculty.id][current_date.strftime('%B %d, %Y')] for faculty in assigned_faculty) or \
#                             slot in faculty_bookings[group.adviser.id][current_date.strftime('%B %d, %Y')] or \
#                             slot in faculty_bookings[group.capstone_teacher.id][current_date.strftime('%B %d, %Y')]:
#                             conflict_groups.append(group)
#                             continue

#                         # Assign the group if no conflicts
#                         for faculty in assigned_faculty:
#                             faculty_bookings[faculty.id][current_date.strftime('%B %d, %Y')].add(slot)
#                             faculty_loads[faculty.id] += 1  # Track total assignments
#                             daily_loads[current_date][faculty.id] += 1  # Track daily assignments
#                         faculty_bookings[group.adviser.id][current_date.strftime('%B %d, %Y')].add(slot)
#                         faculty_bookings[group.capstone_teacher.id][current_date.strftime('%B %d, %Y')].add(slot)

#                         assignments.append({
#                             'group': group,
#                             'title': group.title,
#                             'faculties': assigned_faculty,
#                             'slot': slot,
#                             'date': current_date.strftime('%B %d, %Y'),
#                             'room': room,
#                             'day_label': f"Day {actual_day_counter + 1}"  # Track actual day
#                         })

#                         logger.debug(f"Assignment created for group {group}: {assignments[-1]}")
#                         assigned_today = True
#                         break  # Move to the next room after successful assignment

#                 if len(assignments) >= len(groups):
#                     break  # Break outer loop if all groups are assigned

#             # Only increment the actual day counter if there were assignments
#             if assigned_today:
#                 actual_day_counter += 1

#             # If still conflict groups exist, we need to move to the next day
#             if conflict_groups:
#                 day_offset += 1
#             else:
#                 break  # Break if all groups are successfully scheduled

#         # Save assignments to the database in a transaction
#         with transaction.atomic():
#             logger.info("Starting transaction to save schedules.")
#             SchedulePOD.objects.bulk_create([
#                 SchedulePOD(
#                     group=assignment['group'],
#                     title=assignment['title'],
#                     faculty1=assignment['faculties'][0],
#                     faculty2=assignment['faculties'][1],
#                     faculty3=assignment['faculties'][2],
#                     slot=assignment['slot'],
#                     date=assignment['date'],
#                     room=assignment['room'],
#                     adviser=assignment['group'].adviser,
#                     capstone_teacher=assignment['group'].capstone_teacher,
#                     day=assignment['day_label'],
#                     school_year=selected_school_year
#                 )
#                 for assignment in assignments
#             ])
#             logger.info("Transaction completed successfully.")
#             # print("Scheduling completed successfully.")

#     except Exception as e:
#         logger.error(f"An error occurred: {e}")
#         print(f"An error occurred: {e}")

def generate_schedulePOD(request, start_date):
    try:
        logger.info("Starting schedule generation with panel/adviser constraints...")

        # Get selected school year or fallback
        selected_school_year = None
        if 'selected_school_year_id' in request.session:
            try:
                selected_school_year = SchoolYear.objects.get(id=request.session['selected_school_year_id'])
            except SchoolYear.DoesNotExist:
                pass

        if not selected_school_year:
            selected_school_year = SchoolYear.get_active_school_year()
            if selected_school_year:
                request.session['selected_school_year_id'] = selected_school_year.id

        if not selected_school_year:
            raise ValueError("No active school year found")

        # Clear previous schedules
        SchedulePOD.objects.filter(school_year=selected_school_year).delete()

        groups = list(GroupInfoPOD.objects.filter(school_year=selected_school_year))
        if not groups:
            raise ValueError("No groups found to schedule")

        random.shuffle(groups)
        faculties = list(Faculty.objects.filter(is_active=True))
        rooms = list(Room.objects.all().order_by("status"))
        time_slots = ['8AM-9:30AM', '9:30AM-11AM', '12PM-01:30PM', '1:30PM-3PM', '3PM-4:30PM', '4:30PM-5PM', '5PM-6:30PM']

        # Tracking
        faculty_bookings = defaultdict(lambda: defaultdict(set))  # faculty_id -> date -> set of slots
        faculty_daily_roles = defaultdict(lambda: defaultdict(lambda: {
            'panel': 0,
            'adviser': 0,
            'total': 0
        }))
        faculty_loads = defaultdict(int)  # For load balancing
        assignments = []
        conflict_groups = deque(groups)

        day_offset = 0
        actual_day_counter = 0

        def is_faculty_eligible(faculty, date_str, slot, role):
            day_data = faculty_daily_roles[faculty.id][date_str]
            if day_data['total'] >= 3:
                return False
            if role == 'panel' and day_data['panel'] >= 3:
                return False
            if slot in faculty_bookings[faculty.id][date_str]:
                return False
            return True

        def is_morning_slot(slot):
            return any(am in slot for am in ['8AM', '9:30AM', '11AM'])

        while conflict_groups and day_offset < 30:
            current_date = start_date + timedelta(days=day_offset)
            if current_date.weekday() in (5, 6):  # Skip weekends
                day_offset += 1
                continue

            date_str = current_date.strftime('%B %d, %Y')
            slots_today = time_slots[1:] if current_date.weekday() == 0 else time_slots
            assigned_today = False

            for slot in slots_today:
                for room in rooms:
                    attempts = len(conflict_groups)
                    while attempts > 0:
                        attempts -= 1
                        group = conflict_groups.popleft()

                        # Adviser & Capstone Teacher must be available
                        if not is_faculty_eligible(group.adviser, date_str, slot, 'adviser') or \
                           not is_faculty_eligible(group.capstone_teacher, date_str, slot, 'adviser'):
                            conflict_groups.append(group)
                            continue

                        # Exclude advisers and capstone teacher from panel list
                        excluded_ids = {group.adviser.id, group.capstone_teacher.id}
                        available_panelists = [
                            f for f in faculties
                            if f.id not in excluded_ids and
                            is_faculty_eligible(f, date_str, slot, 'panel')
                        ]

                        # Sort to balance faculty loads
                        available_panelists.sort(key=lambda f: faculty_loads[f.id])

                        # Select 3 eligible panelists, with at least one master's degree holder
                        selected_panel = []
                        for f in available_panelists:
                            if len(selected_panel) < 3:
                                selected_panel.append(f)
                            if any(p.has_master_degree for p in selected_panel) and len(selected_panel) == 3:
                                break

                        if len(selected_panel) < 3 or not any(f.has_master_degree for f in selected_panel):
                            conflict_groups.append(group)
                            continue

                        # Update bookings and role tracking
                        for f in selected_panel:
                            faculty_bookings[f.id][date_str].add(slot)
                            faculty_loads[f.id] += 1
                            faculty_daily_roles[f.id][date_str]['panel'] += 1
                            faculty_daily_roles[f.id][date_str]['total'] += 1

                        for adviser in [group.adviser, group.capstone_teacher]:
                            faculty_bookings[adviser.id][date_str].add(slot)
                            faculty_daily_roles[adviser.id][date_str]['adviser'] += 1
                            faculty_daily_roles[adviser.id][date_str]['total'] += 1

                        assignments.append({
                            'group': group,
                            'title': group.title,
                            'faculties': selected_panel,
                            'slot': slot,
                            'date': date_str,
                            'room': room,
                            'day_label': f"Day {actual_day_counter + 1}",
                            'adviser': group.adviser,
                            'capstone_teacher': group.capstone_teacher
                        })

                        assigned_today = True
                        break  # Room is occupied in this slot

            if assigned_today:
                actual_day_counter += 1
            day_offset += 1

        # Save all generated schedules
        if assignments:
            with transaction.atomic():
                SchedulePOD.objects.bulk_create([
                    SchedulePOD(
                        group=a['group'],
                        title=a['title'],
                        faculty1=a['faculties'][0],
                        faculty2=a['faculties'][1],
                        faculty3=a['faculties'][2],
                        slot=a['slot'],
                        date=a['date'],
                        room=a['room'],
                        adviser=a['adviser'],
                        capstone_teacher=a['capstone_teacher'],
                        day=a['day_label'],
                        school_year=selected_school_year
                    ) for a in assignments
                ])
                logger.info(f"Successfully created {len(assignments)} schedules.")
                return True
        else:
            logger.warning("No schedules were created.")
            return False

    except Exception as e:
        logger.error(f"Scheduling failed: {str(e)}", exc_info=True)
        messages.error(request, f"Scheduling failed: {str(e)}")
        return False     

def get_faculty_assignmentsPOD():
    """Retrieve a summary of faculty assignments, sorted by teaching experience."""
    faculty_assignments = {faculty.id: 0 for faculty in Faculty.objects.all()}

    current_school_year = SchoolYear.get_active_school_year()
    # selected_school_year_id = request.session.get('selected_school_year_id')
    # # get the last school year added to the db
    # last_school_year = SchoolYear.objects.all().order_by('-end_year').first()

    # # Get the selected school year from session or fallback to the active school year
    # selected_school_year = ''
    # if not selected_school_year_id:
    #     selected_school_year = last_school_year
    #     request.session['selected_school_year_id'] = selected_school_year.id  # Set in session
    # else:
    #     # Retrieve the selected school year based on the session
    #     selected_school_year = SchoolYear.objects.get(id=selected_school_year_id)

    schedules = SchedulePOD.objects.filter(school_year=current_school_year)

    for schedule in schedules:
        for faculty_id in [schedule.faculty1.id, schedule.faculty2.id, schedule.faculty3.id]:
            faculty_assignments[faculty_id] += 1

    faculty_list = []
    for faculty in Faculty.objects.all():
        faculty_list.append({
            'faculty_id': faculty.id,
            'name': faculty.name,
            'years': faculty.years_of_teaching,
            'assignments': faculty_assignments.get(faculty.id, 0)
        })

    faculty_list.sort(key=lambda x: x['years'], reverse=True)

    return faculty_list


# import logging
# import random
# from collections import defaultdict, deque
# from django.shortcuts import render, redirect
# from django.contrib import messages
# from django.db import transaction
# from .models import GroupInfoPOD, Faculty, SchedulePOD, Schedule, Room
# from datetime import datetime, timedelta
# from users.models import SchoolYear

# # Set up logging
# logger = logging.getLogger(__name__)

# def normalize_members(members):
#     """Normalize member names for comparison."""
#     return sorted([member.strip().lower() for member in members if member])

# def remove_faculties(excluded_faculty1, excluded_faculty2, members_pod, faculty_bookings, day, slot):
#     """Select faculties for the given group, avoiding those in the exclusion lists."""
#     prev_panel = []
#     current_school_year = SchoolYear.get_active_school_year()  # Ensure you're getting the active year

#     # Fetch existing schedules to check for previous panel assignments
#     schedules = Schedule.objects.filter(school_year=current_school_year, has_been_rescheduled=False)

#     for schedule in schedules:
#         members_schedule = schedule.get_members()
#         if normalize_members(members_pod) == normalize_members(members_schedule):
#             prev_panel.extend(schedule.get_faculties_by_members())
#             # Remove excluded faculties from the previous panel
#             prev_panel = [faculty for faculty in prev_panel if faculty not in excluded_faculty1 and faculty not in excluded_faculty2]
#             if len(set(prev_panel)) >= 3:  # Ensure uniqueness
#                 prev_panel = list(set(prev_panel))  # Remove duplicates
#                 return prev_panel[:3]

#     # If not enough faculties, fill up with new ones
#     faculty_cycle = deque(Faculty.objects.filter(is_active=True).order_by('-years_of_teaching'))  # Create a cycle from active faculties
#     while len(prev_panel) < 3:
#         faculty = faculty_cycle.popleft()
#         # Avoid conflict: skip if the faculty is already assigned as an adviser or panel member in the same slot/day
#         if (faculty.id not in faculty_bookings or slot not in faculty_bookings[faculty.id][day]) and faculty not in excluded_faculty1 and faculty not in excluded_faculty2:
#             if faculty not in prev_panel:
#                 prev_panel.append(faculty)
#         faculty_cycle.append(faculty)

#     prev_panel = list(set(prev_panel))  # Remove duplicates
#     return prev_panel[:3]

# def generate_schedulePOD(start_date):
#     try:
#         logger.info("Starting schedule generation...")

#         current_school_year = SchoolYear.get_active_school_year()

#         # Clear existing schedules
#         SchedulePOD.objects.filter(school_year=current_school_year).delete()
#         logger.debug("Existing schedules cleared.")

#         groups = list(GroupInfoPOD.objects.filter(school_year=current_school_year))
#         random.shuffle(groups)
#         logger.debug(f"Fetched {len(groups)} groups for scheduling.")
        
#         faculties = list(Faculty.objects.filter(is_active=True))
#         faculties.sort(key=lambda f: -f.years_of_teaching)
#         logger.debug(f"Sorted faculties by experience.")

#         # Initialize assignment tracking
#         faculty_assignments = defaultdict(int)
#         time_slots = ['8AM-9:30AM', '9:30AM-11AM', '12PM-01:30PM', '1:30PM-3PM', '3PM-4:30PM', '4:30PM-5PM', '5PM-6:30PM']
#         rooms = Room.objects.all().order_by("status")

#         # Prepare for scheduling
#         assignments = []
#         max_retries = 3 
#         faculty_bookings = defaultdict(lambda: defaultdict(set))  # faculty_id -> day -> slot
#         conflict_groups = deque(groups)  # Start with all groups as potential conflicts

#         # Day increment
#         # Day increment
#         day_offset = 0
#         actual_day_counter = 0  # Track actual scheduling days

#         while conflict_groups:
#             # Calculate the current date
#             current_date = start_date + timedelta(days=day_offset)

#             # Skip weekends
#             if current_date.weekday() == 5:  # Saturday
#                 day_offset += 1
#                 continue
#             if current_date.weekday() == 6:  # Sunday
#                 day_offset += 1
#                 continue

#             # Adjust for Monday's first time slot skip
#             slots_to_schedule = time_slots if current_date.weekday() != 0 else time_slots[1:]

#             # Track if any groups are assigned on this day
#             assigned_today = False

#             # Iterate through the time slots
#             for slot in slots_to_schedule:
#                 for room in rooms:
#                     # Process each group
#                     for _ in range(len(conflict_groups)):
#                         group = conflict_groups.popleft()
#                         excluded_faculty1 = {group.capstone_teacher}
#                         excluded_faculty2 = {group.adviser}
#                         members_pod = group.get_members()

#                         assigned_faculty = remove_faculties(excluded_faculty1, excluded_faculty2, members_pod, faculty_bookings, current_date.strftime('%B %d, %Y'), slot)

#                         # Check for master's degree and double booking
#                         if not any(faculty.has_master_degree for faculty in assigned_faculty):
#                             logger.warning(f"Group {group} cannot be assigned because no faculty has a master's degree.")
#                             conflict_groups.append(group)  # Re-add group to conflicts
#                             continue

#                         if any(slot in faculty_bookings[faculty.id][current_date.strftime('%B %d, %Y')] for faculty in assigned_faculty) or \
#                         slot in faculty_bookings[group.adviser.id][current_date.strftime('%B %d, %Y')] or \
#                         slot in faculty_bookings[group.capstone_teacher.id][current_date.strftime('%B %d, %Y')]:
#                             conflict_groups.append(group)  # Re-add group to conflicts
#                             continue

#                         # Assign the group if no conflicts
#                         for faculty in assigned_faculty:
#                             faculty_bookings[faculty.id][current_date.strftime('%B %d, %Y')].add(slot)
#                             faculty_assignments[faculty.id] += 1
#                         faculty_bookings[group.adviser.id][current_date.strftime('%B %d, %Y')].add(slot)
#                         faculty_bookings[group.capstone_teacher.id][current_date.strftime('%B %d, %Y')].add(slot)

#                         assignments.append({
#                             'group': group,
#                             'title': group.title,
#                             'faculties': assigned_faculty,
#                             'slot': slot,
#                             'date': current_date.strftime('%B %d, %Y'),
#                             'room': room,
#                             'day_label': f"Day {actual_day_counter + 1}"  # Track actual day
#                         })

#                         logger.debug(f"Assignment created for group {group}: {assignments[-1]}")
#                         assigned_today = True  # Mark that we have assigned today
#                         break  # Move to the next room after successful assignment

#                 if len(assignments) >= len(groups):
#                     break  # Break outer loop if all groups are assigned

#             # Only increment the actual day counter if there were assignments
#             if assigned_today:
#                 actual_day_counter += 1

#             # If still conflict groups exist, we need to move to the next day
#             if conflict_groups:
#                 day_offset += 1
#             else:
#                 break  # Break if all groups are successfully scheduled

#         # Handle saving assignments to the database
#         with transaction.atomic():
#             logger.info("Starting transaction to save schedules.")
#             for assignment in assignments:
#                 SchedulePOD.objects.create(
#                     group=assignment['group'],
#                     title=assignment['title'],
#                     faculty1=assignment['faculties'][0],
#                     faculty2=assignment['faculties'][1],
#                     faculty3=assignment['faculties'][2],
#                     slot=assignment['slot'],
#                     date=assignment['date'],
#                     room=assignment['room'],
#                     adviser=assignment['group'].adviser,
#                     capstone_teacher=assignment['group'].capstone_teacher,
#                     day=assignment['day_label'],
#                     school_year=current_school_year
#                 )
#             logger.info("Transaction completed successfully.")
#             print("Scheduling completed successfully.")

#     except Exception as e:
#         logger.error(f"An error occurred: {e}")
#         print(f"An error occurred: {e}")


# def get_faculty_assignmentsPOD():
#     # Initialize a dictionary to hold faculty assignments
#     faculty_assignments = {faculty.id: 0 for faculty in Faculty.objects.all()}

#     # Count the number of groups each faculty is assigned as a panel member
#     current_school_year = SchoolYear.get_active_school_year()
#     schedules = SchedulePOD.objects.filter(school_year=current_school_year)
#     for schedule in schedules:
#         for faculty_id in [schedule.faculty1.id, schedule.faculty2.id, schedule.faculty3.id]:
#             faculty_assignments[faculty_id] += 1

#     # Create a list of faculty with their respective number of assignments
#     faculty_list = []
#     for faculty in Faculty.objects.all():
#         faculty_list.append({
#             'faculty_id': faculty.id,
#             'name': faculty.name,
#             'years': faculty.years_of_teaching,
#             'assignments': faculty_assignments.get(faculty.id, 0)
#         })

#     # Sort the list by years_of_teaching in descending order
#     faculty_list.sort(key=lambda x: x['years'], reverse=True)

#     return faculty_list








# # import logging
# # import random
# # import time
# # from collections import defaultdict, deque
# # from django.shortcuts import render, redirect
# # from django.contrib import messages
# # from django.db import transaction
# # from .models import GroupInfoPOD, Faculty, SchedulePOD, Schedule, Room
# # from datetime import datetime, timedelta
# # from users.models import SchoolYear

# # # Set up logging
# # logger = logging.getLogger(__name__)

# # def normalize_members(members):
# #     """Normalize member names for comparison."""
# #     return sorted([member.strip().lower() for member in members if member])

# # def remove_faculties(excluded_faculty1, excluded_faculty2, members_pod, faculty_bookings, day, slot, faculty_cache):
# #     """Select faculties for the given group, avoiding those in the exclusion lists."""
# #     prev_panel = []
# #     current_school_year = SchoolYear.get_active_school_year()

# #     # Fetch existing schedules once
# #     schedules = faculty_cache['schedules']

# #     for schedule in schedules:
# #         members_schedule = schedule.get_members()
# #         if normalize_members(members_pod) == normalize_members(members_schedule):
# #             prev_panel.extend(schedule.get_faculties_by_members())
# #             prev_panel = [faculty for faculty in prev_panel if faculty not in excluded_faculty1 and faculty not in excluded_faculty2]
# #             if len(set(prev_panel)) >= 3:
# #                 return list(set(prev_panel))[:3]

# #     # If not enough faculties, fill up with new ones
# #     faculty_cycle = deque(faculty_cache['faculties'])  # Use cached faculties
# #     while len(prev_panel) < 3:
# #         faculty = faculty_cycle.popleft()
# #         if (faculty.id not in faculty_bookings or slot not in faculty_bookings[faculty.id][day]) and \
# #             faculty not in excluded_faculty1 and faculty not in excluded_faculty2:
# #             if faculty not in prev_panel:
# #                 prev_panel.append(faculty)
# #         faculty_cycle.append(faculty)

# #     return list(set(prev_panel))[:3]

# # def generate_schedulePOD(start_date):
# #     try:
# #         logger.info("Starting schedule generation...")

# #         current_school_year = SchoolYear.get_active_school_year()

# #         # Clear existing schedules
# #         SchedulePOD.objects.filter(school_year=current_school_year).delete()
# #         logger.debug("Existing schedules cleared.")

# #         groups = list(GroupInfoPOD.objects.filter(school_year=current_school_year))
# #         random.shuffle(groups)
# #         logger.debug(f"Fetched {len(groups)} groups for scheduling.")
        
# #         faculties = list(Faculty.objects.filter(is_active=True).select_related())
# #         faculties.sort(key=lambda f: -f.years_of_teaching)
# #         logger.debug(f"Sorted faculties by experience.")

# #         rooms = list(Room.objects.all().order_by("status"))
# #         logger.debug(f"Loaded {len(rooms)} rooms.")

# #         faculty_assignments = defaultdict(int)
# #         time_slots = ['8AM-9:30AM', '9:30AM-11AM', '12PM-01:30PM', '1:30PM-3PM', '3PM-4:30PM', '4:30PM-5PM', '5PM-6:30PM']

# #         faculty_bookings = defaultdict(lambda: defaultdict(set))  # faculty_id -> day -> slot
# #         conflict_groups = deque(groups)  # Start with all groups as potential conflicts

# #         day_offset = 0
# #         actual_day_counter = 0

# #         # Faculty Cache
# #         faculty_cache = {
# #             'faculties': faculties,
# #             'schedules': list(Schedule.objects.filter(school_year=current_school_year, has_been_rescheduled=False))
# #         }

# #         # Start scheduling
# #         assignments = []
# #         while conflict_groups:
# #             current_date = start_date + timedelta(days=day_offset)

# #             # Skip weekends
# #             if current_date.weekday() in [5, 6]:  # Skip Saturday and Sunday
# #                 day_offset += 1
# #                 continue

# #             # Adjust for Monday's first time slot skip
# #             slots_to_schedule = time_slots if current_date.weekday() != 0 else time_slots[1:]

# #             assigned_today = False

# #             for slot in slots_to_schedule:
# #                 for room in rooms:
# #                     for _ in range(len(conflict_groups)):
# #                         group = conflict_groups.popleft()
# #                         excluded_faculty1 = {group.capstone_teacher}
# #                         excluded_faculty2 = {group.adviser}
# #                         members_pod = group.get_members()

# #                         assigned_faculty = remove_faculties(excluded_faculty1, excluded_faculty2, members_pod, faculty_bookings, current_date.strftime('%B %d, %Y'), slot, faculty_cache)

# #                         if not any(faculty.has_master_degree for faculty in assigned_faculty):
# #                             logger.warning(f"Group {group} cannot be assigned because no faculty has a master's degree.")
# #                             conflict_groups.append(group)
# #                             continue

# #                         if any(slot in faculty_bookings[faculty.id][current_date.strftime('%B %d, %Y')] for faculty in assigned_faculty) or \
# #                         slot in faculty_bookings[group.adviser.id][current_date.strftime('%B %d, %Y')] or \
# #                         slot in faculty_bookings[group.capstone_teacher.id][current_date.strftime('%B %d, %Y')]:
# #                             conflict_groups.append(group)
# #                             continue

# #                         for faculty in assigned_faculty:
# #                             faculty_bookings[faculty.id][current_date.strftime('%B %d, %Y')].add(slot)
# #                             faculty_assignments[faculty.id] += 1
# #                         faculty_bookings[group.adviser.id][current_date.strftime('%B %d, %Y')].add(slot)
# #                         faculty_bookings[group.capstone_teacher.id][current_date.strftime('%B %d, %Y')].add(slot)

# #                         assignments.append({
# #                             'group': group,
# #                             'title': group.title,
# #                             'faculties': assigned_faculty,
# #                             'slot': slot,
# #                             'date': current_date.strftime('%B %d, %Y'),
# #                             'room': room,
# #                             'day_label': f"Day {actual_day_counter + 1}"
# #                         })

# #                         logger.debug(f"Assignment created for group {group}: {assignments[-1]}")
# #                         assigned_today = True
# #                         break

# #                 if len(assignments) >= len(groups):
# #                     break

# #             if assigned_today:
# #                 actual_day_counter += 1

# #             if conflict_groups:
# #                 day_offset += 1
# #             else:
# #                 break

# #         # Bulk insert to database
# #         with transaction.atomic():
# #             logger.info("Starting bulk insert of schedules.")
# #             SchedulePOD.objects.bulk_create([
# #                 SchedulePOD(
# #                     group=assignment['group'],
# #                     title=assignment['title'],
# #                     faculty1=assignment['faculties'][0],
# #                     faculty2=assignment['faculties'][1],
# #                     faculty3=assignment['faculties'][2],
# #                     slot=assignment['slot'],
# #                     date=assignment['date'],
# #                     room=assignment['room'],
# #                     adviser=assignment['group'].adviser,
# #                     capstone_teacher=assignment['group'].capstone_teacher,
# #                     day=assignment['day_label'],
# #                     school_year=current_school_year
# #                 )
# #                 for assignment in assignments
# #             ])
# #             logger.info("Bulk insert completed successfully.")
# #             print("Scheduling completed successfully.")

# #     except Exception as e:
# #         logger.error(f"An error occurred: {e}")
# #         print(f"An error occurred: {e}")


# # def get_faculty_assignmentsPOD():
# #     faculty_assignments = {faculty.id: 0 for faculty in Faculty.objects.all()}

# #     current_school_year = SchoolYear.get_active_school_year()
# #     schedules = SchedulePOD.objects.filter(school_year=current_school_year)

# #     for schedule in schedules:
# #         for faculty_id in [schedule.faculty1.id, schedule.faculty2.id, schedule.faculty3.id]:
# #             faculty_assignments[faculty_id] += 1

# #     faculty_list = []
# #     for faculty in Faculty.objects.all():
# #         faculty_list.append({
# #             'faculty_id': faculty.id,
# #             'name': faculty.name,
# #             'years': faculty.years_of_teaching,
# #             'assignments': faculty_assignments.get(faculty.id, 0)
# #         })

# #     faculty_list.sort(key=lambda x: x['years'], reverse=True)

# #     return faculty_list

