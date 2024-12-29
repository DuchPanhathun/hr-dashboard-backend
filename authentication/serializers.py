from rest_framework import serializers
from .models import Staff

class StaffSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    staff_name = serializers.CharField(max_length=100)
    role = serializers.CharField(max_length=100)
    start_date = serializers.DateTimeField()
    end_date = serializers.DateTimeField()
    total_loe = serializers.FloatField(min_value=0, max_value=100)

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