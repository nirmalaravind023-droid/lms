"""Certificate list page."""
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView

from apps.assessments.models import QuizAttempt
from apps.courses.models import Enrollment

from .models import Certificate
from .services import ensure_module_certificates


def _format_mark(value):
    numeric = float(value or 0)
    if numeric.is_integer():
        return str(int(numeric))
    return f"{numeric:.2f}".rstrip("0").rstrip(".")


def _badge_tier(percentage):
    score = float(percentage or 0)
    if score >= 90:
        return {"key": "gold", "label": "Gold Badge"}
    if score >= 75:
        return {"key": "silver", "label": "Silver Badge"}
    return {"key": "bronze", "label": "Bronze Badge"}


class CertificateListView(LoginRequiredMixin, ListView):
    template_name = "certificates/certificate_list.html"
    context_object_name = "certificates"

    def get_queryset(self):
        # Admins can audit many certificates; learners see only their own records.
        queryset = Certificate.objects.select_related("course", "module", "learner", "template")
        user = self.request.user
        selected_department = self.request.GET.get("department", "").strip()
        if user.is_admin_like:
            if user.company_id:
                queryset = queryset.filter(company=user.company)
            if selected_department:
                queryset = queryset.filter(learner__department_id=selected_department)
            return queryset
        return queryset.filter(learner=user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        departments = []
        selected_department = self.request.GET.get("department", "").strip()
        if self.request.user.company_id and self.request.user.is_admin_like:
            departments = list(self.request.user.company.departments.order_by("name"))
        if not self.request.user.is_admin_like:
            for enrollment in Enrollment.objects.filter(learner=self.request.user).select_related("course"):
                ensure_module_certificates(enrollment)
            context["object_list"] = self.get_queryset()
            context["certificates"] = context["object_list"]

        badge_attempts = QuizAttempt.objects.select_related(
            "quiz",
            "quiz__course",
            "quiz__module",
            "quiz__module__course",
            "learner",
            "learner__department",
        ).prefetch_related("quiz__questions").filter(is_passed=True)
        user = self.request.user
        if user.is_admin_like:
            if user.company_id:
                badge_attempts = badge_attempts.filter(quiz__company=user.company)
            if selected_department:
                badge_attempts = badge_attempts.filter(learner__department_id=selected_department)
        else:
            badge_attempts = badge_attempts.filter(learner=user)

        quiz_badges = []
        for attempt in badge_attempts.order_by("-updated_at"):
            quiz = attempt.quiz
            linked_course = quiz.course or getattr(quiz.module, "course", None)
            total_marks = sum(question.marks for question in quiz.questions.all())
            tier = _badge_tier(attempt.percentage)
            quiz_badges.append(
                {
                    "attempt": attempt,
                    "quiz": quiz,
                    "learner": attempt.learner,
                    "course": linked_course,
                    "badge_label": f"{quiz.get_assessment_type_display()} Badge",
                    "marks_label": f"{_format_mark(attempt.score)} / {_format_mark(total_marks or 0)}",
                    "percentage_label": f"{_format_mark(attempt.percentage)}%",
                    "tier_key": tier["key"],
                    "tier_label": tier["label"],
                }
            )

        context["departments"] = departments
        context["selected_department"] = selected_department
        context["quiz_badges"] = quiz_badges
        return context
