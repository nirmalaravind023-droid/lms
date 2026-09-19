"""Assessment forms.

Portal forms here cover quiz assignment and quiz builder metadata.
"""
from django import forms
from django.db.models import Q

from apps.accounts.models import User
from apps.organizations.models import Company, Department

from .models import Quiz, QuizAssignment


def resolve_lms_company(user):
    if getattr(user, "company_id", None):
        return user.company
    return Company.objects.filter(is_active=True, name__iexact="Demo Company").order_by("name").first()


class QuizBuilderForm(forms.ModelForm):
    department = forms.ModelChoiceField(
        queryset=Department.objects.none(),
        required=False,
        label="Department",
    )
    assign_department = forms.ModelChoiceField(
        queryset=Department.objects.none(),
        required=False,
        label="Assign To Department",
    )
    assign_due_date = forms.DateField(
        required=False,
        label="Assignment Due Date",
        widget=forms.DateInput(attrs={"type": "date"}),
    )

    class Meta:
        model = Quiz
        fields = [
            "title",
            "assessment_type",
            "description",
            "instructions",
            "category",
            "course",
            "module",
            "passing_score",
            "time_limit_minutes",
            "allow_multiple_attempts",
            "max_attempts",
            "allow_continue_on_fail",
            "status",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4, "class": "calendar-input"}),
            "instructions": forms.Textarea(attrs={"rows": 4, "class": "calendar-input"}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user")
        super().__init__(*args, **kwargs)
        active_company = resolve_lms_company(user)
        for field_name in ["title", "passing_score", "time_limit_minutes", "max_attempts"]:
            self.fields[field_name].widget.attrs.update({"class": "calendar-input"})
        for field_name in ["department", "assign_department", "assessment_type", "category", "course", "module", "status"]:
            self.fields[field_name].widget.attrs.update({"class": "calendar-input calendar-select"})
        self.fields["assign_due_date"].widget.attrs.update({"class": "calendar-input", "data-holiday-date-input": "true"})
        self.fields["allow_multiple_attempts"].widget.attrs.update({"class": "calendar-checkbox"})
        self.fields["allow_continue_on_fail"].widget.attrs.update({"class": "calendar-checkbox"})
        departments = Department.objects.order_by("name")
        categories = self.fields["category"].queryset.order_by("name")
        courses = self.fields["course"].queryset.order_by("title")
        modules = self.fields["module"].queryset.select_related("course").order_by("course__title", "title")
        if active_company:
            departments = departments.filter(company=active_company)
            categories = categories.filter(company=active_company)
            courses = courses.filter(company=active_company)
            modules = modules.filter(course__company=active_company)
        self.fields["department"].queryset = departments
        self.fields["assign_department"].queryset = departments
        self.fields["department"].empty_label = "Select Department"
        self.fields["assign_department"].empty_label = "Select Department"
        self.fields["department"].label_from_instance = lambda department: department.name
        self.fields["assign_department"].label_from_instance = lambda department: department.name
        self.fields["category"].queryset = categories
        self.fields["course"].queryset = courses
        self.fields["module"].queryset = modules

    def clean(self):
        cleaned_data = super().clean()
        department = cleaned_data.get("department")
        course = cleaned_data.get("course")
        module = cleaned_data.get("module")
        assign_department = cleaned_data.get("assign_department")
        if module and not course:
            cleaned_data["course"] = module.course
            self.instance.course = module.course
            course = module.course
        if course and module and module.course_id != course.id:
            self.add_error("module", "Choose a module that belongs to the selected course.")
        if department and course and course.department_id and course.department_id != department.id:
            self.add_error("course", "Choose a course from the selected department.")
        if department and module and module.course.department_id and module.course.department_id != department.id:
            self.add_error("module", "Choose a module from the selected department.")
        if department and not course:
            self.add_error("course", "Choose the course inside the selected department before saving this quiz.")
        quiz_department = None
        if module and module.course.department_id:
            quiz_department = module.course.department
        elif course and course.department_id:
            quiz_department = course.department
        elif department:
            quiz_department = department
        if assign_department and quiz_department and assign_department.id != quiz_department.id:
            self.add_error("assign_department", "Assign the quiz only to the same department as the selected quiz course.")
        return cleaned_data


class QuizAssignmentForm(forms.ModelForm):
    learners = forms.ModelMultipleChoiceField(
        queryset=User.objects.none(),
        required=False,
        widget=forms.SelectMultiple(),
        label="Selected Learners",
    )

    class Meta:
        model = QuizAssignment
        fields = ["quiz", "department", "due_date"]
        widgets = {
            "due_date": forms.DateInput(attrs={"type": "date"}),
        }
        labels = {
            "department": "Department",
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user")
        super().__init__(*args, **kwargs)
        active_company = resolve_lms_company(user)
        self.fields["quiz"].widget.attrs.update({"class": "calendar-input calendar-select"})
        self.fields["department"].widget.attrs.update({"class": "calendar-input calendar-select"})
        self.fields["due_date"].widget.attrs.update({"class": "calendar-input", "data-holiday-date-input": "true"})
        self.fields["learners"].widget.attrs.update({"class": "calendar-input", "size": "8"})
        # Querysets are scoped so HR only sees what their company/department should manage.
        quizzes = Quiz.objects.select_related("course", "module")
        departments = Department.objects.select_related("company")
        learners = User.objects.select_related("department", "company").filter(role=User.Role.LEARNER)
        if active_company:
            quizzes = quizzes.filter(company=active_company)
            departments = departments.filter(company=active_company)
            learners = learners.filter(company=active_company)
        if user.role == User.Role.HR_MANAGER and user.department_id:
            quizzes = quizzes.filter(
                Q(course__department=user.department)
                | Q(course__department__isnull=True)
                | Q(module__course__department=user.department)
                | Q(module__course__department__isnull=True)
                | Q(course__isnull=True, module__isnull=True)
            ).distinct()
            learners = learners.filter(department=user.department)
        self.fields["quiz"].queryset = quizzes.filter(status=Quiz.Status.PUBLISHED).order_by("title")
        self.fields["department"].queryset = departments.order_by("name")
        self.fields["department"].empty_label = "Select Department"
        self.fields["department"].label_from_instance = lambda department: department.name
        self.fields["learners"].queryset = learners.order_by("first_name", "email")

    def clean(self):
        cleaned_data = super().clean()
        department = cleaned_data.get("department")
        learners = cleaned_data.get("learners")
        if not department and not learners:
            raise forms.ValidationError("Choose a department or one or more learners for this quiz assignment.")
        return cleaned_data
