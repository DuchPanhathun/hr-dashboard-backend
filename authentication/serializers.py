from rest_framework import serializers
from .models import Staff, Project, ProjectStaff, Skill

class SkillSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    name = serializers.CharField(max_length=100)
    category = serializers.CharField(max_length=100)

class StaffSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    staff_name = serializers.CharField(max_length=100)
    role = serializers.CharField(max_length=100)
    start_date = serializers.DateTimeField()
    end_date = serializers.DateTimeField()
    total_loe = serializers.FloatField(min_value=0, max_value=100)
    skills = SkillSerializer(many=True, required=False)
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
        skills_data = validated_data.pop('skills', [])
        staff = Staff.objects.create(**validated_data)
        staff.skills = [Skill.objects.get(id=skill['id']) for skill in skills_data]
        staff.save()
        return staff

    def update(self, instance, validated_data):
        if 'skills' in validated_data:
            skills_data = validated_data.pop('skills')
            instance.skills = [Skill.objects.get(id=skill['id']) for skill in skills_data]
        
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
    project = ProjectSerializer()  # Nested serializer
    staff = StaffSerializer()      # Nested serializer
    loe_percentage = serializers.FloatField(min_value=0, max_value=100)
    start_date = serializers.DateTimeField()
    end_date = serializers.DateTimeField()

    def create(self, validated_data):
        project_data = validated_data.pop('project')
        staff_data = validated_data.pop('staff')
        project = Project.objects.get(id=project_data.get('id'))
        staff = Staff.objects.get(id=staff_data.get('id'))
        return ProjectStaff.objects.create(
            project=project,
            staff=staff,
            **validated_data
        )

    def update(self, instance, validated_data):
        if 'project' in validated_data:
            project_data = validated_data.pop('project')
            project = Project.objects.get(id=project_data.get('id'))
            instance.project = project
        if 'staff' in validated_data:
            staff_data = validated_data.pop('staff')
            staff = Staff.objects.get(id=staff_data.get('id'))
            instance.staff = staff
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance

class DocumentSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    title = serializers.CharField()
    content = serializers.CharField()
    file_type = serializers.CharField()
    uploaded_at = serializers.DateTimeField(read_only=True) 