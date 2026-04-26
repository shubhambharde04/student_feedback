import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'feedback_system.settings')
django.setup()

from django.db import connection

with connection.cursor() as cursor:
    cursor.execute("SELECT app, name FROM django_migrations WHERE app='users' ORDER BY id")
    migrations = cursor.fetchall()
    for m in migrations:
        print(f"{m[0]}: {m[1]}")
