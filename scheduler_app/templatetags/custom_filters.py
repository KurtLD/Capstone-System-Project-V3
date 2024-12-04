from django import template
from django.forms import BoundField

register = template.Library()

@register.filter(name='replace_commas')
def replace_commas(value):
    if not isinstance(value, str):
        value = str(value)
    return value.replace(',', ',')

@register.filter(name='add_class')
def add_class(field, css_class):
    if isinstance(field, BoundField):
        return field.as_widget(attrs={"class": css_class})
    return field

@register.filter
def to_dict(group):
    group_dict = {
        'id': group.id,
        'member1': group.member1,
        'member2': group.member2,
        'member3': group.member3,
        'section': group.section,
    }
    
    if hasattr(group, 'subject_teacher'):
        group_dict['subject_teacher'] = group.subject_teacher.name
    if hasattr(group, 'capstone_teacher'):
        group_dict['capstone_teacher'] = group.capstone_teacher.name
    if hasattr(group, 'adviser'):
        group_dict['adviser'] = group.adviser.name
    if hasattr(group, 'title'):
        group_dict['title'] = group.title
    if hasattr(group, 'date'):
        group_dict['date'] = group.date

    return group_dict

@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)


@register.filter
def unique_days(grouped_schedules):
    unique_days = []
    for day_room, schedules in grouped_schedules.items():
        if day_room[0] not in unique_days:
            unique_days.append(day_room[0])
    return unique_days

@register.filter
def unique_rooms(grouped_schedules):
    unique_rooms = []
    for day_room, schedules in grouped_schedules.items():
        if day_room[2] not in unique_rooms:
            unique_rooms.append(day_room[2])
    return unique_rooms



@register.filter
def sort_days(days):
    return sorted(days)

@register.filter
def is_in(value, arg):
    """Check if value is in a list."""
    return value in arg

@register.filter
def ordinal_status(value):
    if value == 0:
        return "None"
    suffix = "th"  # Default suffix
    if 10 <= value % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(value % 10, "th")
    return f"{value}{suffix}"