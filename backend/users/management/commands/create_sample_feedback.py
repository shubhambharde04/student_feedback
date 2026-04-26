from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import date, timedelta
import random
from users.models import (
    FeedbackSession, FeedbackResponse, FeedbackSubmission, SessionOffering,
    Question, FeedbackForm, User, Answer
)


class Command(BaseCommand):
    help = 'Create sample feedback data for analytics testing'

    def handle(self, *args, **options):
        self.stdout.write('Creating sample feedback data for analytics...')
        
        try:
            # Get current session
            current_session = FeedbackSession.objects.filter(
                is_active=True
            ).first()
            
            if not current_session:
                self.stdout.write(self.style.ERROR('No active session found'))
                return
            
            # Get students
            students = User.objects.filter(role='student')[:10]
            if not students.exists():
                self.stdout.write(self.style.ERROR('No students found'))
                return
            
            # Get session offerings
            offerings = SessionOffering.objects.filter(session=current_session)[:5]
            if not offerings.exists():
                self.stdout.write(self.style.ERROR('No session offerings found'))
                return
            
            # Get questions
            questions = Question.objects.filter(question_type='RATING')
            if not questions.exists():
                self.stdout.write(self.style.ERROR('No rating questions found'))
                return
            
            # Create sample feedback
            created_count = 0
            for student in students:
                for offering in offerings:
                    # Check if already submitted
                    existing = FeedbackSubmission.objects.filter(
                        student=student,
                        offering=offering,
                        session=current_session
                    ).first()
                    
                    if existing and existing.is_completed:
                        continue
                    
                    # Create submission
                    submission, created = FeedbackSubmission.objects.get_or_create(
                        session=current_session,
                        offering=offering,
                        student=student,
                        defaults={
                            'form': FeedbackForm.objects.filter(session=current_session).first(),
                            'ip_address': '127.0.0.1',
                            'user_agent': 'Sample Data Generator'
                        }
                    )
                    
                    # Create ANONYMOUS FeedbackResponse (teacher is User directly)
                    response_container = FeedbackResponse.objects.create(
                        session=current_session,
                        form=submission.form,
                        offering=offering,
                        teacher=offering.teacher,
                        overall_remark=random.choice(["Great teaching!", "Good explanation.", "Needs more interaction.", "Helpful.", "Excellent."])
                    )

                    # Create individual Answers for each question
                    for question in questions:
                        rating = random.choices(
                            [5, 4, 3, 2, 1],
                            weights=[40, 35, 15, 7, 3]
                        )[0]
                        
                        Answer.objects.create(
                            response_parent=response_container,
                            question=question,
                            rating=rating
                        )
                    
                    # Mark as completed
                    submission.is_completed = True
                    submission.completion_percentage = 100.0
                    submission.save(update_fields=['is_completed', 'completion_percentage'])
                    created_count += 1
            
            self.stdout.write(self.style.SUCCESS(f'Created {created_count} sample feedback submissions'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error: {e}'))
