from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from .models import User, Staff, Notification, Project, ProjectStaff, Document, Skill
from django.core.exceptions import ObjectDoesNotExist
from .serializers import StaffSerializer, ProjectSerializer, ProjectStaffSerializer, DocumentSerializer
import pandas as pd
from rest_framework.parsers import MultiPartParser, FormParser
from django.core.files.storage import default_storage
import os
from rag_system import create_rag_system, query_rag
from langchain.document_loaders import PyPDFLoader
from pathlib import Path
import logging

# Global RAG system instance
rag_qa_chain = None

logger = logging.getLogger(__name__)

def initialize_rag():
    global rag_qa_chain
    if rag_qa_chain is None:
        try:
            rag_qa_chain = create_rag_system()
        except Exception as e:
            print(f"Error initializing RAG system: {e}")
            rag_qa_chain = None

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
        staff_data = []
        for s in staff:
            staff_info = {
                'id': s.id,
                'staff_name': s.staff_name,
                'role': s.role,
                'start_date': s.start_date,
                'end_date': s.end_date,
                'total_loe': s.total_loe,
                'skills': [{'id': skill.id, 'name': skill.name, 'category': skill.category} 
                          for skill in s.skills] if s.skills else []
            }
            staff_data.append(staff_info)
        return Response(staff_data)
    except Exception as e:
        print(f"Error in list_staff: {str(e)}")
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
            'loe_percentage': 'LOE 2025 (Average)',
            'skills': 'Skill',
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
                    'total_loe': float(row['LOE 2025 (Average)']),
                    'skills': []
                }

                # Process skills if they exist in the row
                if 'Skill' in row and pd.notna(row['Skill']):
                    skills_str = str(row['Skill']).strip()
                    if skills_str:
                        # Split skills by comma if multiple skills are provided
                        skill_names = [s.strip() for s in skills_str.split(',')]
                        for skill_name in skill_names:
                            # Create or get skill
                            skill, created = Skill.objects.get_or_create(
                                name=skill_name,
                                defaults={'category': 'General'}  # Default category
                            )
                            staff_data['skills'].append(skill)

                # Create or update staff
                try:
                    staff = Staff.objects.get(staff_name=staff_data['staff_name'])
                    for key, value in staff_data.items():
                        if key == 'skills':
                            staff.skills = value
                        else:
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
                print(f"Error processing row {index + 1}: {str(row_error)}")
                return Response(
                    {'error': f'Error processing row {index + 1}: {str(row_error)}'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )

        return Response(
            {'message': f'Successfully processed {len(df_subset)} records'}, 
            status=status.HTTP_201_CREATED
        )

    except Exception as e:
        print(f"Error in upload_file: {str(e)}")
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

@api_view(['POST'])
@permission_classes([AllowAny])
@parser_classes([MultiPartParser, FormParser])
def upload_document(request):
    try:
        file = request.FILES['file']
        file_type = os.path.splitext(file.name)[1][1:].lower()
        
        if file_type not in ['pdf', 'txt', 'xlsx', 'xls']:
            return Response({
                'error': 'Unsupported file type. Only PDF, TXT, and Excel files are allowed.'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Define the data directory
        data_dir = Path('/Users/thun/Desktop/Project/hr-project/hr_dashboard_backend/data')
        
        # Create the directory if it doesn't exist
        data_dir.mkdir(parents=True, exist_ok=True)
        
        # Create a safe filename
        safe_filename = file.name.replace(' ', '_')
        file_path = data_dir / safe_filename

        # Save the file to the data directory
        with open(file_path, 'wb+') as destination:
            for chunk in file.chunks():
                destination.write(chunk)
        
        # Extract content based on file type
        try:
            if file_type == 'pdf':
                loader = PyPDFLoader(str(file_path))
                pages = loader.load()
                content = '\n'.join([page.page_content for page in pages])
            elif file_type in ['xlsx', 'xls']:
                df = pd.read_excel(str(file_path))
                content = df.to_string(index=False)
            else:  # txt
                with open(file_path, 'r') as f:
                    content = f.read()

            # Create document in database
            document = Document(
                title=file.name,
                content=content,
                file_type=file_type,
                uploaded_by=request.user if request.user.is_authenticated else None
            )
            document.save()

            # Reinitialize RAG system to include new document
            initialize_rag()

            return Response({
                'message': 'Document uploaded successfully',
                'document': DocumentSerializer(document).data,
                'file_path': str(file_path)
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            # If there's an error processing the file, delete it
            if file_path.exists():
                file_path.unlink()
            raise Exception(f"Error processing file: {str(e)}")

    except Exception as e:
        return Response({
            'error': f'Error uploading document: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([AllowAny])
def list_documents(request):
    documents = Document.objects.all().order_by('-uploaded_at')
    serializer = DocumentSerializer(documents, many=True)
    return Response(serializer.data)

@api_view(['POST'])
@permission_classes([AllowAny])
def rag_query(request):
    try:
        question = request.data.get('question')
        if not question:
            return Response({
                'error': 'Question is required'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Initialize RAG system if not already initialized
        initialize_rag()
        
        if rag_qa_chain is None:
            return Response({
                'error': 'RAG system is not initialized'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Query the RAG system
        result = query_rag(rag_qa_chain, question)
        
        return Response({
            'answer': result['answer'],
            'sources': result['sources']
        })

    except Exception as e:
        return Response({
            'error': f'Error processing query: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([AllowAny])
def list_project_staff(request):
    try:
        project_staff = ProjectStaff.objects.all()
        serializer = ProjectStaffSerializer(project_staff, many=True)
        return Response(serializer.data)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([AllowAny])
def get_project_staff_detail(request, project_staff_id):
    try:
        project_staff = ProjectStaff.objects.get(id=project_staff_id)
        serializer = ProjectStaffSerializer(project_staff)
        return Response(serializer.data)
    except ProjectStaff.DoesNotExist:
        return Response({'error': 'Project staff not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([AllowAny])
def create_project_staff(request):
    try:
        serializer = ProjectStaffSerializer(data=request.data)
        if serializer.is_valid():
            project_staff = serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['PUT'])
@permission_classes([AllowAny])
def update_project_staff(request, project_staff_id):
    try:
        project_staff = ProjectStaff.objects.get(id=project_staff_id)
        serializer = ProjectStaffSerializer(project_staff, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    except ProjectStaff.DoesNotExist:
        return Response({'error': 'Project staff not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['DELETE'])
@permission_classes([AllowAny])
def delete_project_staff(request, project_staff_id):
    try:
        project_staff = ProjectStaff.objects.get(id=project_staff_id)
        project_staff.delete()
        return Response({'message': 'Project staff deleted successfully'}, status=status.HTTP_200_OK)
    except ProjectStaff.DoesNotExist:
        return Response({'error': 'Project staff not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([AllowAny])
def debug_token(request):
    try:
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return Response({'error': 'No Bearer token'}, status=400)
        
        token = auth_header.split(' ')[1]
        
        # Log token details
        logger.info(f"Received token: {token[:20]}...")
        
        # Check if user exists
        username = request.data.get('username', '')
        user = User.objects.filter(username=username).first()
        
        if user:
            logger.info(f"Found user: {user.username}")
            return Response({
                'message': 'User found',
                'username': user.username,
                'is_active': user.is_active,
            })
        else:
            # List all users for debugging
            all_users = User.objects.all()
            usernames = [u.username for u in all_users]
            logger.info(f"All users in database: {usernames}")
            
            return Response({
                'error': 'User not found',
                'username_searched': username,
                'available_users': usernames
            }, status=404)
            
    except Exception as e:
        logger.error(f"Debug token error: {str(e)}")
        return Response({'error': str(e)}, status=500) 