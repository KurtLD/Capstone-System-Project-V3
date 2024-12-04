import random
from .models import GroupInfoTH, Faculty, Schedule, Room
from collections import defaultdict, deque
from django.db import transaction
from datetime import datetime, timedelta
import logging
from users.models import SchoolYear

# Initialize logger
logger = logging.getLogger(__name__)

def generate_schedule(request, start_date=None):
    if start_date is None:
        raise ValueError("Start date must be provided")

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
    Schedule.objects.filter(school_year=selected_school_year).delete()

    groups = list(GroupInfoTH.objects.filter(school_year=selected_school_year))
    random.shuffle(groups)
    faculties = list(Faculty.objects.filter(is_active=True))

    # Sort faculties based on years of teaching (most experienced first)
    faculties.sort(key=lambda f: -f.years_of_teaching)

    # Initialize assignment tracking
    faculty_assignments = defaultdict(int)

    base_time_slots = ["8AM-9AM", "9AM-10AM", "10AM-11AM", "11AM-12PM", "1PM-2PM", "2PM-3PM", "3PM-4PM", "4PM-5PM"]
    rooms = Room.objects.all().order_by("status")

    total_slots_per_room_per_day = len(base_time_slots)
    total_rooms = len(rooms)
    total_slots_per_day = total_slots_per_room_per_day * total_rooms
    total_days_needed = (len(groups) + total_slots_per_day - 1) // total_slots_per_day
    print("total_days_needed: ", total_days_needed)

    # Initialize a list for scheduling days, excluding weekends
    days = []
    current_date = start_date

    # Generate valid weekdays for scheduling
    while len(days) < total_days_needed:
        if current_date.weekday() < 5:  # Only add weekdays (0-4)
            days.append(current_date.strftime('%B %d, %Y'))
        current_date += timedelta(days=1)  # Increment to the next day

    # Initialize round-robin iterator for faculties
    faculty_cycle = deque(faculties)

    # Track assigned time slots for each faculty per day
    faculty_time_slots = defaultdict(lambda: defaultdict(set))

    # Track used time slots for each room per day
    room_time_slot_usage = defaultdict(lambda: defaultdict(set))

    def get_next_faculties(day, slot):
        result = []
        while len(result) < 3 and faculty_cycle:
            faculty = faculty_cycle.popleft()
            if slot not in faculty_time_slots[faculty.id][day]:
                result.append(faculty)
                faculty_time_slots[faculty.id][day].add(slot)  # Track assigned slot for this faculty on this day
            faculty_cycle.append(faculty)  # Rotate faculty back to the end of the deque
        if len(result) < 3:
            return None  # Return None if not enough faculties are available for the panel
        return result

    # Track the assignment of faculties to ensure balanced distribution
    assignments = []
    schedule_index = 0
    day_counter = 1  # Initialize day counter

    for group in groups:
        print("schedule_index: ", schedule_index)
        print("total_slots_per_day: ", total_slots_per_day)
        print("day_counter: ", day_counter)
        
        if schedule_index % total_slots_per_day == 0 and schedule_index != 0:
            day_counter += 1  # Increment day counter after filling all slots of the day
        
        day_index = schedule_index // total_slots_per_day  # Calculate correct day index
        print("day index: ", day_index)
        day = datetime.strptime(days[day_index], '%B %d, %Y')
        formatted_day = day.strftime('%B %d, %Y')
        print("formatted day: ", formatted_day)

        # Adjust time slots based on whether the day is Monday
        current_date = day
        print("current date: ", current_date)
        current_day_of_week = current_date.strftime('%A')  # Get day name, e.g., "Monday"

        # Adjust time slots for Monday to exclude the first slot
        if current_day_of_week == "Monday":
            time_slots = base_time_slots[1:]  # Exclude "8AM-9AM" on Monday
        else:
            time_slots = base_time_slots  # Use full time slots for other days

        print("current_day_of_week: ", current_day_of_week)
        print("time_slots: ", time_slots)

        # Calculate room and slot indices
        slot_index = (schedule_index % total_slots_per_day) // total_rooms
        room_index = (schedule_index % total_rooms)

        # Ensure no double booking in the same room and slot
        if slot_index >= len(time_slots):
            schedule_index += 1
            continue  # Skip to next iteration if there are no valid slots

        room = rooms[room_index]
        slot = time_slots[slot_index]

        # Ensure no double booking in the same room and slot
        if slot in room_time_slot_usage[room.id][formatted_day]:
            schedule_index += 1  # Skip this schedule if the room/slot is already booked
            continue

        room_time_slot_usage[room.id][formatted_day].add(slot)  # Mark this slot as used for the room on the given day

        assigned_faculty = get_next_faculties(formatted_day, slot)

        if not assigned_faculty:
            print(f"Group {group.id} scheduling failed for {formatted_day}, Room: {room}, Slot: {slot}")
            schedule_index += 1
            continue  # Skip this group if no valid faculties were found

        count = sum(1 for faculty in assigned_faculty if faculty.has_master_degree)
        if count < 1:
            print(f"Group {group.id} scheduling failed: No faculty with a master’s degree in panel for {formatted_day}, Slot: {slot}")
            schedule_index += 1
            continue  # Skip this group if no master’s degree holder is found in the panel

        print(f"Group {group.id} successfully scheduled for {formatted_day}, Room: {room}, Slot: {slot}")

        day_label = f"Day {day_counter}"  # Assign proper day label

        for faculty in assigned_faculty:
            faculty_assignments[faculty.id] += 1

        assignments.append({
            'group': group,
            'faculty': assigned_faculty,
            'slot': slot,
            'date': formatted_day,
            'room': room,
            'day_label': day_label
        })

        schedule_index += 1  # Increment the schedule index

    # Assign remaining groups to the last successful assignment if they were not scheduled
    for group in groups:
        if group not in [assignment['group'] for assignment in assignments]:
            assigned = False  # Track if we successfully assign the group
            day_index = len(assignments) // total_slots_per_day  # Calculate correct day index
            formatted_day = days[day_index]  # Get the appropriate day based on index

            # Iterate through each time slot and each room
            for slot in time_slots:
                for room in rooms:
                    if slot in room_time_slot_usage[room.id][formatted_day]:
                        continue  # Skip this slot if already booked

                    assigned_faculty = get_next_faculties(formatted_day, slot)

                    if assigned_faculty:
                        count = sum(1 for faculty in assigned_faculty if faculty.has_master_degree)
                        if count < 1:
                            continue  # Skip if no faculty with a master's degree

                        print(f"Group {group.id} successfully scheduled for {formatted_day}, Room: {room}, Slot: {slot}")

                        room_time_slot_usage[room.id][formatted_day].add(slot)  # Mark this slot as used
                        for faculty in assigned_faculty:
                            faculty_assignments[faculty.id] += 1

                        assignments.append({
                            'group': group,
                            'faculty': assigned_faculty,
                            'slot': slot,
                            'date': formatted_day,
                            'room': room,
                            'day_label': f"Day {day_index + 1}"
                        })

                        assigned = True  # Mark as successfully assigned
                        break  # Break the room loop if assigned

                if assigned:
                    break  # Break the slot loop if assigned

            if not assigned:
                print(f"Group {group.id} could not be assigned a schedule after all attempts.")

    # Create the schedules
    with transaction.atomic():
        for assignment in assignments:
            group = assignment['group']
            assigned_faculty = assignment['faculty']
            slot = assignment['slot']
            formatted_day = assignment['date']
            room = assignment['room']
            day_label = assignment['day_label']

            # Create and save the schedule object
            Schedule.objects.create(
                group=group,
                faculty1=assigned_faculty[0],
                faculty2=assigned_faculty[1],
                faculty3=assigned_faculty[2],
                slot=slot,
                date=formatted_day,
                day=day_label,
                room=room,
                school_year=selected_school_year
            )

    return assignments  # Return all assignments for review or further processing

def get_faculty_assignments():
    # Initialize a dictionary to hold faculty assignments
    faculty_assignments = {faculty.id: 0 for faculty in Faculty.objects.all()}

    # Count the number of groups each faculty is assigned as a panel member
    schedules = Schedule.objects.all()
    for schedule in schedules:
        for faculty_id in [schedule.faculty1.id, schedule.faculty2.id, schedule.faculty3.id]:
            faculty_assignments[faculty_id] += 1

    # Create a list of faculty with their respective number of assignments
    faculty_list = []
    for faculty in Faculty.objects.all():
        faculty_list.append({
            'faculty_id': faculty.id,
            'name': faculty.name,
            'years': faculty.years_of_teaching,
            'assignments': faculty_assignments.get(faculty.id, 0)
        })

    return faculty_list




