from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from bson import ObjectId
from .services import assign_staff_to_projects_90_100
from .db import get_db
import datetime
import logging

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

@api_view(["POST"])
@permission_classes([AllowAny])
def create_task(request):
    """
    Create a new task and trigger reassignment.
    """
    try:
        # Log the incoming request data
        logger.info(f"Received task creation request with data: {request.data}")
        
        db = get_db()
        data = request.data

        # Validate required fields
        if not data.get("title"):
            logger.warning("Task creation failed: Title is required")
            return Response({
                "status": "error",
                "message": "Title is required"
            }, status=status.HTTP_400_BAD_REQUEST)

        # Create new task with validated data
        new_task = {
            "title": data.get("title"),
            "requiredLOE": float(data.get("requiredLOE", 0)),
            "assignedTo": None,
            "createdAt": datetime.datetime.utcnow()
        }
        
        logger.info(f"Attempting to insert task: {new_task}")
        
        # Insert the new task
        result = db.tasks.insert_one(new_task)
        
        logger.info(f"Task created successfully with ID: {result.inserted_id}")
        
        # Trigger reassignment
        assignment_result = assign_staff_to_projects_90_100()
        
        # Handle both string and dictionary responses from assign_staff_to_projects_90_100
        assignments = []
        if isinstance(assignment_result, dict):
            assignments = assignment_result.get("assignments", [])
        elif isinstance(assignment_result, str):
            assignments = [assignment_result]
        
        return Response({
            "status": "success",
            "message": "Task created and assignment updated",
            "taskId": str(result.inserted_id),
            "assignments": assignments
        }, status=status.HTTP_201_CREATED)
        
    except ValueError as e:
        logger.error(f"Value error in task creation: {str(e)}")
        return Response({
            "status": "error",
            "message": f"Invalid data format: {str(e)}"
        }, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.error(f"Error creating task: {str(e)}", exc_info=True)
        return Response({
            "status": "error",
            "message": f"Internal server error while creating task: {str(e)}"
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(["DELETE"])
@permission_classes([AllowAny])
def delete_task(request, task_id):
    """
    Delete a task by its ID
    """
    try:
        db = get_db()
        result = db.tasks.delete_one({"_id": task_id})
        
        if result.deleted_count > 0:
            # Trigger reassignment after deletion
            assignment_result = assign_staff_to_projects_90_100()
            
            return Response({
                "status": "success",
                "message": "Task deleted successfully",
                "assignments": assignment_result.get("assignments", [])
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                "status": "error",
                "message": "Task not found"
            }, status=status.HTTP_404_NOT_FOUND)
            
    except Exception as e:
        return Response({
            "status": "error",
            "message": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)