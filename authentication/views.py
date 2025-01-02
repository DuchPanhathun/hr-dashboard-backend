from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from .models import User, Staff, Notification, Project, ProjectStaff
from django.core.exceptions import ObjectDoesNotExist
from .serializers import StaffSerializer, ProjectSerializer, ProjectStaffSerializer
import pandas as pd
from rest_framework.parsers import MultiPartParser

@api_view(['POST'])
@permission_classes([AllowAny])
def login_user(request):
    try:
        username = request.data.get('username')
        password = request.data.get('password')

        if not username or not password:
            return Response({
                'detail': 'Please provide both username and password'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(username=username)
        except Exception as e:
            print(f"User lookup error: {str(e)}")
            return Response({
                'detail': 'Invalid credentials'
            }, status=status.HTTP_401_UNAUTHORIZED)

        if user.check_password(password):
            refresh = RefreshToken.for_user(user)
            response = Response({
                'token': str(refresh.access_token),
                'refresh': str(refresh),
                'username': user.username
            })
            
            # Add CORS headers explicitly
            response["Access-Control-Allow-Origin"] = "http://localhost:3000"
            response["Access-Control-Allow-Credentials"] = "true"
            
            return response
        else:
            return Response({
                'detail': 'Invalid credentials'
            }, status=status.HTTP_401_UNAUTHORIZED)

    except Exception as e:
        print(f"Login error: {str(e)}, full error: {e.__dict__}")
        return Response({
            'detail': 'An error occurred during login'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([AllowAny])
def register_view(request):
    username = request.data.get('username')
    email = request.data.get('email')
    password = request.data.get('password')

    if User.objects.filter(username=username).exists():
        return Response(
            {'error': 'Username already exists'}, 
            status=status.HTTP_400_BAD_REQUEST
        )

    if User.objects.filter(email=email).exists():
        return Response(
            {'error': 'Email already exists'}, 
            status=status.HTTP_400_BAD_REQUEST
        )

    user = User(username=username, email=email)
    user.set_password(password)
    user.save()

    refresh = RefreshToken.for_user(user)
    return Response({
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }, status=status.HTTP_201_CREATED) 

@api_view(['GET'])
@permission_classes([IsAdminUser])
def list_users(request):
    users = User.objects.all()
    user_data = [{
        'id': str(user.id),
        'username': user.username,
        'email': user.email,
        'is_active': user.is_active,
        'date_joined': user.date_joined
    } for user in users]
    return Response(user_data) 

@api_view(['POST'])
@permission_classes([AllowAny])
def add_staff(request):
    serializer = StaffSerializer(data=request.data)
    if serializer.is_valid():
        staff = Staff(**serializer.validated_data)
        staff.save()
        
        # Create detailed notification
        Notification(
            message=f"Added new staff member: {staff.staff_name}",
            action_type='add',
            staff_name=staff.staff_name,
            user_name=request.user.username if request.user.is_authenticated else "System",
            details=f"Role: {staff.role}, LOE: {staff.total_loe}%"
        ).save()
        
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@permission_classes([AllowAny])
def list_staff(request):
    try:
        staff = Staff.objects.all()
        serializer = StaffSerializer(staff, many=True)
        return Response(serializer.data)
    except Exception as e:
        print(f"Error in list_staff: {str(e)}")  # Add debugging
        return Response(
            {'error': str(e)}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['DELETE'])
@permission_classes([AllowAny])
def delete_staff(request, staff_id):
    try:
        staff = Staff.objects.get(id=staff_id)
        staff.delete()
        return Response({'message': 'Staff deleted successfully'}, status=status.HTTP_200_OK)
    except Staff.DoesNotExist:
        return Response({'error': 'Staff not found'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['PUT'])
@permission_classes([AllowAny])
def update_staff(request, staff_id):
    try:
        staff = Staff.objects.get(id=staff_id)
        old_data = {
            'role': staff.role,
            'total_loe': staff.total_loe
        }
        
        serializer = StaffSerializer(staff, data=request.data)
        if serializer.is_valid():
            updated_staff = serializer.save()
            
            # Create detailed notification for update
            changes = []
            if old_data['role'] != updated_staff.role:
                changes.append(f"Role: {old_data['role']} → {updated_staff.role}")
            if old_data['total_loe'] != updated_staff.total_loe:
                changes.append(f"LOE: {old_data['total_loe']}% → {updated_staff.total_loe}%")
                
            if changes:
                Notification(
                    message=f"Updated staff member: {updated_staff.staff_name}",
                    action_type='update',
                    staff_name=updated_staff.staff_name,
                    user_name=request.user.username if request.user.is_authenticated else "System",
                    details=", ".join(changes)
                ).save()
            
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    except Staff.DoesNotExist:
        return Response({'error': 'Staff not found'}, status=status.HTTP_404_NOT_FOUND) 

@api_view(['GET'])
@permission_classes([AllowAny])
def get_notifications(request):
    notifications = Notification.objects.order_by('-timestamp')[:10]  # Get last 10 notifications
    return Response([{
        'id': n.id,
        'message': n.message,
        'action_type': n.action_type,
        'staff_name': n.staff_name,
        'timestamp': n.timestamp,
        'is_read': n.is_read
    } for n in notifications])

@api_view(['POST'])
@permission_classes([AllowAny])
def mark_notification_read(request, notification_id):
    try:
        notification = Notification.objects.get(id=notification_id)
        notification.is_read = True
        notification.save()
        return Response({'message': 'Notification marked as read'})
    except Notification.DoesNotExist:
        return Response({'error': 'Notification not found'}, status=404) 

@api_view(['POST'])
@permission_classes([AllowAny])
@parser_classes([MultiPartParser])
def upload_file(request):
    if 'file' not in request.FILES:
        return Response({'error': 'No file provided'}, status=status.HTTP_400_BAD_REQUEST)

    file = request.FILES['file']
    
    try:
        # Check file extension
        if file.name.endswith('.xlsx'):
            df = pd.read_excel(file)
        elif file.name.endswith('.csv'):
            df = pd.read_csv(file)
        else:
            return Response({'error': 'Invalid file format. Please upload .xlsx or .csv file'}, 
                          status=status.HTTP_400_BAD_REQUEST)

        print("Available columns:", df.columns.tolist())  # Debug print

        # Define column mappings (Database field name -> Excel column name)
        column_mappings = {
            'staff_name': 'Staff Name',
            'role': 'Role',
            'start_date': 'Staff Start Date',
            'end_date': 'Staff End Date',
            'award_name': 'Award/SOF Name (Informal)',
            'status': 'Status of Award',
            'project_start_date': 'Project Start Date',
            'project_end_date': 'Project End Date',
            'loe_percentage': 'LOE 2025 (Average)'  # Make sure this matches exactly
        }

        # Create a new dataframe with renamed columns
        df_subset = df[list(column_mappings.values())].copy()
        
        # Convert LOE to float and multiply by 100
        df_subset['LOE 2025 (Average)'] = pd.to_numeric(df_subset['LOE 2025 (Average)'], errors='coerce') * 100

        # Process each row
        for index, row in df_subset.iterrows():
            try:
                # Process Staff data
                staff_data = {
                    'staff_name': str(row['Staff Name']).strip(),
                    'role': str(row['Role']).strip(),
                    'start_date': pd.to_datetime(row['Staff Start Date']).strftime('%Y-%m-%d'),
                    'end_date': pd.to_datetime(row['Staff End Date']).strftime('%Y-%m-%d'),
                    'total_loe': float(row['LOE 2025 (Average)'])  # Add total_loe field
                }

                # Create or update staff
                try:
                    staff = Staff.objects.get(staff_name=staff_data['staff_name'])
                    for key, value in staff_data.items():
                        setattr(staff, key, value)
                    staff.save()
                except Staff.DoesNotExist:
                    staff = Staff.objects.create(**staff_data)

                # Process Project data
                project_data = {
                    'award_name': str(row['Award/SOF Name (Informal)']).strip(),
                    'status': str(row['Status of Award']).strip(),
                    'project_start_date': pd.to_datetime(row['Project Start Date']).strftime('%Y-%m-%d'),
                    'project_end_date': pd.to_datetime(row['Project End Date']).strftime('%Y-%m-%d'),
                }

                # Create or update project
                try:
                    project = Project.objects.get(award_name=project_data['award_name'])
                    for key, value in project_data.items():
                        setattr(project, key, value)
                    project.save()
                except Project.DoesNotExist:
                    project = Project.objects.create(**project_data)

                # Create or update ProjectStaff relationship
                project_staff_data = {
                    'loe_percentage': float(row['LOE 2025 (Average)']),
                    'start_date': pd.to_datetime(row['Staff Start Date']).strftime('%Y-%m-%d'),
                    'end_date': pd.to_datetime(row['Staff End Date']).strftime('%Y-%m-%d')
                }

                ProjectStaff.objects.update_or_create(
                    project=project,
                    staff=staff,
                    defaults=project_staff_data
                )

            except Exception as row_error:
                print(f"Error processing row {index + 1}: {str(row_error)}")  # Add debugging
                return Response(
                    {'error': f'Error processing row {index + 1}: {str(row_error)}'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )

        return Response(
            {'message': f'Successfully processed {len(df_subset)} records'}, 
            status=status.HTTP_201_CREATED
        )

    except Exception as e:
        print(f"Error in upload_file: {str(e)}")  # Add debugging
        return Response(
            {
                'error': 'Error processing file',
                'details': str(e),
                'available_columns': df.columns.tolist() if 'df' in locals() else []
            }, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
@permission_classes([AllowAny])
def list_projects(request):
    try:
        projects = Project.objects.all()
        project_data = []
        
        for project in projects:
            # Get all staff members for this project
            project_staff = ProjectStaff.objects.filter(project=project)
            staff_list = []
            
            for ps in project_staff:
                staff_list.append({
                    'id': ps.staff.id,
                    'staff_name': ps.staff.staff_name,
                    'loe_percentage': ps.loe_percentage,
                    'start_date': ps.start_date,
                    'end_date': ps.end_date
                })
            
            project_data.append({
                'id': project.id,
                'award_name': project.award_name,
                'status': project.status,
                'project_start_date': project.project_start_date,
                'project_end_date': project.project_end_date,
                'loe_percentage': project.loe_percentage,
                'staff': staff_list
            })
            
        return Response(project_data)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([AllowAny])
def get_project_staff(request, project_id):
    try:
        project = Project.objects.get(id=project_id)
        project_staff = ProjectStaff.objects.filter(project=project)
        
        staff_data = []
        for ps in project_staff:
            staff_data.append({
                'id': ps.staff.id,
                'staff_name': ps.staff.staff_name,
                'role': ps.staff.role,
                'loe_percentage': ps.loe_percentage,
                'start_date': ps.start_date,
                'end_date': ps.end_date
            })
            
        return Response(staff_data)
    except Project.DoesNotExist:
        return Response({'error': 'Project not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR) 

@api_view(['DELETE'])
@permission_classes([AllowAny])
def delete_project(request, project_id):
    try:
        project = Project.objects.get(id=project_id)
        project.delete()
        return Response({'message': 'Project deleted successfully'}, status=status.HTTP_200_OK)
    except Project.DoesNotExist:
        return Response({'error': 'Project not found'}, status=status.HTTP_404_NOT_FOUND) 