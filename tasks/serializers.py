from rest_framework import serializers
from .models import Staff, Project, ProjectStaff, Task
from bson import ObjectId
from authentication.serializers import StaffSerializer

class StaffSerializer(serializers.ModelSerializer):
    class Meta:
        model = Staff
        fields = '__all__'

class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = '__all__'

class ProjectStaffSerializer(serializers.ModelSerializer):
    project = ProjectSerializer()
    staff = StaffSerializer()

    class Meta:
        model = ProjectStaff
        fields = '__all__'

class TaskSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    title = serializers.CharField(max_length=200)
    required_loe = serializers.FloatField(min_value=0, max_value=100)
    deadline = serializers.DateTimeField()
    status = serializers.ChoiceField(
        choices=[
            ('unassigned', 'Unassigned'),
            ('assigned', 'Assigned'),
            ('in_progress', 'In Progress'),
            ('completed', 'Completed')
        ],
        default='unassigned'
    )
    assigned_to = StaffSerializer(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)

    def create(self, validated_data):
        return Task.objects.create(**validated_data)

    def update(self, instance, validated_data):
        instance.title = validated_data.get('title', instance.title)
        instance.required_loe = validated_data.get('required_loe', instance.required_loe)
        instance.deadline = validated_data.get('deadline', instance.deadline)
        instance.status = validated_data.get('status', instance.status)
        instance.save()
        return instance

    def validate_deadline(self, value):
        if value is None:
            raise serializers.ValidationError("Deadline is required")
        return value 