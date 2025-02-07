from pulp import *
from authentication.models import Staff, Project, ProjectStaff, Skill
from django.utils import timezone
from .models import Task
from bson import ObjectId  # Add this import at the top
from datetime import datetime
from django.utils.dateparse import parse_datetime

def assign_staff_to_projects_90_100():
    """
    Uses bipartite matching with linear programming to assign staff to tasks
    optimizing for ~100% LOE per staff member, while considering staff capabilities.
    """
    current_date = timezone.now()
    
    # Get active staff and tasks
    staff_list = Staff.objects.filter(end_date__gte=current_date)
    task_list = Task.objects.filter(
        deadline__gte=current_date,
        status='unassigned'  # Only get unassigned tasks
    )
    
    if not staff_list or not task_list:
        return "No active staff or unassigned tasks found."

    # Calculate staff scores once for efficiency
    staff_scores = {staff.id: calculate_staff_score(staff) for staff in staff_list}

    # Create the optimization problem
    prob = LpProblem("Staff_Task_Assignment", LpMinimize)

    # Create binary variables for each staff-task pair
    x = LpVariable.dicts("assign",
        ((s.id, t.id) for s in staff_list for t in task_list),
        cat='Binary')  # Binary because a task should be fully assigned to one person

    # Calculate compatibility weights
    compatibility_weights = {}
    for staff in staff_list:
        for task in task_list:
            compatibility = check_staff_task_compatibility(staff, task, staff_scores[staff.id])
            compatibility_weights[(staff.id, task.id)] = max(0.1, compatibility['score'])

    # Variables to track deviation from 100% for each staff
    deviation = LpVariable.dicts("deviation",
        (s.id for s in staff_list),
        lowBound=0)

    # Modified objective: Minimize deviations while considering compatibility
    prob += lpSum(deviation[s.id] for s in staff_list) + \
            lpSum(x[s.id, t.id] * (1 - compatibility_weights[(s.id, t.id)]) * task.required_loe 
                 for s in staff_list for t in task_list)

    # Constraint 1: Each task must be assigned to exactly one staff member
    for task in task_list:
        prob += lpSum(x[s.id, task.id] for s in staff_list) == 1

    # Constraint 2: For each staff member, track deviation from 100%
    for staff in staff_list:
        total_loe = lpSum(x[staff.id, task.id] * task.required_loe for task in task_list)
        # These two constraints define the absolute deviation from 100%
        prob += total_loe - 100 <= deviation[staff.id]
        prob += 100 - total_loe <= deviation[staff.id]

    # Solve the problem
    prob.solve()

    if LpStatus[prob.status] == 'Optimal':
        # Create assignments
        assignments = []
        for staff in staff_list:
            staff_assignments = []
            for task in task_list:
                if value(x[staff.id, task.id]) > 0.5:  # Using 0.5 as threshold for binary variables
                    # Update task with assignment
                    task.assigned_staff = staff
                    task.status = 'assigned'
                    task.save()
                    
                    staff_assignments.append(
                        f"Task: {task.title}, LOE: {task.required_loe}%, "
                        f"Skills: {task.required_skills}, "
                        f"Deadline: {task.deadline.strftime('%Y-%m-%d')}"
                    )
            
            if staff_assignments:
                assignments.append(f"{staff.staff_name}: {', '.join(staff_assignments)}")

        return {
            "status": "success",
            "message": "Assignment complete with optimal solution",
            "assignments": assignments
        }
    else:
        return {
            "status": "error",
            "message": "No optimal solution found"
        }

def calculate_task_complexity(task):
    """
    Automatically calculate task complexity based on various factors.
    Returns a complexity level from 1-5.
    """
    score = 0
    
    # Factor 1: Number of required skills
    skills_count = len(task.required_skills) if task.required_skills else 0
    if skills_count <= 1:
        score += 1
    elif skills_count <= 2:
        score += 2
    elif skills_count <= 3:
        score += 3
    else:
        score += 4

    # Factor 2: Required LOE (effort)
    if task.required_loe <= 20:
        score += 1
    elif task.required_loe <= 40:
        score += 2
    elif task.required_loe <= 60:
        score += 3
    elif task.required_loe <= 80:
        score += 4
    else:
        score += 5

    # Factor 3: Duration (in days)
    try:
        # Convert deadline to datetime if it's a string
        deadline = task.deadline
        if isinstance(deadline, str):
            deadline = parse_datetime(deadline)
        if not deadline:
            deadline = datetime.strptime(task.deadline, '%Y-%m-%d')
        
        # Calculate duration
        duration = (deadline - timezone.now()).days
        
        if duration <= 7:  # 1 week
            score += 5
        elif duration <= 14:  # 2 weeks
            score += 4
        elif duration <= 30:  # 1 month
            score += 3
        elif duration <= 90:  # 3 months
            score += 2
        else:
            score += 1
    except Exception as e:
        # If there's any error in date calculation, default to lowest duration score
        print(f"Error calculating duration: {e}")
        score += 1

    # Calculate final complexity level (average of factors, rounded)
    final_score = round(score / 3)  # Divide by number of factors
    return min(max(final_score, 1), 5)  # Ensure result is between 1 and 5

def calculate_staff_score(staff):
    """
    Calculate a staff member's capability score based on various factors.
    Returns a dictionary of scores for different aspects.
    """
    scores = {
        'experience_level': 0,
        'skill_level': 0,
        'workload_capacity': 0
    }
    
    # Experience Level (1-5)
    current_date = timezone.now().date()
    start_date = staff.start_date.date()
    years_experience = (current_date - start_date).days / 365
    
    if years_experience <= 1:
        scores['experience_level'] = 1
    elif years_experience <= 3:
        scores['experience_level'] = 2
    elif years_experience <= 5:
        scores['experience_level'] = 3
    elif years_experience <= 8:
        scores['experience_level'] = 4
    else:
        scores['experience_level'] = 5

    # Skill Level (1-5)
    skill_count = len(staff.skills) if staff.skills else 0
    scores['skill_level'] = min(5, max(1, skill_count))

    # Workload Capacity (0-100%)
    current_tasks = Task.objects.filter(
        assigned_staff=staff,
        status__in=['assigned', 'in_progress']
    )
    total_loe = sum(task.required_loe for task in current_tasks)
    scores['workload_capacity'] = max(0, 100 - total_loe)

    return scores

def calculate_skill_match_score(required_skills, staff_skills):
    """
    Calculate a skill match score between required skills and staff skills.
    """
    # Debug prints
    print("Required skills:", required_skills)
    print("Staff skills:", staff_skills)

    def get_id_str(skill_ref):
        print("Processing skill_ref:", skill_ref, "Type:", type(skill_ref))
        if isinstance(skill_ref, dict) and '$oid' in skill_ref:
            return skill_ref['$oid']
        elif isinstance(skill_ref, ObjectId):
            return str(skill_ref)
        elif isinstance(skill_ref, str):
            return skill_ref
        elif hasattr(skill_ref, '_id'):  # Handle LazyReference objects
            return str(skill_ref._id)
        elif hasattr(skill_ref, 'id'):  # Handle Django model instances
            return str(skill_ref.id)
        return str(skill_ref)

    def get_object_id(skill_ref):
        if isinstance(skill_ref, ObjectId):
            return skill_ref
        elif hasattr(skill_ref, '_id'):  # Handle LazyReference objects
            return skill_ref._id
        elif hasattr(skill_ref, 'id'):  # Handle Django model instances
            return skill_ref.id
        id_str = get_id_str(skill_ref)
        try:
            return ObjectId(id_str)
        except Exception as e:
            print(f"Error converting to ObjectId: {e}")
            print(f"Problematic skill_ref: {skill_ref}, Type: {type(skill_ref)}")
            return None

    # Convert skill references to sets of ID strings
    required_set = set()
    staff_set = set()

    if required_skills:
        required_set = {get_id_str(skill) for skill in required_skills if skill is not None}
    if staff_skills:
        staff_set = {get_id_str(skill) for skill in staff_skills if skill is not None}
    
    print("Required set:", required_set)
    print("Staff set:", staff_set)

    if not required_set:
        valid_staff_ids = [get_object_id(sid) for sid in staff_set if get_object_id(sid) is not None]
        staff_skill_objects = Skill.objects.filter(id__in=valid_staff_ids)
        return {
            'score': 1.0,
            'matched_skills': [],
            'missing_skills': [],
            'extra_skills': [skill.name for skill in staff_skill_objects]
        }
    
    # Calculate matching skills
    matched_skills = required_set.intersection(staff_set)
    missing_skills = required_set - staff_set
    extra_skills = staff_set - required_set
    
    # Calculate score
    match_score = len(matched_skills) / len(required_set)

    # Fetch skill names using ObjectIds, handling potential invalid IDs
    valid_matched_ids = [get_object_id(sid) for sid in matched_skills if get_object_id(sid) is not None]
    valid_missing_ids = [get_object_id(sid) for sid in missing_skills if get_object_id(sid) is not None]
    valid_extra_ids = [get_object_id(sid) for sid in extra_skills if get_object_id(sid) is not None]

    matched_skill_objects = Skill.objects.filter(id__in=valid_matched_ids)
    missing_skill_objects = Skill.objects.filter(id__in=valid_missing_ids)
    extra_skill_objects = Skill.objects.filter(id__in=valid_extra_ids)
    
    return {
        'score': match_score,
        'matched_skills': [skill.name for skill in matched_skill_objects],
        'missing_skills': [skill.name for skill in missing_skill_objects],
        'extra_skills': [skill.name for skill in extra_skill_objects]
    }
    
def check_staff_task_compatibility(staff, task, staff_scores):
    """
    Check if a staff member is compatible with a task.
    Returns a compatibility score and reason.
    """
    compatibility = {
        'score': 0,
        'reasons': []
    }

    # Check workload capacity
    if staff_scores['workload_capacity'] < task.required_loe:
        compatibility['reasons'].append(
            f"Insufficient capacity: {staff_scores['workload_capacity']}% available, {task.required_loe}% needed"
        )
        return compatibility

    # Check experience leve l vs task complexity
    exp_match = 1 - (abs(staff_scores['experience_level'] - task.complexity_level) / 5)
    if exp_match < 0.6:  # Less than 60% match
        compatibility['reasons'].append(
            f"Experience mismatch: Staff level {staff_scores['experience_level']}, Task complexity {task.complexity_level}"
        )

    # Use new skill match calculation
    skill_match_result = calculate_skill_match_score(task.required_skills, staff.skills)
    if skill_match_result['score'] < 0.5:  # Less than 50% skill match
        compatibility['reasons'].append(
            f"Skill mismatch: Missing skills: {', '.join(skill_match_result['missing_skills'])}"
        )

    # Calculate overall compatibility score
    compatibility['score'] = (exp_match + skill_match_result['score']) / 2
    
    return compatibility