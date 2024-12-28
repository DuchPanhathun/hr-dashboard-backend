"""
WSGI config for hr_dashboard_backend project.
"""

import os
import sys
from pathlib import Path

# Get the absolute path to the project root
current_path = Path(__file__).resolve().parent.parent
project_root = str(current_path)

# Add the project root and the hr_dashboard_backend directory to Python path
if project_root not in sys.path:
    sys.path.append(project_root)
    sys.path.append(str(current_path / 'hr_dashboard_backend'))

print("Current directory:", os.getcwd())
print("Project root:", project_root)
print("Python path:", sys.path)

try:
    from django.core.wsgi import get_wsgi_application
    
    os.environ['DJANGO_SETTINGS_MODULE'] = 'hr_dashboard_backend.settings'
    
    application = get_wsgi_application()
except Exception as e:
    import traceback
    print("Exception occurred:")
    print(traceback.format_exc())
    raise
