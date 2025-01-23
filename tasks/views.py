from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from bson import ObjectId
from .services import assign_staff_to_projects_90_100
import datetime
import logging
from .models import Staff, Project, ProjectStaff, Task
from django.db.models import Sum, F
from django.utils import timezone
from .serializers import TaskSerializer, StaffSerializer, ProjectSerializer, ProjectStaffSerializer

logger = logging.getLogger(__name__)

@api_view(["POST"])
@permission_classes([AllowAny])
def assign_staff(request):
    """
    Trigger the staff assignment algorithm
    """
    try:
        result = assign_staff_to_projects_90_100()
        return Response(result, status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {
                "status": "error",
                "message": str(e)
            }, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def task_list_create(request):
    if request.method == 'GET':
        try:
            # Use mongoengine's queryset
            tasks = Task.objects.all().order_by('-created_at')
            serializer = TaskSerializer(tasks, many=True)
            return Response(serializer.data)
        except Exception as e:
            logger.error(f"Error in GET tasks: {str(e)}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    elif request.method == 'POST':
        try:
            logger.info(f"Received task data: {request.data}")
            serializer = TaskSerializer(data=request.data)
            if serializer.is_valid():
                # Create new Task document
                task = Task(
                    title=serializer.validated_data['title'],
                    required_loe=serializer.validated_data['required_loe'],
                    deadline=serializer.validated_data['deadline'],
                    status=serializer.validated_data.get('status', 'unassigned'),
                    created_at=timezone.now()
                )
                task.save()
                return Response(TaskSerializer(task).data, status=status.HTTP_201_CREATED)
            logger.error(f"Serializer errors: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
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
        serializer = TaskSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
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
        unassigned_tasks = Task.objects(status='unassigned').count()
        in_progress_tasks = Task.objects(status='in_progress').count()
        completed_tasks = Task.objects(status='completed').count()
        
        return Response({
            'total': total_tasks,
            'unassigned': unassigned_tasks,
            'in_progress': in_progress_tasks,
            'completed': completed_tasks
        })
    except Exception as e:
        logger.error(f"Error getting task stats: {str(e)}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )