from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from .models import User, Staff
from django.core.exceptions import ObjectDoesNotExist
from .serializers import StaffSerializer

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
    print("Received data:", request.data)
    serializer = StaffSerializer(data=request.data)
    if serializer.is_valid():
        staff = Staff(**serializer.validated_data)
        staff.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@permission_classes([AllowAny])
def list_staff(request):
    staff = Staff.objects.all()
    serializer = StaffSerializer(staff, many=True)
    return Response(serializer.data) 

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
        serializer = StaffSerializer(staff, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    except Staff.DoesNotExist:
        return Response({'error': 'Staff not found'}, status=status.HTTP_404_NOT_FOUND) 