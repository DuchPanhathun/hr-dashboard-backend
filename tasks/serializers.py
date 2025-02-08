from rest_framework import serializers
from authentication.models import Staff, Project, ProjectStaff
from .models import Task
from bson import ObjectId
from authentication.serializers import StaffSerializer
from rest_framework_mongoengine import serializers
from rest_framework import fields

class StaffSerializer(serializers.DocumentSerializer):
    class Meta:
        model = Staff
        fields = '__all__'

class ProjectSerializer(serializers.DocumentSerializer):
    class Meta:
        model = Project
        fields = '__all__'

class ProjectStaffSerializer(serializers.DocumentSerializer):
    project = ProjectSerializer()
    staff = StaffSerializer()

    class Meta:
        model = ProjectStaff
        fields = '__all__'

class TaskSerializer(serializers.DocumentSerializer):
    # Use fields from rest_framework instead of serializers
    project_id = fields.CharField(source='project.id', required=False, allow_null=True)
    project_name = fields.CharField(source='project.award_name', required=False, allow_null=True, read_only=True)
    assigned_staff_id = fields.CharField(source='assigned_staff.id', required=False, allow_null=True)
    staff_name = fields.CharField(source='assigned_staff.staff_name', required=False, allow_null=True, read_only=True)

    class Meta:
        model = Task
        fields = ('id', 'title', 'required_skills', 'required_loe', 'deadline', 'status',
                 'project_id', 'project_name', 'assigned_staff_id', 'staff_name',
                 'complexity_level', 'created_at', 'updated_at', 'priority',
                 'completion_date', 'completed_by', 'completion_notes')

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Handle ObjectId conversions
        if instance.project:
            data['project_id'] = str(instance.project.id)
            data['project_name'] = instance.project.award_name
        if instance.assigned_staff:
            data['assigned_staff_id'] = str(instance.assigned_staff.id)
            data['staff_name'] = instance.assigned_staff.staff_name
        if instance.completed_by:
            data['completed_by'] = str(instance.completed_by)
        return data

    def to_internal_value(self, data):
        internal_value = super().to_internal_value(data)
        # Convert string IDs to ObjectId references
        if 'project_id' in data and data['project_id']:
            try:
                project = Project.objects.get(id=ObjectId(data['project_id']))
                internal_value['project'] = project
            except Project.DoesNotExist:
                pass

        if 'assigned_staff_id' in data and data['assigned_staff_id']:
            try:
                staff = Staff.objects.get(id=ObjectId(data['assigned_staff_id']))
                internal_value['assigned_staff'] = staff
            except Staff.DoesNotExist:
                pass

        return internal_value

    def create(self, validated_data):
        return Task.objects.create(**validated_data)

    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance

    def validate_deadline(self, value):
        if value is None:
            raise serializers.ValidationError("Deadline is required")
        return value 