from django.db import migrations
from django.conf import settings

class Migration(migrations.Migration):
    dependencies = [
        ('authentication', '0001_initial'),
    ]

    def migrate_staff_skills(apps, schema_editor):
        # Get the models from their correct apps
        Staff = apps.get_model('authentication', 'Staff')
        Skill = apps.get_model('authentication', 'Skill')
        StaffSkill = apps.get_model('authentication', 'StaffSkill')
        
        # Perform migration
        staff_skills = StaffSkill.objects.all()
        for staff_skill in staff_skills:
            staff = Staff.objects.get(id=staff_skill.staff.id)
            skill = Skill.objects.get(id=staff_skill.skill.id)
            
            if skill not in staff.skills:
                staff.skills.append(skill)
                staff.save()

    def reverse_migrate(apps, schema_editor):
        pass

    operations = [
        migrations.RunPython(migrate_staff_skills, reverse_migrate),
    ] 