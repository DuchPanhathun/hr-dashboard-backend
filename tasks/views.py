from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from bson import ObjectId
from .services import assign_staff_to_projects_90_100
import datetime
import logging
from authentication.models import Staff, Project, ProjectStaff
from .models import Task, Skill
from django.db.models import Sum, F
from django.utils import timezone
from .serializers import TaskSerializer, StaffSerializer, ProjectSerializer, ProjectStaffSerializer
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.contrib.auth import get_user_model
from django.utils.dateparse import parse_datetime

logger = logging.getLogger(__name__)

@api_view(['POST'])
@permission_classes([AllowAny])
def assign_staff(request):
    try:
        logger.info("Starting staff assignment process")
        
        # Call assignment service
        assignments = assign_staff_to_projects_90_100()
        logger.info(f"Assignments completed: {assignments}")

        if isinstance(assignments, dict) and assignments.get('status') == 'success':
            return Response(assignments, status=status.HTTP_200_OK)
        else:
            return Response({
                'error': 'Assignment failed',
                'detail': assignments
            }, status=status.HTTP_400_BAD_REQUEST)

    except Exception as e:
        logger.error(f"Error in assign_staff: {str(e)}", exc_info=True)
        return Response({
            'detail': str(e),
            'code': 'server_error'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def task_list_create(request):
    if request.method == 'GET':
        try:
            # Get query parameters
            sort_by = request.GET.get('sortBy', 'deadline')  # default to deadline
            availability_threshold = float(request.GET.get('availabilityThreshold', 0))
            skill_filter = request.GET.get('skillFilter', 'all')
            
            # Start with all tasks
            tasks = Task.objects.all()
            
            # Apply skill filter if specified
            if skill_filter != 'all':
                tasks = tasks.filter(required_skills__category=skill_filter)
            
            # Apply sorting
            if sort_by == 'deadline':
                tasks = tasks.order_by('deadline')
            elif sort_by == 'effort':
                tasks = tasks.order_by('-required_loe')
            elif sort_by == 'project':
                tasks = tasks.order_by('project__award_name')
            
            # Serialize tasks
            tasks_data = []
            for task in tasks:
                # Safely get dependencies
                dependencies_data = []
                if hasattr(task, 'dependencies') and task.dependencies:
                    try:
                        for dep_id in task.dependencies:
                            try:
                                dep_task = Task.objects.get(id=dep_id)
                                dependencies_data.append({
                                    'id': str(dep_task.id),
                                    'title': dep_task.title
                                })
                            except Task.DoesNotExist:
                                continue
                    except Exception as e:
                        logger.warning(f"Error processing dependencies for task {task.id}: {str(e)}")

                task_data = {
                    'id': str(task.id),
                    'title': task.title,
                    'required_skills': [
                        {
                            'id': str(skill.id),
                            'name': skill.name,
                            'category': skill.category
                        } for skill in task.required_skills
                    ] if task.required_skills else [],
                    'required_loe': float(task.required_loe),
                    'deadline': task.deadline.isoformat() if task.deadline else None,
                    'status': task.status,
                    'project': {
                        'id': str(task.project.id),
                        'award_name': task.project.award_name
                    } if task.project else None,
                    'assigned_staff': {
                        'id': str(task.assigned_staff.id),
                        'staff_name': task.assigned_staff.staff_name
                    } if task.assigned_staff else None,
                    'complexity_level': task.complexity_level,
                    'created_at': task.created_at.isoformat() if task.created_at else None,
                    'updated_at': task.updated_at.isoformat() if task.updated_at else None,
                    'dependencies': dependencies_data
                }
                tasks_data.append(task_data)
            
            return Response(tasks_data)
            
        except Exception as e:
            logger.error(f"Error in GET tasks: {str(e)}", exc_info=True)
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    elif request.method == 'POST':
        try:
            data = request.data
            logger.info(f"Received task data: {data}")

            # Convert string IDs to references for required fields
            if 'required_skills' in data:
                data['required_skills'] = [
                    Skill.objects.get(id=skill_id) 
                    for skill_id in data['required_skills']
                ]
            
            if 'project' in data and data['project']:
                data['project'] = Project.objects.get(id=data['project'])
                
            if 'dependencies' in data:
                data['dependencies'] = [
                    Task.objects.get(id=task_id) 
                    for task_id in data['dependencies']
                ]

            # Create new Task document
            task = Task(**data)
            task.save()

            # Return the created task in the same format as GET
            response_data = {
                'id': str(task.id),
                'title': task.title,
                'required_skills': [
                    {
                        'id': str(skill.id),
                        'name': skill.name,
                        'category': skill.category
                    } for skill in task.required_skills
                ],
                'required_loe': float(task.required_loe),
                'deadline': task.deadline if isinstance(task.deadline, str) else task.deadline.isoformat() if task.deadline else None,
                'status': task.status,
                'project': {
                    'id': str(task.project.id),
                    'award_name': task.project.award_name
                } if task.project else None,
                'complexity_level': task.complexity_level,
                'created_at': task.created_at.isoformat() if task.created_at else None,
                'updated_at': task.updated_at.isoformat() if task.updated_at else None,
                'dependencies': [
                    {
                        'id': str(dep.id),
                        'title': dep.title
                    } for dep in task.dependencies
                ],
                'priority': task.priority
            }
            
            return Response(response_data, status=status.HTTP_201_CREATED)
        except Exception as e:
            logger.error(f"Error in POST task: {str(e)}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([AllowAny])
def task_detail(request, task_id):
    try:
        # Use mongoengine's get method
        task = Task.objects.get(id=task_id)
    except Task.DoesNotExist:
        return Response(
            {'error': 'Task not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.error(f"Error fetching task {task_id}: {str(e)}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    if request.method == 'GET':
        serializer = TaskSerializer(task)
        return Response(serializer.data)

    elif request.method == 'PUT':
        try:
            serializer = TaskSerializer(data=request.data)
            if serializer.is_valid():
                # Update task fields
                task.title = serializer.validated_data.get('title', task.title)
                task.required_loe = serializer.validated_data.get('required_loe', task.required_loe)
                task.deadline = serializer.validated_data.get('deadline', task.deadline)
                task.status = serializer.validated_data.get('status', task.status)
                task.save()
                return Response(TaskSerializer(task).data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error updating task {task_id}: {str(e)}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    elif request.method == 'DELETE':
        try:
            task.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            logger.error(f"Error deleting task {task_id}: {str(e)}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

@api_view(['GET'])
def get_workload_overview(request):
    try:
        current_date = timezone.now()
        
        # Get all active staff
        staff_list = Staff.objects.filter(
            start_date__lte=current_date,
            end_date__gte=current_date
        )
        
        # Calculate LOE distribution
        distribution = {
            'under_utilized': 0,
            'optimal': 0,
            'overloaded': 0
        }
        
        bottlenecks = []
        
        for staff in staff_list:
            # Calculate total LOE for each staff member
            total_loe = ProjectStaff.objects.filter(
                staff=staff,
                start_date__lte=current_date,
                end_date__gte=current_date
            ).aggregate(total=Sum('loe_percentage'))['total'] or 0
            
            # Categorize staff based on LOE
            if total_loe < 90:
                distribution['under_utilized'] += 1
            elif 90 <= total_loe <= 100:
                distribution['optimal'] += 1
            else:
                distribution['overloaded'] += 1
                bottlenecks.append({
                    'staff_name': staff.staff_name,
                    'current_loe': total_loe,
                    'suggestion': f"Consider redistributing tasks from {staff.staff_name}"
                })
        
        return Response({
            'distribution': distribution,
            'bottlenecks': bottlenecks
        })
        
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(["GET"])
@permission_classes([AllowAny])
def get_staff_details(request):
    """
    Get detailed staff information including skills and current assignments
    """
    try:
        current_date = timezone.now()
        staff_list = Staff.objects.filter(
            start_date__lte=current_date,
            end_date__gte=current_date
        )

        staff_details = []
        for staff in staff_list:
            assignments = ProjectStaff.objects.filter(
                staff=staff,
                start_date__lte=current_date,
                end_date__gte=current_date
            )
            
            total_loe = sum(a.loe_percentage for a in assignments)
            
            staff_details.append({
                'id': staff.id,
                'name': staff.staff_name,
                'current_loe': total_loe,
                'skills': staff.skills.split(',') if staff.skills else [],
                'assignments': [{
                    'project_name': a.project.award_name,
                    'loe': a.loe_percentage,
                    'start_date': a.start_date,
                    'end_date': a.end_date
                } for a in assignments]
            })

        return Response(staff_details)
    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
def get_project_staff(request):
    try:
        current_date = timezone.now()
        project_staff = ProjectStaff.objects.filter(
            start_date__lte=current_date,
            end_date__gte=current_date
        ).select_related('staff', 'project')
        
        data = [{
            'id': ps.id,
            'staff': ps.staff.id,
            'project_name': ps.project.award_name,
            'loe': ps.loe_percentage,
            'start_date': ps.start_date,
            'end_date': ps.end_date
        } for ps in project_staff]
        
        return Response(data)
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
@permission_classes([AllowAny])
def create_task(request):
    try:
        data = request.data.copy()

        # Convert deadline string to datetime object
        if 'deadline' in data:
            try:
                # If receiving date string in format YYYY-MM-DD
                deadline_str = data['deadline']
                if isinstance(deadline_str, str):
                    if 'T' in deadline_str:  # If ISO format with time
                        data['deadline'] = parse_datetime(deadline_str)
                    else:  # If just date
                        data['deadline'] = datetime.datetime.strptime(deadline_str, '%Y-%m-%d')
            except ValueError as e:
                return Response(
                    {'error': f'Invalid deadline format: {str(e)}'},
                    status=status.HTTP_400_BAD_REQUEST
                )

        # Handle required_skills
        if 'required_skills' in data:
            data['required_skills'] = [
                Skill.objects.get(id=skill_id) 
                for skill_id in data['required_skills']
            ] if data['required_skills'] else []
        
        # Handle project
        if 'project' in data and data['project']:
            data['project'] = Project.objects.get(id=data['project'])
        
        # Handle dependencies
        if 'dependencies' in data and data['dependencies']:
            data['dependencies'] = [
                Task.objects.get(id=task_id) 
                for task_id in data['dependencies']
            ]
        else:
            data['dependencies'] = []

        # Create new Task document
        task = Task(**data)
        task.save()

        # Return the created task
        response_data = {
            'id': str(task.id),
            'title': task.title,
            'required_skills': [
                {
                    'id': str(skill.id),
                    'name': skill.name,
                    'category': skill.category
                } for skill in task.required_skills
            ] if task.required_skills else [],
            'required_loe': float(task.required_loe),
            'deadline': task.deadline.isoformat() if task.deadline else None,
            'status': task.status,
            'project': {
                'id': str(task.project.id),
                'award_name': task.project.award_name
            } if task.project else None,
            'complexity_level': task.complexity_level,
            'dependencies': [
                {
                    'id': str(dep.id),
                    'title': dep.title
                } for dep in task.dependencies
            ] if task.dependencies else []
        }
        
        return Response(response_data, status=status.HTTP_201_CREATED)
    except Exception as e:
        logger.error(f"Error in create_task: {str(e)}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['DELETE'])
@permission_classes([AllowAny])
def delete_task(request, task_id):
    try:
        task = Task.objects.get(id=task_id)
        task.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    except Task.DoesNotExist:
        return Response(
            {'error': 'Task not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
@permission_classes([AllowAny])
def get_staff_details(request):
    try:
        staff = Staff.objects.all()
        serializer = StaffSerializer(staff, many=True)
        return Response(serializer.data)
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
@permission_classes([AllowAny])
def get_project_staff(request):
    try:
        project_staff = ProjectStaff.objects.all().select_related('staff', 'project')
        serializer = ProjectStaffSerializer(project_staff, many=True)
        return Response(serializer.data)
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
@permission_classes([AllowAny])
def get_task_stats(request):
    try:
        total_tasks = Task.objects.count()
        unassigned_tasks = Task.objects.filter(status='unassigned').count()
        in_progress_tasks = Task.objects.filter(status='in_progress').count()
        completed_tasks = Task.objects.filter(status='completed').count()
        
        return Response({
            'total': total_tasks,
            'unassigned': unassigned_tasks,
            'in_progress': in_progress_tasks,
            'completed': completed_tasks
        })
    except Exception as e:
        logger.error(f"Error getting task stats: {str(e)}", exc_info=True)
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
@permission_classes([AllowAny])
def list_skills(request):
    try:
        skills = Skill.objects.all()
        skills_data = [{
            'id': str(skill.id),
            'name': skill.name,
            'category': skill.category
        } for skill in skills]
        
        return Response(skills_data)
    except Exception as e:
        logger.error(f"Error fetching skills: {str(e)}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
@permission_classes([AllowAny])
def create_skill(request):
    try:
        data = request.data
        skill = Skill(
            name=data['name'],
            category=data['category']
        )
        skill.save()
        
        return Response({
            'id': str(skill.id),
            'name': skill.name,
            'category': skill.category
        }, status=status.HTTP_201_CREATED)
    except Exception as e:
        logger.error(f"Error creating skill: {str(e)}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )