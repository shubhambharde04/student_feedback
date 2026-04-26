import re
content = open('users/urls.py', 'r', encoding='utf-8').read()
content = content.replace("router.register(r'departments', DepartmentViewSet)", "router.register(r'departments', DepartmentViewSet, basename='department')")
content = content.replace("router.register(r'branches', BranchViewSet)", "router.register(r'branches', BranchViewSet, basename='branch')")
content = content.replace("router.register(r'semesters', SemesterViewSet)", "router.register(r'semesters', SemesterViewSet, basename='semester')")
content = content.replace("router.register(r'offerings', SubjectOfferingViewSet)", "router.register(r'offerings', SubjectOfferingViewSet, basename='offering')")
content = content.replace("router.register(r'assignments', SubjectAssignmentViewSet)", "router.register(r'assignments', SubjectAssignmentViewSet, basename='assignment')")
open('users/urls.py', 'w', encoding='utf-8').write(content)
