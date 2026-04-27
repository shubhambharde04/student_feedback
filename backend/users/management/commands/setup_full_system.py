from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import date
from users.models import (
    Department, Branch, Semester, Subject, SubjectOffering,
    FeedbackSession, FeedbackForm, Question, FormQuestionMapping,
    SessionOffering, User, StudentSemester
)

class Command(BaseCommand):
    help = 'Setup full system with core data and sample users'

    def handle(self, *args, **options):
        self.stdout.write('Starting full system setup...')

        try:
            # 1. Create Departments
            dept_it, _ = Department.objects.get_or_create(name='Information Technology')
            dept_cse, _ = Department.objects.get_or_create(name='Computer Science')
            self.stdout.write(self.style.SUCCESS('Departments created.'))

            # 2. Create Branches
            branch_it, _ = Branch.objects.get_or_create(
                code='IT', 
                defaults={'name': 'Information Technology', 'department': dept_it}
            )
            branch_cse, _ = Branch.objects.get_or_create(
                code='CSE', 
                defaults={'name': 'Computer Science Engineering', 'department': dept_cse}
            )
            self.stdout.write(self.style.SUCCESS('Branches created.'))

            # 3. Create Semesters
            semesters = []
            for i in range(1, 7):
                sem, _ = Semester.objects.get_or_create(
                    number=i,
                    defaults={'name': f'Semester {i}'}
                )
                semesters.append(sem)
            self.stdout.write(self.style.SUCCESS('Semesters created.'))

            # 4. Create Subjects
            sub1, _ = Subject.objects.get_or_create(code='IT101', defaults={'name': 'Web Programming', 'credits': 4})
            sub2, _ = Subject.objects.get_or_create(code='CS101', defaults={'name': 'Data Structures', 'credits': 4})
            sub3, _ = Subject.objects.get_or_create(code='GEN101', defaults={'name': 'Professional Ethics', 'credits': 2})
            self.stdout.write(self.style.SUCCESS('Subjects created.'))

            # 5. Create Base Subject Offerings
            offering1, _ = SubjectOffering.objects.get_or_create(subject=sub1, branch=branch_it, semester=semesters[4]) # Sem 5
            offering2, _ = SubjectOffering.objects.get_or_create(subject=sub2, branch=branch_cse, semester=semesters[2]) # Sem 3
            offering3, _ = SubjectOffering.objects.get_or_create(subject=sub3, branch=branch_it, semester=semesters[4])
            self.stdout.write(self.style.SUCCESS('Base offerings created.'))

            # 6. Create Feedback Session
            session, _ = FeedbackSession.objects.get_or_create(
                type='ODD',
                year=2024,
                defaults={
                    'name': 'ODD 2024',
                    'start_date': date(2024, 7, 1),
                    'end_date': date(2024, 12, 31),
                    'is_active': True
                }
            )
            self.stdout.write(self.style.SUCCESS(f'Session {session.name} created.'))

            # 7. Create Questions
            questions_data = [
                ('The teacher explains concepts clearly', 'CLARITY', 1),
                ('The teacher is punctual', 'PUNCTUALITY', 2),
                ('The teacher is approachable', 'BEHAVIOR', 3),
            ]
            questions = []
            for text, cat, order in questions_data:
                q, _ = Question.objects.get_or_create(
                    text=text,
                    defaults={'question_type': 'RATING', 'category': cat, 'order': order}
                )
                questions.append(q)
            self.stdout.write(self.style.SUCCESS('Questions created.'))

            # 8. Create Form
            form, _ = FeedbackForm.objects.get_or_create(
                session=session,
                name='Main Feedback Form',
                defaults={'is_active': True}
            )
            for q in questions:
                FormQuestionMapping.objects.get_or_create(form=form, question=q)
            self.stdout.write(self.style.SUCCESS('Form created.'))

            # 9. Create Users (Teacher and Student)
            teacher, _ = User.objects.get_or_create(
                username='teacher_demo',
                defaults={'role': 'teacher', 'first_name': 'Demo', 'last_name': 'Teacher', 'email': 'teacher@demo.com'}
            )
            if _: teacher.set_password('password123'); teacher.save()

            student, _ = User.objects.get_or_create(
                username='student_demo',
                defaults={'role': 'student', 'first_name': 'Demo', 'last_name': 'Student', 'email': 'student@demo.com', 'enrollment_no': 'EN1001'}
            )
            if _: student.set_password('password123'); student.save()
            self.stdout.write(self.style.SUCCESS('Demo users created.'))

            # 10. Link Student to Semester/Branch
            StudentSemester.objects.get_or_create(
                student=student,
                session=session,
                defaults={'branch': branch_it, 'semester': semesters[4], 'is_active': True}
            )

            # 11. Create Session Offerings (assigned to teacher)
            SessionOffering.objects.get_or_create(
                session=session,
                base_offering=offering1,
                defaults={'teacher': teacher, 'is_active': True}
            )
            SessionOffering.objects.get_or_create(
                session=session,
                base_offering=offering3,
                defaults={'teacher': teacher, 'is_active': True}
            )
            self.stdout.write(self.style.SUCCESS('Session offerings created.'))

            self.stdout.write(self.style.SUCCESS('\nFull system setup completed successfully!'))
            self.stdout.write('You can now run "python manage.py create_sample_feedback" to generate test data.')

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error during setup: {e}'))
