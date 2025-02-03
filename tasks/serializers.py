from rest_framework import serializers
from .models import Staff, Project, ProjectStaff, Task
from bson import ObjectId
from authentication.serializers import StaffSerializer
from rest_framework_mongoengine import serializers

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
    class Meta:
        model = Task
        fields = '__all__'

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Convert ObjectId to string for project and assigned_staff
        if instance.project:
            data['project'] = str(instance.project.id)
            data['project_name'] = instance.project.award_name
        if instance.assigned_staff:
            data['assigned_staff'] = str(instance.assigned_staff.id)
            data['staff_name'] = instance.assigned_staff.staff_name
        return data

    def to_internal_value(self, data):
        # Convert string IDs to ObjectId for project and assigned_staff
        if 'project' in data and data['project']:
            data['project'] = ObjectId(data['project'])
        if 'assigned_staff' in data and data['assigned_staff']:
            data['assigned_staff'] = ObjectId(data['assigned_staff'])
        return super().to_internal_value(data)

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