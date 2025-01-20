from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    return dictionary.get(str(key), '')


@register.filter
def sum_existing_grades(criteria_list, existing_grades_data, member_index=None):
    """
    This filter calculates the sum of the existing grades for a given criteria list.

    :param criteria_list: The list of criteria to calculate the grades for.
    :param existing_grades_data: The dictionary of existing grades data.
    :param member_index: Optional member index for individual grading.
    :return: The sum of grades for the criteria list.
    """
    total = 0.0
    for criteria in criteria_list:
        if member_index:
            # For individual grading, use member-specific keys
            key = f"{criteria.id}_member{member_index}"
        else:
            # Regular grading
            key = str(criteria.id)
        
        total += float(existing_grades_data.get(key, 0))

    return round(total, 2)

@register.filter
def get_item_v2(list, index):
    try:
        return list[index]
    except IndexError:
        return None