"""Forms for user creation, registration, and login.

Beginner map:
- Forms validate browser input
- Views use these forms
- On success, the form creates/updates a User model record
"""
from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserChangeForm, UserCreationForm
from django.core.exceptions import ValidationError
from django.db.models import Q

from .models import User, UserLifecycleRequest
from apps.organizations.models import Company, Department


class LMSUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = (
            "email",
            "username",
            "first_name",
            "last_name",
            "company",
            "department",
            "role",
        )


class LMSUserChangeForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = User
        fields = (
            "email",
            "username",
            "first_name",
            "last_name",
            "company",
            "department",
            "role",
            "is_active",
            "is_staff",
        )


class LMSAuthenticationForm(AuthenticationForm):
    # This replaces Django's default username-only label with a friendlier multi-login label.
    username = forms.CharField(
        label="Email / Username / Phone",
        widget=forms.TextInput(
            attrs={
                "autofocus": True,
                "placeholder": "Enter email, username, or phone number",
            }
        ),
    )

    password = forms.CharField(
        label="Password",
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                "autocomplete": "current-password",
                "placeholder": "Enter password",
            }
        ),
    )

    pending_approval_message = None

    def _find_user_by_identifier(self, identifier):
        identifier = (identifier or "").strip()
        if not identifier:
            return None
        return (
            User.objects.filter(
                Q(email__iexact=identifier)
                | Q(username__iexact=identifier)
                | Q(phone_number__iexact=identifier)
            )
            .distinct()
            .first()
        )

    def clean(self):
        username = self.cleaned_data.get("username")
        password = self.cleaned_data.get("password")
        user = self._find_user_by_identifier(username)
        if user and password and user.check_password(password) and not user.is_active:
            pending_request = UserLifecycleRequest.objects.filter(
                target_user=user,
                action=UserLifecycleRequest.Action.REGISTRATION_APPROVAL,
                status=UserLifecycleRequest.Status.PENDING,
            ).select_related("requested_department", "target_user__department", "target_user__company").first()
            if pending_request:
                department = pending_request.requested_department or user.department
                company = user.company or getattr(department, "company", None)
                self.pending_approval_message = {
                    "title": "Please Wait For HR Approval",
                    "body": "Your registration was received, but your account is still pending approval.",
                    "email": user.email,
                    "department": department.name if department else "",
                    "company": company.name if company else "",
                    "note": "You can sign in after HR or your manager approves your account.",
                }
                raise ValidationError(
                    "Your account is pending HR approval. Please wait until HR or your manager approves your account before signing in.",
                    code="pending_approval",
                )
            raise ValidationError(
                "Your account is inactive. Please contact your administrator.",
                code="inactive",
            )
        return super().clean()


class RegistrationForm(UserCreationForm):
    # Registration is learner-focused in this LMS. HR/manager management happens elsewhere.
    department = forms.ModelChoiceField(queryset=Department.objects.none(), empty_label=None)
    phone_number = forms.CharField(max_length=30, required=False)
    employee_code = forms.CharField(max_length=50, required=False)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = (
            "first_name",
            "last_name",
            "email",
            "username",
            "employee_code",
            "phone_number",
            "department",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        demo_company = Company.objects.filter(is_active=True, name__iexact="Demo Company").order_by("name").first()
        self.company = demo_company or Company.objects.filter(is_active=True).order_by("name").first()
        self.fields["employee_code"].widget = forms.HiddenInput()
        self.fields["first_name"].label = "First name"
        self.fields["last_name"].label = "Last name"
        self.fields["email"].label = "Email"
        self.fields["username"].label = "Username"
        self.fields["phone_number"].label = "Phone number"
        self.fields["password1"].label = "Password"
        self.fields["password2"].label = "Confirm password"
        self.fields["username"].help_text = "Use this username or your email after HR or a manager approves the account."
        self.fields["phone_number"].help_text = "Optional, but useful for office contact and employee verification."
        self.fields["password1"].help_text = "Create the password you will use after approval."
        self.fields["password2"].help_text = "Enter the same password again to confirm it."
        departments = Department.objects.select_related("company").filter(company__is_active=True)
        if self.company:
            departments = departments.filter(company=self.company)
        departments = departments.order_by("company__name", "name")
        department_list = list(departments)
        self.fields["department"].queryset = Department.objects.filter(id__in=[department.id for department in department_list]).order_by("name")
        self.fields["department"].label_from_instance = lambda department: department.name
        self.fields["department"].label = "Department / Sector"
        self.fields["department"].help_text = (
            "Choose the department already created by HR or a manager."
            " Select the sector you belong to from the dropdown."
            " Your account will stay pending until HR or a manager approves you as an employee."
        )

    def _alpha_sequence(self, index):
        letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        value = index
        output = ""
        while True:
            value, remainder = divmod(value, 26)
            output = letters[remainder] + output
            if value == 0:
                return output
            value -= 1

    def _name_token(self, first_name, last_name, username):
        source = (first_name or last_name or username or "USER").upper()
        cleaned = "".join(char for char in source if char.isalpha())
        return (cleaned[:4] or "USER").ljust(4, "X")

    def _generate_employee_code(self, company_code, department_code, first_name, last_name, username):
        existing_count = User.objects.filter(company__company_code=company_code.upper()).count()
        sequence_number = existing_count + 1
        alpha_prefix = self._alpha_sequence((sequence_number - 1) // 9999)
        sector_token = (department_code or "GEN")[:4].upper()
        name_token = self._name_token(first_name, last_name, username)
        while True:
            serial = ((sequence_number - 1) % 9999) + 1
            candidate = f"{alpha_prefix}-{sector_token}-{name_token}-{serial:04d}"
            if not User.objects.filter(employee_code=candidate).exists():
                return candidate
            sequence_number += 1

    def clean(self):
        cleaned_data = super().clean()
        department = cleaned_data.get("department")
        if self.company and department and department.company_id != self.company.id:
            self.add_error("department", "Choose a department from Demo Company.")
        return cleaned_data

    def clean_email(self):
        email = (self.cleaned_data.get("email") or "").strip().lower()
        if email and User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("This email is already registered.")
        return email

    def clean_username(self):
        username = (self.cleaned_data.get("username") or "").strip()
        if username and User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("This username is already taken.")
        return username

    def clean_phone_number(self):
        phone_number = (self.cleaned_data.get("phone_number") or "").strip()
        if phone_number and User.objects.filter(phone_number=phone_number).exists():
            raise forms.ValidationError("This phone number is already registered.")
        return phone_number

    def save(self, commit=True):
        # Registration always attaches the user to the single active company.
        company = self.company
        if company is None:
            raise forms.ValidationError("Choose a valid department created by HR or a manager before registering.")
        department = self.cleaned_data["department"]
        user = super().save(commit=False)
        user.company = company
        user.department = department
        user.role = User.Role.LEARNER
        user.is_active = False
        user.employee_code = ""
        if commit:
            user.save()
        return user


class UserTransferForm(forms.Form):
    department = forms.ModelChoiceField(
        queryset=Department.objects.none(),
        label="New Department",
        widget=forms.Select(attrs={"class": "calendar-input calendar-select"}),
    )
    note = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 2, "class": "calendar-input", "placeholder": "Optional transfer note"}),
    )

    def __init__(self, *args, **kwargs):
        company = kwargs.pop("company", None)
        super().__init__(*args, **kwargs)
        departments = Department.objects.all().order_by("name")
        if company:
            departments = departments.filter(company=company)
        self.fields["department"].queryset = departments


class UserLifecycleRequestForm(forms.Form):
    note = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 2}))
