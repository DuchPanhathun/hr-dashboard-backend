from rest_framework import serializers
from .models import Staff, Project, ProjectStaff

class StaffSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    staff_name = serializers.CharField(max_length=100)
    role = serializers.CharField(max_length=100)
    start_date = serializers.DateTimeField()
    end_date = serializers.DateTimeField()
    total_loe = serializers.FloatField(min_value=0, max_value=100)
    projects = serializers.SerializerMethodField()

    def get_projects(self, obj):
        project_staff = ProjectStaff.objects.filter(staff=obj)
        return [{
            'id': ps.project.id,
            'award_name': ps.project.award_name,
            'status': ps.project.status,
            'loe_percentage': ps.loe_percentage,
            'start_date': ps.start_date,
            'end_date': ps.end_date
        } for ps in project_staff]

    def create(self, validated_data):
        return Staff.objects.create(**validated_data)

    def update(self, instance, validated_data):
        instance.staff_name = validated_data.get('staff_name', instance.staff_name)
        instance.role = validated_data.get('role', instance.role)
        instance.start_date = validated_data.get('start_date', instance.start_date)
        instance.end_date = validated_data.get('end_date', instance.end_date)
        instance.total_loe = validated_data.get('total_loe', instance.total_loe)
        instance.save()
        return instance 

class ProjectSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    award_name = serializers.CharField(max_length=200)
    status = serializers.CharField(max_length=100)
    project_start_date = serializers.DateTimeField()
    project_end_date = serializers.DateTimeField()
    loe_percentage = serializers.FloatField(min_value=0, max_value=100)

    def create(self, validated_data):
        return Project.objects.create(**validated_data)

    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance

class ProjectStaffSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    project = serializers.PrimaryKeyRelatedField(queryset=Project.objects.all())
    staff = serializers.PrimaryKeyRelatedField(queryset=Staff.objects.all())
    loe_percentage = serializers.FloatField(min_value=0, max_value=100)
    start_date = serializers.DateTimeField()
    end_date = serializers.DateTimeField()

    def create(self, validated_data):
        return ProjectStaff.objects.create(**validated_data)

    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance 