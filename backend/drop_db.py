import os
import django
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'feedback_system.settings')
django.setup()

import pymysql

conn = pymysql.connect(
    host=settings.DATABASES['default'].get('HOST') or 'localhost',
    user=settings.DATABASES['default'].get('USER') or 'root',
    password=settings.DATABASES['default'].get('PASSWORD') or '',
    port=int(settings.DATABASES['default'].get('PORT') or 3306)
)
cursor = conn.cursor()
db = settings.DATABASES['default']['NAME']
if db:
    cursor.execute(f"DROP DATABASE IF EXISTS {db}")
    cursor.execute(f"CREATE DATABASE {db}")
    print(f"Database {db} recreated.")
else:
    print("No DB configured!")
