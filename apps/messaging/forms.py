"""Messaging forms.

This file powers the "new message" screen:
- user enters To / CC / BCC / Sector
- form resolves typed names/emails/IDs into real User records
- view creates the needed conversations/messages
"""
from django import forms

from apps.accounts.models import User
from apps.organizations.models import Department


class ConversationCreateForm(forms.Form):
    recipients = forms.ModelMultipleChoiceField(queryset=User.objects.none(), required=False, widget=forms.MultipleHiddenInput())
    to_lookup = forms.CharField(
        label="To",
        max_length=255,
        help_text="Type @username, employee ID, or email. Use commas for multiple people.",
        widget=forms.TextInput(attrs={"placeholder": "@sachin"}),
    )
    cc_lookup = forms.CharField(
        label="CC",
        max_length=255,
        required=False,
        help_text="Optional visible copy recipients.",
        widget=forms.TextInput(attrs={"placeholder": "@alex, @maria"}),
    )
    bcc_lookup = forms.CharField(
        label="BCC",
        max_length=255,
        required=False,
        help_text="Optional hidden copy recipients.",
        widget=forms.TextInput(attrs={"placeholder": "@hidden.user"}),
    )
    department = forms.ModelChoiceField(queryset=Department.objects.none(), required=False, label="Sector")
    subject = forms.CharField(max_length=255, required=False, widget=forms.TextInput(attrs={"placeholder": "Optional subject"}))
    initial_message = forms.CharField(widget=forms.Textarea(attrs={"rows": 4}), required=False)

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user")
        super().__init__(*args, **kwargs)
        queryset = User.objects.select_related("department", "company").exclude(id=user.id)
        if user.company_id:
            queryset = queryset.filter(company=user.company)
        if not user.is_manager_like and user.department_id:
            queryset = queryset.filter(department=user.department)
        self.fields["recipients"].queryset = queryset
        departments = Department.objects.select_related("company")
        if user.company_id:
            departments = departments.filter(company=user.company)
        if not user.is_manager_like and user.department_id:
            departments = departments.filter(id=user.department_id)
        self.fields["department"].queryset = departments.order_by("name")
        self.user = user

    def _resolve_lookup_list(self, lookup_value):
        # This is what lets users type @username or email instead of picking raw database IDs.
        queryset = self.fields["recipients"].queryset
        users = []
        tokens = [token.strip() for token in (lookup_value or "").split(",") if token.strip()]
        for token in tokens:
            normalized = token.lstrip("@").strip()
            user = (
                queryset.filter(username__iexact=normalized).first()
                or queryset.filter(email__iexact=normalized).first()
                or queryset.filter(employee_code__iexact=normalized).first()
                or queryset.filter(first_name__iexact=normalized).first()
            )
            if user is None:
                raise forms.ValidationError(f"User not found for '{token}'.")
            if user not in users:
                users.append(user)
        return users

    def clean(self):
        # Final cleaned_data contains resolved to_users / cc_users / bcc_users
        # so the view does not need to repeat lookup logic.
        cleaned_data = super().clean()
        department = cleaned_data.get("department")
        to_users = self._resolve_lookup_list(cleaned_data.get("to_lookup"))
        cc_users = self._resolve_lookup_list(cleaned_data.get("cc_lookup"))
        bcc_users = self._resolve_lookup_list(cleaned_data.get("bcc_lookup"))

        if department:
            sector_users = list(self.fields["recipients"].queryset.filter(department=department))
            for user in sector_users:
                if user not in to_users:
                    to_users.append(user)

        if not to_users and not cc_users and not bcc_users:
            raise forms.ValidationError("Choose at least one user or sector to message.")

        cleaned_data["to_users"] = to_users
        cleaned_data["cc_users"] = [user for user in cc_users if user not in to_users]
        cleaned_data["bcc_users"] = [user for user in bcc_users if user not in to_users and user not in cc_users]
        return cleaned_data
