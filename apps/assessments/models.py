"""Assessment data models.

These tables power the quiz engine:
- Quiz and Question define the assessment
- QuizAssignment decides who should see it
- QuizAttempt and QuizAnswer store learner results
"""
from django.db import models

from apps.common.models import OrderedModel, TimeStampedModel


class AssessmentCategory(TimeStampedModel):
    company = models.ForeignKey("organizations.Company", related_name="assessment_categories", on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=50)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ("name",)
        unique_together = ("company", "code")

    def __str__(self) -> str:
        return self.name


class Quiz(TimeStampedModel):
    class AssessmentType(models.TextChoices):
        QUIZ = "quiz", "Quiz"
        TEST = "test", "Test"

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PUBLISHED = "published", "Published"
        ARCHIVED = "archived", "Archived"

    company = models.ForeignKey("organizations.Company", related_name="quizzes", on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    assessment_type = models.CharField(max_length=20, choices=AssessmentType.choices, default=AssessmentType.QUIZ)
    description = models.TextField(blank=True)
    instructions = models.TextField(blank=True)
    category = models.ForeignKey(AssessmentCategory, related_name="quizzes", on_delete=models.SET_NULL, blank=True, null=True)
    course = models.ForeignKey("courses.Course", related_name="quizzes", on_delete=models.SET_NULL, blank=True, null=True)
    module = models.ForeignKey("courses.Module", related_name="quizzes", on_delete=models.SET_NULL, blank=True, null=True)
    passing_score = models.DecimalField(max_digits=5, decimal_places=2, default=70)
    time_limit_minutes = models.PositiveIntegerField(default=0)
    max_attempts = models.PositiveIntegerField(default=1)
    allow_multiple_attempts = models.BooleanField(default=False)
    allow_continue_on_fail = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)

    class Meta:
        ordering = ("title",)
        indexes = [
            models.Index(fields=["company", "status"], name="assess_quiz_company_status_idx"),
            models.Index(fields=["company", "assessment_type", "status"], name="assess_quiz_comp_type_stat_idx"),
            models.Index(fields=["course", "status"], name="assess_quiz_course_status_idx"),
            models.Index(fields=["module", "status"], name="assess_quiz_module_status_idx"),
        ]

    def __str__(self) -> str:
        return self.title


class Question(OrderedModel):
    class QuestionType(models.TextChoices):
        SINGLE_CHOICE = "single_choice", "Single Choice"
        MULTIPLE_CHOICE = "multiple_choice", "Multiple Choice"
        TRUE_FALSE = "true_false", "True / False"
        SHORT_ANSWER = "short_answer", "Short Answer"
        ESSAY = "essay", "Essay"

    quiz = models.ForeignKey(Quiz, related_name="questions", on_delete=models.CASCADE)
    prompt = models.TextField()
    section_title = models.CharField(max_length=120, blank=True)
    question_type = models.CharField(max_length=30, choices=QuestionType.choices, default=QuestionType.SINGLE_CHOICE)
    marks = models.PositiveIntegerField(default=1)
    negative_marks = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    suggested_seconds = models.PositiveIntegerField(default=0)
    explanation = models.TextField(blank=True)
    correct_answer_text = models.CharField(max_length=255, blank=True)
    style_config = models.JSONField(default=dict, blank=True)

    class Meta(OrderedModel.Meta):
        unique_together = ("quiz", "order")

    def __str__(self) -> str:
        return f"{self.quiz.title}: {self.prompt[:40]}"


class Choice(OrderedModel):
    question = models.ForeignKey(Question, related_name="choices", on_delete=models.CASCADE)
    text = models.CharField(max_length=500)
    is_correct = models.BooleanField(default=False)

    class Meta(OrderedModel.Meta):
        unique_together = ("question", "order")

    def __str__(self) -> str:
        return self.text


class QuizAssignment(TimeStampedModel):
    quiz = models.ForeignKey(Quiz, related_name="assignments", on_delete=models.CASCADE)
    department = models.ForeignKey(
        "organizations.Department",
        related_name="quiz_assignments",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )
    learner = models.ForeignKey(
        "accounts.User",
        related_name="quiz_assignments",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )
    assigned_by = models.ForeignKey(
        "accounts.User",
        related_name="created_quiz_assignments",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )
    due_date = models.DateField(blank=True, null=True)

    class Meta:
        indexes = [
            models.Index(fields=["quiz", "department"], name="assess_asg_quiz_dept_idx"),
            models.Index(fields=["quiz", "learner"], name="assess_asg_quiz_learner_idx"),
            models.Index(fields=["learner", "due_date"], name="assess_asg_learner_due_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.quiz} assignment"


class QuizAttempt(TimeStampedModel):
    class Status(models.TextChoices):
        IN_PROGRESS = "in_progress", "In Progress"
        SUBMITTED = "submitted", "Submitted"
        GRADED = "graded", "Graded"
        PENDING_EVALUATION = "pending_evaluation", "Pending Evaluation"

    quiz = models.ForeignKey(Quiz, related_name="attempts", on_delete=models.CASCADE)
    learner = models.ForeignKey("accounts.User", related_name="quiz_attempts", on_delete=models.CASCADE)
    started_at = models.DateTimeField(auto_now_add=True)
    submitted_at = models.DateTimeField(blank=True, null=True)
    score = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    percentage = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    is_passed = models.BooleanField(blank=True, null=True)
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.IN_PROGRESS)

    class Meta:
        indexes = [
            models.Index(fields=["quiz", "status"], name="assess_attempt_quiz_status_idx"),
            models.Index(fields=["learner", "status"], name="assess_attempt_learner_status_idx"),
            models.Index(fields=["learner", "is_passed"], name="assess_attempt_learner_passed_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.learner} - {self.quiz}"


class QuizAnswer(TimeStampedModel):
    attempt = models.ForeignKey(QuizAttempt, related_name="answers", on_delete=models.CASCADE)
    question = models.ForeignKey(Question, related_name="answers", on_delete=models.CASCADE)
    selected_choice_ids = models.JSONField(default=list, blank=True)
    answer_text = models.TextField(blank=True)
    awarded_marks = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    requires_manual_review = models.BooleanField(default=False)

    class Meta:
        unique_together = ("attempt", "question")

    def __str__(self) -> str:
        return f"{self.attempt} / {self.question_id}"
