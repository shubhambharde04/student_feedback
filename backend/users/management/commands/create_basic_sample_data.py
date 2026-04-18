from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import date, timedelta
from users.models import (
    FeedbackSession, Question, FeedbackForm, FormQuestionMapping,
    User
)


class Command(BaseCommand):
    help = 'Create basic sample data for the new session-based feedback system'

    def handle(self, *args, **options):
        self.stdout.write('Creating basic sample session-based feedback data...')
        
        try:
            # Create sample sessions
            current_session = self.create_sample_sessions()
            
            # Create sample questions
            questions = self.create_sample_questions()
            
            # Create sample form and assign questions
            form = self.create_sample_form(current_session, questions)
            
            self.stdout.write(self.style.SUCCESS('Basic sample data created successfully!'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error: {e}'))

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
        else:
            self.stdout.write(f'Session already exists: {current_session.name}')
        
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
                    'is_active': True,
                    'is_required': True
                }
            )
            questions.append(question)
            if created:
                self.stdout.write(f'Created question: {question.text[:50]}...')
            else:
                self.stdout.write(f'Question already exists: {question.text[:50]}...')
        
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
        else:
            self.stdout.write(f'Form already exists: {form.name}')
        
        # Assign questions to form
        FormQuestionMapping.objects.filter(form=form).delete()  # Clear existing
        
        for order, question in enumerate(questions):
            mapping, created = FormQuestionMapping.objects.get_or_create(
                form=form,
                question=question,
                defaults={
                    'order': order,
                    'is_required': True
                }
            )
            if created:
                self.stdout.write(f'Assigned question to form: {question.text[:30]}...')
        
        self.stdout.write(f'Assigned {len(questions)} questions to form')
        return form
