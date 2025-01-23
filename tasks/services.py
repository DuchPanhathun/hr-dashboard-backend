from pulp import *
from authentication.models import Staff, Project, ProjectStaff
from django.utils import timezone

def assign_staff_to_projects_90_100():
    """
    Uses bipartite matching with linear programming to assign staff to projects
    optimizing for ~100% LOE per staff member.
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

    # Create the optimization problem
    prob = LpProblem("Staff_Project_Assignment", LpMinimize)

    # Create binary variables for each staff-project pair
    # x[i][j] = percentage of time staff i spends on project j
    x = LpVariable.dicts("assign",
        ((s.id, p.id) for s in staff_list for p in project_list),
        lowBound=0,
        upBound=100)

    # Variables to track deviation from 100% for each staff
    deviation = LpVariable.dicts("deviation",
        (s.id for s in staff_list),
        lowBound=0)

    # Constraint 1: For each staff member, track deviation from 100%
    for staff in staff_list:
        total_loe = lpSum(x[staff.id, project.id] for project in project_list)
        # These two constraints define the absolute deviation from 100%
        prob += total_loe - 100 <= deviation[staff.id]
        prob += 100 - total_loe <= deviation[staff.id]

    # Objective: Minimize the sum of all deviations
    prob += lpSum(deviation[s.id] for s in staff_list)

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