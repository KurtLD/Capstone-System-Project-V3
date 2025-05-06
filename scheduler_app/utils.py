import random
import math
from .models import GroupInfoTH, Faculty, Schedule, Room, FacultyUnavailableSlot, FacultyUnavailableDate
from collections import defaultdict
from django.db import transaction
from datetime import datetime, timedelta
import logging
from users.models import SchoolYear

logger = logging.getLogger(__name__)

def generate_schedule(request, start_date=None):
    if start_date is None:
        raise ValueError("Start date must be provided")

    selected_school_year_id = request.session.get('selected_school_year_id')
    last_school_year = SchoolYear.objects.all().order_by('-end_year').first()
    selected_school_year = last_school_year if not selected_school_year_id else SchoolYear.objects.get(id=selected_school_year_id)
    if not selected_school_year_id:
        request.session['selected_school_year_id'] = selected_school_year.id

    Schedule.objects.filter(school_year=selected_school_year).delete()

    groups = list(GroupInfoTH.objects.filter(school_year=selected_school_year))
    faculties = list(Faculty.objects.filter(is_active=True))
    rooms = list(Room.objects.all().order_by("status"))
    base_time_slots = ["8AM-9AM", "9AM-10AM", "10AM-11AM", "11AM-12PM", 
                       "1PM-2PM", "2PM-3PM", "3PM-4PM", "4PM-5PM"]

    subject_teacher_ids = {group.subject_teacher.id for group in groups if group.subject_teacher}

    section_groups = defaultdict(list)
    for group in groups:
        section_groups[group.section].append(group)

    interleaved_groups = []
    while any(section_groups.values()):
        for section, section_group in list(section_groups.items()):
            if section_group:
                interleaved_groups.append(section_group.pop(0))
            if not section_group:
                del section_groups[section]

    groups = interleaved_groups

    days = []
    current_date = start_date
    total_days_needed = (len(groups) * 3) // (len(rooms) * len(base_time_slots)) + 5
    while len(days) < total_days_needed:
        if current_date.weekday() < 5:
            days.append(current_date.strftime('%B %d, %Y'))
        current_date += timedelta(days=1)

    faculty_assignments = defaultdict(int)
    faculty_daily_assignments = defaultdict(lambda: defaultdict(int))
    faculty_time_slots = defaultdict(set)
    faculty_pairings = defaultdict(set)
    room_schedule = defaultdict(lambda: defaultdict(set))
    assignments = []

    subject_teacher_groups = defaultdict(list)
    for group in groups:
        if group.subject_teacher:
            subject_teacher_groups[group.subject_teacher.id].append(group)

    total_assignments_needed = len(groups) * 3
    max_assignments_per_faculty = math.ceil(total_assignments_needed / len(faculties))
    min_assignments_per_faculty = max_assignments_per_faculty - 1

    faculty_unavailable_dates = defaultdict(set)
    faculty_unavailable_slots = defaultdict(set)

    for entry in FacultyUnavailableDate.objects.all():
        faculty_unavailable_dates[entry.faculty_id].add(entry.date)

    for entry in FacultyUnavailableSlot.objects.all():
        faculty_unavailable_slots[entry.faculty_id].add(entry.time_slot)

    def is_faculty_available(faculty, day_str, slot):
        try:
            day = datetime.strptime(day_str, '%B %d, %Y').date()
            if (day_str, slot) in faculty_time_slots[faculty.id]:
                return False
            if day in faculty_unavailable_dates[faculty.id]:
                return False
            if slot in faculty_unavailable_slots[faculty.id]:
                return False
            return True
        except ValueError:
            return False

    def get_available_faculties(day, slot, group=None, exclude=None, current_panel=None):
        exclude = exclude or []
        current_panel = current_panel or []

        subject_teacher = group.subject_teacher if group else None
        base_available = [
            f for f in faculties
            if f not in exclude
            and is_faculty_available(f, day, slot)
            and faculty_daily_assignments[f.id][day] < 4
        ]

        def faculty_allowed(f):
            if f.id in subject_teacher_ids:
                return faculty_assignments[f.id] < max_assignments_per_faculty
            else:
                return faculty_assignments[f.id] < min_assignments_per_faculty

        base_available = [f for f in base_available if faculty_allowed(f)]

        panel = []
        if subject_teacher in base_available:
            panel.append(subject_teacher)
            base_available.remove(subject_teacher)

        def score_faculty(f):
            pairing_score = sum(1 for p in current_panel if f.id in faculty_pairings[p.id])
            return (pairing_score, faculty_assignments[f.id], -int(f.has_master_degree), -f.years_of_teaching)

        base_available.sort(key=score_faculty)
        panel += base_available[:3 - len(panel)]

        return panel if len(panel) == 3 else []

    day_str_to_date = {d: datetime.strptime(d, '%B %d, %Y').date() for d in days}
    scheduled_group_ids = set()

    def find_best_day_and_slot(group, preferred_day=None):
        start_day_index = days.index(preferred_day) if preferred_day else 0

        for day_idx in range(start_day_index, len(days)):
            day = days[day_idx]
            day_obj = day_str_to_date[day]
            current_day_of_week = day_obj.strftime('%A')
            time_slots = base_time_slots[1:] if current_day_of_week == "Monday" else base_time_slots

            for slot in time_slots:
                for room in rooms:
                    if slot in room_schedule[room.id][day]:
                        continue
                    panel = get_available_faculties(day, slot, group=group)
                    if panel:
                        return day, slot, room, panel
        return None, None, None, None

    for group in groups:
        day, slot, room, panel = find_best_day_and_slot(group)
        if panel:
            room_schedule[room.id][day].add(slot)
            for faculty in panel:
                faculty_daily_assignments[faculty.id][day] += 1
                faculty_assignments[faculty.id] += 1
                faculty_time_slots[faculty.id].add((day, slot))
            for i in range(len(panel)):
                for j in range(i + 1, len(panel)):
                    faculty_pairings[panel[i].id].add(panel[j].id)
                    faculty_pairings[panel[j].id].add(panel[i].id)
            assignments.append({
                'group': group,
                'faculty': panel,
                'slot': slot,
                'date': day,
                'room': room,
                'day_label': f"Day {days.index(day) + 1}"
            })
            scheduled_group_ids.add(group.id)
        else:
            logger.warning(f"Failed to schedule group {group.id} after all attempts")

    for teacher_id in subject_teacher_ids:
        teacher = next((f for f in faculties if f.id == teacher_id), None)
        while faculty_assignments[teacher_id] < max_assignments_per_faculty:
            for group in subject_teacher_groups[teacher_id]:
                if group.id in scheduled_group_ids:
                    continue
                for day in days:
                    for slot in base_time_slots:
                        for room in rooms:
                            if slot in room_schedule[room.id][day]:
                                continue
                            other_faculties = [f for f in faculties if f.id != teacher_id and is_faculty_available(f, day, slot) and faculty_assignments[f.id] < min_assignments_per_faculty]
                            if len(other_faculties) < 2:
                                continue
                            panel = [teacher] + other_faculties[:2]
                            room_schedule[room.id][day].add(slot)
                            for faculty in panel:
                                faculty_assignments[faculty.id] += 1
                                faculty_daily_assignments[faculty.id][day] += 1
                                faculty_time_slots[faculty.id].add((day, slot))
                            assignments.append({
                                'group': group,
                                'faculty': panel,
                                'slot': slot,
                                'date': day,
                                'room': room,
                                'day_label': f"Day {days.index(day) + 1}"
                            })
                            scheduled_group_ids.add(group.id)
                            break
                    else:
                        continue
                    break

    with transaction.atomic():
        Schedule.objects.bulk_create([
            Schedule(
                group=a['group'],
                faculty1=a['faculty'][0],
                faculty2=a['faculty'][1],
                faculty3=a['faculty'][2],
                slot=a['slot'],
                date=a['date'],
                day=a['day_label'],
                room=a['room'],
                school_year=selected_school_year
            ) for a in assignments
        ])

    assignment_report = []
    for faculty in faculties:
        daily_counts = [faculty_daily_assignments[faculty.id][day] for day in days]
        max_daily = max(daily_counts) if daily_counts else 0
        unique_coworkers = len(faculty_pairings[faculty.id])
        assignment_report.append({
            'faculty': faculty.name,
            'total_assignments': faculty_assignments[faculty.id],
            'max_daily': max_daily,
            'unique_coworkers': unique_coworkers,
            'overloaded': max_daily > 3
        })

    assignment_counts = [a['total_assignments'] for a in assignment_report]
    avg_assignments = sum(assignment_counts) / len(assignment_counts) if assignment_counts else 0
    min_assignments = min(assignment_counts) if assignment_counts else 0
    max_assignments = max(assignment_counts) if assignment_counts else 0
    avg_coworkers = sum(a['unique_coworkers'] for a in assignment_report) / len(assignment_report) if assignment_report else 0

    print(f"Scheduling Summary:")
    print(f"Total groups: {len(groups)}")
    print(f"Scheduled groups: {len(assignments)}")
    print(f"Total faculty assignments: {sum(assignment_counts)}/{total_assignments_needed}")
    print(f"Avg assignments: {avg_assignments:.2f}")
    print(f"Min assignments: {min_assignments}")
    print(f"Max assignments: {max_assignments}")
    print(f"Avg unique coworkers: {avg_coworkers:.2f}")

    return assignments, assignment_report

def get_faculty_assignments():
    faculty_assignments = {f.id: 0 for f in Faculty.objects.all()}
    schedules = Schedule.objects.all()

    for s in schedules:
        faculty_assignments[s.faculty1.id] += 1
        faculty_assignments[s.faculty2.id] += 1
        faculty_assignments[s.faculty3.id] += 1

    return [{
        'faculty_id': f.id,
        'name': f.name,
        'years': f.years_of_teaching,
        'assignments': faculty_assignments[f.id]
    } for f in Faculty.objects.all()]
