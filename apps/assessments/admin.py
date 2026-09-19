from django.contrib import admin

from .models import AssessmentCategory, Choice, Question, Quiz, QuizAnswer, QuizAssignment, QuizAttempt


class ChoiceInline(admin.TabularInline):
    model = Choice
    extra = 0


class QuestionInline(admin.TabularInline):
    model = Question
    extra = 0


@admin.register(AssessmentCategory)
class AssessmentCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "company", "code")
    list_filter = ("company",)


@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = ("title", "company", "category", "course", "module", "status", "passing_score")
    list_filter = ("company", "category", "status")
    inlines = [QuestionInline]


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ("quiz", "order", "question_type", "marks")
    list_filter = ("quiz", "question_type")
    inlines = [ChoiceInline]


@admin.register(Choice)
class ChoiceAdmin(admin.ModelAdmin):
    list_display = ("question", "order", "text", "is_correct")


@admin.register(QuizAssignment)
class QuizAssignmentAdmin(admin.ModelAdmin):
    list_display = ("quiz", "department", "learner", "due_date")


@admin.register(QuizAttempt)
class QuizAttemptAdmin(admin.ModelAdmin):
    list_display = ("quiz", "learner", "status", "score", "percentage", "is_passed")
    list_filter = ("status", "quiz")


@admin.register(QuizAnswer)
class QuizAnswerAdmin(admin.ModelAdmin):
    list_display = ("attempt", "question", "awarded_marks", "requires_manual_review")

