from pulp import *
from authentication.models import Staff, Project, ProjectStaff
from django.utils import timezone
from .models import Task

def assign_staff_to_projects_90_100():
    """
    Uses bipartite matching with linear programming to assign staff to projects
    optimizing for ~100% LOE per staff member, while considering staff capabilities.
    """
    # Fetch all active staff and projects
    current_date = timezone.now()
    staff_list = Staff.objects.filter(
        start_date__lte=current_date,
        end_date__gte=current_date
    )
    project_list = Project.objects.filter(
        project_start_date__lte=current_date,
        project_end_date__gte=current_date
    )

    if not staff_list or not project_list:
        return "No active staff or projects found."

    # Calculate staff scores once for efficiency
    staff_scores = {staff.id: calculate_staff_score(staff) for staff in staff_list}

    # Create the optimization problem
    prob = LpProblem("Staff_Project_Assignment", LpMinimize)

    # Create binary variables for each staff-project pair
    x = LpVariable.dicts("assign",
        ((s.id, p.id) for s in staff_list for p in project_list),
        lowBound=0,
        upBound=100)

    # Add compatibility weights to the objective function
    compatibility_weights = {}
    for staff in staff_list:
        for project in project_list:
            # Create a mock task object to calculate complexity
            mock_task = type('MockTask', (), {
                'required_skills': project.required_skills,
                'required_loe': 100,  # Full-time equivalent
                'deadline': project.project_end_date,
                'dependencies': [],  # You might want to add project dependencies if available
            })
            
            # Calculate complexity using the existing function
            calculated_complexity = calculate_task_complexity(mock_task)
            
            # Create mock task with calculated complexity
            mock_task_with_complexity = type('MockTask', (), {
                'required_skills': project.required_skills,
                'complexity_level': calculated_complexity,  # Use calculated complexity
                'required_loe': 100,
                'deadline': project.project_end_date
            })
            
            compatibility = check_staff_task_compatibility(staff, mock_task_with_complexity, staff_scores[staff.id])
            compatibility_weights[(staff.id, project.id)] = max(0.1, compatibility['score'])

    # Variables to track deviation from 100% for each staff
    deviation = LpVariable.dicts("deviation",
        (s.id for s in staff_list),
        lowBound=0)

    # Modified objective: Minimize deviations while considering compatibility
    prob += lpSum(deviation[s.id] for s in staff_list) + \
            lpSum(x[s.id, p.id] * (1 - compatibility_weights[(s.id, p.id)]) 
                 for s in staff_list for p in project_list)

    # Constraint 1: For each staff member, track deviation from 100%
    for staff in staff_list:
        total_loe = lpSum(x[staff.id, project.id] for project in project_list)
        # These two constraints define the absolute deviation from 100%
        prob += total_loe - 100 <= deviation[staff.id]
        prob += 100 - total_loe <= deviation[staff.id]

    # Solve the problem
    prob.solve()

    if LpStatus[prob.status] == 'Optimal':
        # Clear existing assignments
        ProjectStaff.objects.all().delete()

        # Create new assignments
        assignments = []
        for staff in staff_list:
            staff_assignments = []
            for project in project_list:
                loe = value(x[staff.id, project.id])
                if loe > 0:  # Only create assignments with non-zero LOE
                    ProjectStaff.objects.create(
                        project=project,
                        staff=staff,
                        loe_percentage=loe,
                        start_date=max(staff.start_date, project.project_start_date),
                        end_date=min(staff.end_date, project.project_end_date)
                    )
                    staff_assignments.append(f"{project.award_name}: {loe:.1f}%")
            
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
    skills_count = len(task.required_skills.split(',')) if task.required_skills else 0
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

    # Factor 3: Dependencies
    dependency_count = task.dependencies.count() if hasattr(task, 'dependencies') else 0
    if dependency_count == 0:
        score += 1
    elif dependency_count <= 2:
        score += 2
    elif dependency_count <= 4:
        score += 3
    else:
        score += 4

    # Factor 4: Duration (in days)
    duration = (task.deadline - timezone.now()).days
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

    # Calculate final complexity level (average of factors, rounded)
    final_score = round(score / 4)  # Divide by number of factors
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
    years_experience = (timezone.now().date() - staff.start_date).days / 365
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
    skill_count = len(staff.skills.split(',')) if staff.skills else 0
    scores['skill_level'] = min(5, max(1, skill_count))

    # Workload Capacity (0-100%)
    current_tasks = Task.objects.filter(
        assigned_staff=staff,
        status__in=['assigned', 'in_progress']
    )
    total_loe = sum(task.required_loe for task in current_tasks)
    scores['workload_capacity'] = max(0, 100 - total_loe)  # Remaining capacity

    return scores

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

    # Check experience level vs task complexity
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

def assign_staff_with_weights(deadline_weight=1.0, complexity_weight=1.0, skill_match_weight=1.0, min_score_threshold=0.4):
    """
    Assigns staff to tasks based on weighted criteria and staff compatibility.
    Returns a list of assignment strings.
    """
    assignments = []
    unassigned_tasks = Task.objects.filter(status='unassigned')
    available_staff = Staff.objects.all()

    if not unassigned_tasks or not available_staff:
        return ["No unassigned tasks or available staff found"]

    # Calculate staff scores once
    staff_scores = {staff.id: calculate_staff_score(staff) for staff in available_staff}

    for task in unassigned_tasks:
        best_score = -1
        best_staff = None
        best_compatibility = None

        for staff in available_staff:
            # Check basic compatibility first
            compatibility = check_staff_task_compatibility(staff, task, staff_scores[staff.id])
            
            if compatibility['score'] < 0.6:  # Basic compatibility threshold
                continue

            # Calculate weighted score as before
            days_until_deadline = (task.deadline - timezone.now()).days
            deadline_score = 1.0 / max(days_until_deadline, 1)

            total_score = (
                deadline_weight * deadline_score +
                complexity_weight * compatibility['score'] +
                skill_match_weight * (staff_scores[staff.id]['skill_level'] / 5)
            ) * (staff_scores[staff.id]['workload_capacity'] / 100)

            normalized_score = total_score / (deadline_weight + complexity_weight + skill_match_weight)

            if normalized_score > best_score and normalized_score >= min_score_threshold:
                best_score = normalized_score
                best_staff = staff
                best_compatibility = compatibility

        if best_staff:
            task.assigned_staff = best_staff
            task.status = 'assigned'
            task.save()
            assignments.append(
                f"Assigned '{task.title}' to {best_staff.staff_name}\n"
                f"Match Score: {best_score:.2f}\n"
                f"Capacity: {staff_scores[best_staff.id]['workload_capacity']}%\n"
                f"Experience Level: {staff_scores[best_staff.id]['experience_level']}/5"
            )
        else:
            reasons = "No suitable staff found. Requirements not met:"
            for staff in available_staff:
                compatibility = check_staff_task_compatibility(staff, task, staff_scores[staff.id])
                if compatibility['reasons']:
                    reasons += f"\n{staff.staff_name}: {', '.join(compatibility['reasons'])}"
            assignments.append(f"Could not assign task '{task.title}'. {reasons}")

    return assignments

def calculate_skill_match_score(required_skills, staff_skills):
    """
    Calculate a skill match score between required skills and staff skills.
    
    Args:
        required_skills (str): Comma-separated string of required skills
        staff_skills (str): Comma-separated string of staff skills
    
    Returns:
        dict: Contains score (0-1) and detailed matching information
    """
    # Convert skill strings to sets, handling None values
    required_set = set(s.strip().lower() for s in required_skills.split(',')) if required_skills else set()
    staff_set = set(s.strip().lower() for s in staff_skills.split(',')) if staff_skills else set()
    
    if not required_set:
        return {
            'score': 1.0,
            'matched_skills': [],
            'missing_skills': [],
            'extra_skills': list(staff_set)
        }
    
    # Calculate matching skills
    matched_skills = required_set.intersection(staff_set)
    missing_skills = required_set - staff_set
    extra_skills = staff_set - required_set
    
    # Calculate score
    match_score = len(matched_skills) / len(required_set)
    
    return {
        'score': match_score,
        'matched_skills': list(matched_skills),
        'missing_skills': list(missing_skills),
        'extra_skills': list(extra_skills)
    }