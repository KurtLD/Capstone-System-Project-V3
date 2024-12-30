import logging
import random
from collections import defaultdict, deque
from django.shortcuts import render, redirect
from django.contrib import messages
from django.db import transaction
from .models import GroupInfoPOD, Faculty, SchedulePOD, Schedule, ScheduleMD, GroupInfoMD, Room
from datetime import datetime, timedelta
from users.models import SchoolYear

# Set up logging
logger = logging.getLogger(__name__)




def normalize_members(members):
    """Normalize member names for comparison."""
    return sorted([member.strip().lower() for member in members if member])

def remove_faculties(excluded_faculty1, excluded_faculty2, members_pod, faculty_bookings, day, slot, faculty_loads):
    """Select faculties for the given group, ensuring consistent panel arrangement."""
    prev_panel = []
    current_school_year = SchoolYear.get_active_school_year()

    # Fetch existing schedules to check for previous panel assignments
    schedules = SchedulePOD.objects.filter(school_year=current_school_year, has_been_rescheduled=False)

    for schedule in schedules:
        members_schedule = schedule.get_members()
        if normalize_members(members_pod) == normalize_members(members_schedule):
            prev_panel.extend(schedule.get_faculties_by_members())
            # Remove excluded faculties from the previous panel
            prev_panel = [
                faculty for faculty in prev_panel 
                if faculty not in excluded_faculty1 and faculty not in excluded_faculty2
            ]
            if len(set(prev_panel)) >= 3:  # Ensure uniqueness
                # Return the previous panel in its original order
                return prev_panel[:3]

    # If not enough faculties, fill up with new ones while balancing load
    available_faculties = Faculty.objects.filter(is_active=True).exclude(
        id__in=[fac.id for fac in excluded_faculty1 | excluded_faculty2]
    )
    sorted_faculties = sorted(available_faculties, key=lambda f: faculty_loads[f.id])

    for faculty in sorted_faculties:
        # Skip if faculty already has an assignment in the same slot/day
        if (faculty.id not in faculty_bookings or slot not in faculty_bookings[faculty.id][day]):
            prev_panel.append(faculty)
            if len(prev_panel) >= 3:
                break

    # Reorder new panel to ensure the lead panelist is properly assigned
    return reorder_faculty_panel(list(set(prev_panel))[:3])

def reorder_faculty_panel(faculties):
    """Ensure the first faculty in the list is the lead, defined as having the highest qualifications."""
    faculties.sort(
        key=lambda f: (
            f.has_master_degree, 
            f.highest_degree, 
            f.years_of_teaching
        ), 
        reverse=True
    )
    return faculties[:3]



def generate_scheduleMD(request, start_date):
    try:
        logger.info("Starting schedule generation...")

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

        # Clear existing schedules
        ScheduleMD.objects.filter(school_year=selected_school_year).delete()
        logger.debug("Existing schedules cleared.")

        groups = list(GroupInfoMD.objects.filter(school_year=selected_school_year))
        random.shuffle(groups)
        logger.debug(f"Fetched {len(groups)} groups for scheduling.")
        
        faculties = list(Faculty.objects.filter(is_active=True))
        logger.debug(f"Loaded {len(faculties)} active faculties.")

        # Initialize assignment tracking
        faculty_loads = defaultdict(int)  # Track total assignments per faculty
        daily_loads = defaultdict(lambda: defaultdict(int))  # Track daily loads to balance within each day
        time_slots = ['8AM-9:30AM', '9:30AM-11AM', '12PM-01:30PM', '1:30PM-3PM', '3PM-4:30PM', '4:30PM-5PM', '5PM-6:30PM']
        rooms = Room.objects.all().order_by("status")

        assignments = []
        faculty_bookings = defaultdict(lambda: defaultdict(set))  # faculty_id -> day -> slot
        conflict_groups = deque(groups)

        day_offset = 0
        actual_day_counter = 0  # Track actual scheduling days

        while conflict_groups:
            # Calculate the current date
            current_date = start_date + timedelta(days=day_offset)

            # Skip weekends
            if current_date.weekday() in (5, 6):  # Skip Saturday and Sunday
                day_offset += 1
                continue

            # Adjust for Monday's first time slot skip
            slots_to_schedule = time_slots if current_date.weekday() != 0 else time_slots[1:]

            assigned_today = False

            for slot in slots_to_schedule:
                for room in rooms:
                    for _ in range(len(conflict_groups)):
                        group = conflict_groups.popleft()
                        excluded_faculty1 = {group.capstone_teacher}
                        excluded_faculty2 = {group.adviser}
                        members_pod = group.get_members()

                        assigned_faculty = remove_faculties(
                            excluded_faculty1, excluded_faculty2, members_pod, 
                            faculty_bookings, current_date.strftime('%B %d, %Y'), slot, faculty_loads
                        )

                        # Ensure at least one faculty has a master's degree
                        if not any(faculty.has_master_degree for faculty in assigned_faculty):
                            logger.warning(f"Group {group} cannot be assigned due to lack of master's degree.")
                            conflict_groups.append(group)
                            continue

                        # Check for double booking conflicts
                        if any(slot in faculty_bookings[faculty.id][current_date.strftime('%B %d, %Y')] for faculty in assigned_faculty) or \
                            slot in faculty_bookings[group.adviser.id][current_date.strftime('%B %d, %Y')] or \
                            slot in faculty_bookings[group.capstone_teacher.id][current_date.strftime('%B %d, %Y')]:
                            conflict_groups.append(group)
                            continue

                        # Assign the group if no conflicts
                        for faculty in assigned_faculty:
                            faculty_bookings[faculty.id][current_date.strftime('%B %d, %Y')].add(slot)
                            faculty_loads[faculty.id] += 1  # Track total assignments
                            daily_loads[current_date][faculty.id] += 1  # Track daily assignments
                        faculty_bookings[group.adviser.id][current_date.strftime('%B %d, %Y')].add(slot)
                        faculty_bookings[group.capstone_teacher.id][current_date.strftime('%B %d, %Y')].add(slot)

                        assignments.append({
                            'group': group,
                            'title': group.title,
                            'faculties': assigned_faculty,
                            'slot': slot,
                            'date': current_date.strftime('%B %d, %Y'),
                            'room': room,
                            'day_label': f"Day {actual_day_counter + 1}"  # Track actual day
                        })

                        logger.debug(f"Assignment created for group {group}: {assignments[-1]}")
                        assigned_today = True
                        break  # Move to the next room after successful assignment

                if len(assignments) >= len(groups):
                    break  # Break outer loop if all groups are assigned

            # Only increment the actual day counter if there were assignments
            if assigned_today:
                actual_day_counter += 1

            # If still conflict groups exist, we need to move to the next day
            if conflict_groups:
                day_offset += 1
            else:
                break  # Break if all groups are successfully scheduled

        # Save assignments to the database in a transaction
        with transaction.atomic():
            logger.info("Starting transaction to save schedules.")
            ScheduleMD.objects.bulk_create([
                ScheduleMD(
                    group=assignment['group'],
                    title=assignment['title'],
                    faculty1=assignment['faculties'][0],
                    faculty2=assignment['faculties'][1],
                    faculty3=assignment['faculties'][2],
                    slot=assignment['slot'],
                    date=assignment['date'],
                    room=assignment['room'],
                    adviser=assignment['group'].adviser,
                    capstone_teacher=assignment['group'].capstone_teacher,
                    day=assignment['day_label'],
                    school_year=selected_school_year
                )
                for assignment in assignments
            ])
            logger.info("Transaction completed successfully.")
            print("Scheduling completed successfully.")

    except Exception as e:
        logger.error(f"An error occurred: {e}")
        print(f"An error occurred: {e}")

def get_faculty_assignmentsMD():
    """Retrieve a summary of faculty assignments, sorted by teaching experience."""
    faculty_assignments = {faculty.id: 0 for faculty in Faculty.objects.all()}

    current_school_year = SchoolYear.get_active_school_year()
    schedules = ScheduleMD.objects.filter(school_year=current_school_year)

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
