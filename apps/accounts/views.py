"""Account and user-directory views.

These views connect:
- registration form -> user creation
- user directory page -> filtered company/department user lists
"""
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import OperationalError, ProgrammingError
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404, redirect
from django.utils.decorators import method_decorator
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, DetailView, FormView, ListView, TemplateView
from django.views.decorators.cache import never_cache

from apps.assessments.models import QuizAssignment, QuizAttempt
from apps.common.pagination import build_pagination_context, paginate_items
from apps.common.models import LearningAuditEvent
from apps.courses.models import Enrollment, LessonProgress

from .forms import RegistrationForm, UserTransferForm
from .models import User, UserLifecycleRequest
from .services import apply_user_lifecycle_action, resolve_lifecycle_request


def get_manageable_departments_for_user(user: User):
    departments = []
    if user.company_id:
        departments = list(user.company.departments.order_by("name"))
    if not user.is_manager_like and user.department_id:
        departments = [department for department in departments if department.id == user.department_id]
    return departments


def get_directory_user_queryset(user: User):
    queryset = User.objects.select_related("company", "department").order_by("first_name", "last_name", "email")
    if user.is_superuser or user.role == User.Role.SUPER_ADMIN:
        return queryset
    if user.role == User.Role.LEARNER:
        return queryset.filter(id=user.id)
    if user.company_id:
        queryset = queryset.filter(company=user.company)
    if not user.is_manager_like and user.department_id:
        queryset = queryset.filter(department=user.department)
    return queryset


class UserDirectoryView(LoginRequiredMixin, ListView):
    model = User
    template_name = "accounts/user_directory.html"
    context_object_name = "users"
    paginate_by = 12

    def get_queryset(self):
        user = self.request.user
        queryset = get_directory_user_queryset(user)
        selected_department = self.request.GET.get("department", "").strip()
        selected_role = self.request.GET.get("role", "").strip()
        search = self.request.GET.get("q", "").strip()
        if selected_department:
            queryset = queryset.filter(department_id=selected_department)
        if selected_role:
            queryset = queryset.filter(role=selected_role)
        if search:
            queryset = queryset.filter(
                Q(first_name__icontains=search)
                | Q(last_name__icontains=search)
                | Q(username__icontains=search)
                | Q(email__icontains=search)
                | Q(employee_code__icontains=search)
                | Q(phone_number__icontains=search)
            )
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        users = context["users"]
        context["is_self_directory"] = self.request.user.role == User.Role.LEARNER
        context["profile_user"] = users.first() if context["is_self_directory"] else None
        filtered_users = self.get_queryset()
        learners_page = paginate_items(
            self.request,
            filtered_users.filter(role=User.Role.LEARNER),
            per_page=8,
            page_param="learner_page",
        )
        context["learners"] = learners_page["items"]
        context["learners_page"] = learners_page["page_obj"]
        context["learners_page_numbers"] = learners_page["page_numbers"]
        context["learners_pagination_query"] = learners_page["pagination_query"]
        context["learners_page_param"] = learners_page["page_param"]
        context["hr_users"] = filtered_users.filter(role=User.Role.HR_MANAGER)
        context["users_page"] = context["page_obj"]
        users_pagination = build_pagination_context(self.request, context["page_obj"])
        context["users_page_numbers"] = users_pagination["page_numbers"]
        context["users_pagination_query"] = users_pagination["pagination_query"]
        context["users_page_param"] = users_pagination["page_param"]
        departments = get_manageable_departments_for_user(self.request.user)
        context["departments"] = departments
        context["selected_department"] = self.request.GET.get("department", "").strip()
        context["selected_role"] = self.request.GET.get("role", "").strip()
        context["search_query"] = self.request.GET.get("q", "").strip()
        context["role_options"] = [
            (User.Role.SUPER_ADMIN, "Platform Admin"),
            (User.Role.COMPANY_ADMIN, "Developer Admin"),
            (User.Role.HR_MANAGER, "HR / Manager"),
            (User.Role.LEARNER, "Learner"),
        ]
        context["can_manage_users"] = self.request.user.is_manager_like or self.request.user.is_admin_like
        context["pending_lifecycle_requests"] = self._get_pending_lifecycle_requests()
        context["company_departments"] = departments
        return context

    def _get_pending_lifecycle_requests(self):
        try:
            pending_requests = UserLifecycleRequest.objects.select_related(
                "target_user", "requested_by", "requested_department"
            )
            if self.request.user.company_id:
                pending_requests = pending_requests.filter(target_user__company=self.request.user.company)
            return list(pending_requests.filter(
                status=UserLifecycleRequest.Status.PENDING
            )[:20])
        except (OperationalError, ProgrammingError):
            return []


class UserDetailView(LoginRequiredMixin, DetailView):
    model = User
    template_name = "accounts/user_detail.html"
    context_object_name = "profile_user"
    pk_url_kwarg = "user_id"

    def get_queryset(self):
        return get_directory_user_queryset(self.request.user)

    @staticmethod
    def _format_hours(total_seconds: int) -> str:
        hours = round((total_seconds or 0) / 3600, 1)
        return f"{hours:.1f} hrs"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile_user = context["profile_user"]
        enrollments = Enrollment.objects.filter(learner=profile_user).select_related("course").order_by("-updated_at")
        lesson_progress = LessonProgress.objects.filter(learner=profile_user).select_related(
            "lesson", "lesson__module", "lesson__module__course"
        )
        quiz_attempts = QuizAttempt.objects.filter(learner=profile_user).select_related("quiz", "quiz__course", "quiz__module").order_by("-created_at")
        quiz_assignments = QuizAssignment.objects.filter(learner=profile_user).select_related("quiz").order_by("-created_at")
        activity_feed = LearningAuditEvent.objects.filter(learner=profile_user).select_related(
            "course", "module", "lesson", "quiz", "department"
        )[:10]

        total_time_spent_seconds = lesson_progress.aggregate(total=Sum("time_spent_seconds"))["total"] or 0
        completed_lessons = lesson_progress.filter(status=LessonProgress.Status.COMPLETED).count()
        completed_courses = enrollments.filter(status=Enrollment.Status.COMPLETED).count()
        average_completion = enrollments.aggregate(total=Sum("completion_percentage"))["total"] or 0
        average_completion = round(float(average_completion) / enrollments.count(), 1) if enrollments.exists() else 0
        completed_quiz_attempts = quiz_attempts.exclude(status=QuizAttempt.Status.IN_PROGRESS)
        pending_quiz_attempts = quiz_attempts.filter(status=QuizAttempt.Status.PENDING_EVALUATION)
        passed_quiz_attempts = completed_quiz_attempts.filter(is_passed=True)

        context["profile_summary"] = {
            "hours_label": self._format_hours(total_time_spent_seconds),
            "time_spent_seconds": total_time_spent_seconds,
            "completed_lessons": completed_lessons,
            "completed_courses": completed_courses,
            "average_completion": average_completion,
            "quiz_attempts": completed_quiz_attempts.count(),
            "passed_quizzes": passed_quiz_attempts.count(),
            "pending_quiz_reviews": pending_quiz_attempts.count(),
            "active_assignments": quiz_assignments.count(),
        }
        context["recent_enrollments"] = enrollments[:8]
        context["recent_lesson_progress"] = lesson_progress.order_by("-updated_at")[:8]
        context["recent_quiz_attempts"] = quiz_attempts[:8]
        context["recent_activity_feed"] = activity_feed
        context["can_manage_users"] = self.request.user.is_manager_like or self.request.user.is_admin_like
        return context


@method_decorator(never_cache, name="dispatch")
class RegistrationView(CreateView):
    form_class = RegistrationForm
    template_name = "accounts/register.html"
    success_url = reverse_lazy("register-success")

    def form_valid(self, form):
        # After creating the user, we save a lightweight summary in session
        # so the next page can show the generated credentials clearly.
        response = super().form_valid(form)
        UserLifecycleRequest.objects.create(
            target_user=self.object,
            requested_by=self.object,
            action=UserLifecycleRequest.Action.REGISTRATION_APPROVAL,
            note="New employee registration is waiting for HR / Manager approval.",
        )
        self.request.session["registration_summary"] = {
            "user_id": "",
            "email": self.object.email,
            "username": self.object.username,
            "name": self.object.get_full_name() or self.object.username,
            "department": self.object.department.name if self.object.department else "",
            "role": self.object.get_role_display(),
            "status": "Pending HR / Manager Approval",
            "login_note": "After HR or manager approval, this employee can sign in with username or email and password.",
            "employee_id_note": "Employee ID will be generated only after HR or manager approval.",
        }
        messages.success(self.request, "Registration request submitted. HR or a manager must approve this employee account before login.")
        return response


@method_decorator(never_cache, name="dispatch")
class RegistrationSuccessView(TemplateView):
    template_name = "accounts/register_success.html"

    def dispatch(self, request, *args, **kwargs):
        if not request.session.get("registration_summary"):
            messages.info(request, "Register a user first to view the credential summary.")
            return super().dispatch(request, *args, **kwargs)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["registration"] = self.request.session.get("registration_summary")
        return context


class UserLifecycleActionView(LoginRequiredMixin, View):
    def post(self, request, user_id):
        if not (request.user.is_manager_like or request.user.is_admin_like):
            return redirect("user-directory")
        target_users = User.objects.select_related("company", "department")
        if request.user.company_id and not request.user.is_superuser and request.user.role != User.Role.SUPER_ADMIN:
            target_users = target_users.filter(company=request.user.company)
        target_user = target_users.filter(id=user_id).first()
        if target_user is None:
            messages.error(
                request,
                "That user is no longer available in your current department/company scope. Refresh the People page and try again.",
            )
            return redirect("user-directory")
        action = request.POST.get("action", "").strip()
        note = request.POST.get("note", "").strip()
        if action not in {
            UserLifecycleRequest.Action.DEACTIVATE,
            UserLifecycleRequest.Action.REACTIVATE,
            UserLifecycleRequest.Action.SOFT_DELETE,
        }:
            messages.error(request, "Unsupported lifecycle action.")
            return redirect("user-directory")
        apply_user_lifecycle_action(
            user=target_user,
            action=action,
            actor=request.user,
            note=note,
        )
        messages.success(request, f"{target_user.email} updated successfully.")
        return redirect("user-directory")


class UserTransferView(LoginRequiredMixin, FormView):
    template_name = "accounts/user_transfer.html"
    form_class = UserTransferForm

    def dispatch(self, request, *args, **kwargs):
        if not (request.user.is_manager_like or request.user.is_admin_like):
            return redirect("user-directory")
        target_users = User.objects.select_related("company", "department")
        if request.user.company_id and not request.user.is_superuser and request.user.role != User.Role.SUPER_ADMIN:
            target_users = target_users.filter(company=request.user.company)
        self.target_user = target_users.filter(id=kwargs["user_id"]).first()
        if self.target_user is None:
            messages.error(
                request,
                "That user is no longer available in your current department/company scope. Refresh the People page and try again.",
            )
            return redirect("user-directory")
        if self.target_user.id == request.user.id:
            messages.info(request, "Use a different HR / Manager account to transfer this profile.")
            return redirect("user-directory")
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["company"] = self.request.user.company if self.request.user.company_id else self.target_user.company
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["target_user"] = self.target_user
        context["current_department"] = self.target_user.department
        return context

    def form_valid(self, form):
        new_department = form.cleaned_data["department"]
        note = form.cleaned_data.get("note", "").strip()
        if self.target_user.department_id == new_department.id:
            messages.info(self.request, f"{self.target_user.email} is already in {new_department.name}.")
            return redirect("user-directory")
        apply_user_lifecycle_action(
            user=self.target_user,
            action=UserLifecycleRequest.Action.TRANSFER,
            actor=self.request.user,
            new_department=new_department,
            note=note,
        )
        messages.success(
            self.request,
            f"{self.target_user.email} moved to {new_department.name}.",
            extra_tags="popup",
        )
        return redirect("user-directory")


class UserLifecycleRequestCreateView(LoginRequiredMixin, View):
    def post(self, request):
        action = request.POST.get("action", UserLifecycleRequest.Action.SOFT_DELETE).strip()
        if action not in {
            UserLifecycleRequest.Action.DEACTIVATE,
            UserLifecycleRequest.Action.SOFT_DELETE,
        }:
            messages.error(request, "Unsupported request type.")
            return redirect("dashboard-home")
        if UserLifecycleRequest.objects.filter(
            target_user=request.user,
            action=action,
            status=UserLifecycleRequest.Status.PENDING,
        ).exists():
            messages.info(request, "A matching lifecycle request is already pending.")
            return redirect("dashboard-home")
        UserLifecycleRequest.objects.create(
            target_user=request.user,
            requested_by=request.user,
            action=action,
            note=request.POST.get("note", "").strip(),
        )
        messages.success(request, "Your account request was sent to HR for approval.")
        return redirect("dashboard-home")


class UserLifecycleRequestDecisionView(LoginRequiredMixin, View):
    def post(self, request, request_id):
        if not (request.user.is_manager_like or request.user.is_admin_like):
            return redirect("user-directory")
        lifecycle_requests = UserLifecycleRequest.objects.select_related("target_user", "requested_department")
        if request.user.company_id and not request.user.is_superuser and request.user.role != User.Role.SUPER_ADMIN:
            lifecycle_requests = lifecycle_requests.filter(target_user__company=request.user.company)
        lifecycle_request = get_object_or_404(
            lifecycle_requests,
            id=request_id,
        )
        decision = request.POST.get("decision", "").strip()
        selected_department_id = request.POST.get("requested_department", "").strip()
        if selected_department_id and lifecycle_request.action == UserLifecycleRequest.Action.REGISTRATION_APPROVAL:
            departments = get_manageable_departments_for_user(request.user)
            selected_department = next((department for department in departments if str(department.id) == selected_department_id), None)
            if selected_department is not None:
                lifecycle_request.requested_department = selected_department
                lifecycle_request.save(update_fields=["requested_department", "updated_at"])
        resolve_lifecycle_request(
            request_obj=lifecycle_request,
            reviewer=request.user,
            approve=decision == "approve",
            resolution_note=request.POST.get("resolution_note", "").strip(),
        )
        messages.success(request, "User request updated.")
        return redirect("user-directory")
