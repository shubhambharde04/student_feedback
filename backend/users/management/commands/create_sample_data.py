from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import date, timedelta
from users.models import (
    FeedbackSession, Question, FeedbackForm, FormQuestionMapping,
    SessionOffering, SubjectOffering, User
)


class Command(BaseCommand):
    help = 'Create sample data for the new session-based feedback system'

    def handle(self, *args, **options):
        self.stdout.write('Creating sample session-based feedback data...')
        
        # Create sample sessions
        current_session = self.create_sample_sessions()
        
        # Create sample questions
        questions = self.create_sample_questions()
        
        # Create sample form and assign questions
        form = self.create_sample_form(current_session, questions)
        
        # Create sample session offerings
        self.create_sample_session_offerings(current_session)
        
        self.stdout.write(self.style.SUCCESS('Sample data created successfully!'))

    def create_sample_sessions(self):
        """Create sample feedback sessions"""
        # Current session (ODD 2024)
        current_session, created = FeedbackSession.objects.get_or_create(
            type='ODD',
            year=2024,
            defaults={
                'name': 'ODD 2024',
                'start_date': date(2024, 7, 1),
                'end_date': date(2024, 12, 31),
                'is_active': True,
                'is_locked': False,
                'description': 'Odd semester 2024 feedback session'
            }
        )
        
        if created:
            self.stdout.write(f'Created session: {current_session.name}')
        
        # Previous session (EVEN 2023)
        previous_session, created = FeedbackSession.objects.get_or_create(
            type='EVEN',
            year=2023,
            defaults={
                'name': 'EVEN 2023',
                'start_date': date(2023, 1, 1),
                'end_date': date(2023, 6, 30),
                'is_active': False,
                'is_locked': True,
                'description': 'Even semester 2023 feedback session'
            }
        )
        
        if created:
            self.stdout.write(f'Created session: {previous_session.name}')
        
        return current_session

    def create_sample_questions(self):
        """Create sample questions"""
        questions_data = [
            {
                'text': 'The teacher explains concepts clearly and effectively',
                'question_type': 'RATING',
                'category': 'CLARITY',
                'weight': 1.0,
                'order': 1
            },
            {
                'text': 'The teacher is punctual and maintains regular class schedule',
                'question_type': 'RATING',
                'category': 'PUNCTUALITY',
                'weight': 1.0,
                'order': 2
            },
            {
                'text': 'The teacher\'s teaching methods are engaging and effective',
                'question_type': 'RATING',
                'category': 'TEACHING',
                'weight': 1.2,
                'order': 3
            },
            {
                'text': 'The teacher encourages student participation and interaction',
                'question_type': 'RATING',
                'category': 'INTERACTION',
                'weight': 1.0,
                'order': 4
            },
            {
                'text': 'The teacher is approachable and helpful outside class',
                'question_type': 'RATING',
                'category': 'BEHAVIOR',
                'weight': 1.0,
                'order': 5
            },
            {
                'text': 'Please provide any additional comments or suggestions',
                'question_type': 'TEXT',
                'category': 'GENERAL',
                'weight': 0.5,
                'order': 6
            },
            {
                'text': 'How would you rate the overall course content?',
                'question_type': 'MULTIPLE_CHOICE',
                'category': 'GENERAL',
                'weight': 0.8,
                'order': 7,
                'choices': {'options': ['Excellent', 'Good', 'Average', 'Poor', 'Very Poor']}
            }
        ]
        
        questions = []
        for q_data in questions_data:
            question, created = Question.objects.get_or_create(
                text=q_data['text'],
                defaults={
                    'question_type': q_data['question_type'],
                    'category': q_data['category'],
                    'weight': q_data['weight'],
                    'order': q_data['order'],
                    'choices': q_data.get('choices', {}),
                    'is_active': True,
                    'is_required': q_data['question_type'] != 'TEXT'
                }
            )
            questions.append(question)
            if created:
                self.stdout.write(f'Created question: {question.text[:50]}...')
        
        return questions

    def create_sample_form(self, session, questions):
        """Create sample feedback form and assign questions"""
        form, created = FeedbackForm.objects.get_or_create(
            session=session,
            name='Student Feedback Form',
            defaults={
                'description': 'Comprehensive student feedback form for course evaluation',
                'is_active': True
            }
        )
        
        if created:
            self.stdout.write(f'Created form: {form.name}')
        
        # Assign questions to form
        FormQuestionMapping.objects.filter(form=form).delete()  # Clear existing
        
        for order, question in enumerate(questions):
            FormQuestionMapping.objects.get_or_create(
                form=form,
                question=question,
                defaults={
                    'order': order,
                    'is_required': question.question_type != 'TEXT'
                }
            )
        
        self.stdout.write(f'Assigned {len(questions)} questions to form')
        return form

    def create_sample_session_offerings(self, session):
        """Create sample session offerings"""
        # Get some existing subject offerings
        base_offerings = SubjectOffering.objects.all()[:5]
        
        # Get some teachers
        teachers = User.objects.filter(role='teacher')[:3]
        
        if not teachers.exists():
            # Create a sample teacher if none exists
            teacher, created = User.objects.get_or_create(
                username='teacher1',
                defaults={
                    'first_name': 'John',
                    'last_name': 'Doe',
                    'role': 'teacher',
                    'email': 'teacher1@example.com'
                }
            )
            if created:
                teacher.set_password('password123')
                teacher.save()
            teachers = [teacher]
        
        created_count = 0
        for offering in base_offerings:
            for teacher in teachers:
                session_offering, created = SessionOffering.objects.get_or_create(
                    session=session,
                    base_offering=offering,
                    teacher=teacher,
                    defaults={
                        'max_students': 60,
                        'is_active': True
                    }
                )
                if created:
                    self.stdout.write(f'Created session offering: {session_offering}')
                    created_count += 1
                else:
                    self.stdout.write(f'Session offering already exists: {session_offering}')
        
        if created_count == 0:
            self.stdout.write('All session offerings already exist')
        else:
            self.stdout.write(f'Created {created_count} new session offerings')
