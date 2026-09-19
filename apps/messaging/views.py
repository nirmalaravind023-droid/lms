"""Messaging views.

Flow:
- ConversationListView shows inbox + contacts
- ConversationCreateView builds a new conversation
- ConversationDetailView loads the chat thread and marks it read
"""
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Prefetch, Q
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.views.generic import DetailView, FormView, ListView

from apps.accounts.models import User
from apps.common.pagination import build_pagination_context, paginate_items

from .forms import ConversationCreateForm
from .models import Conversation, ConversationParticipant, Message


class ConversationListView(LoginRequiredMixin, ListView):
    template_name = "messaging/conversation_list.html"
    context_object_name = "conversations"
    paginate_by = 10

    def get_queryset(self):
        # Search works across conversation title plus participant identity fields.
        search = self.request.GET.get("q", "").strip()
        conversations = (
            Conversation.objects.filter(participants__user=self.request.user)
            .select_related("company")
            .prefetch_related("participants__user")
            .distinct()
            .order_by("-updated_at")
        )
        if search:
            conversations = conversations.filter(
                Q(title__icontains=search)
                | Q(participants__user__first_name__icontains=search)
                | Q(participants__user__last_name__icontains=search)
                | Q(participants__user__email__icontains=search)
                | Q(participants__user__username__icontains=search)
            ).distinct()
        for conversation in conversations:
            membership = next(
                (participant for participant in conversation.participants.all() if participant.user_id == self.request.user.id),
                None,
            )
            latest_message = conversation.messages.order_by("-created_at").first()
            conversation.has_unread = bool(
                membership
                and latest_message
                and (membership.last_read_at is None or latest_message.created_at > membership.last_read_at)
                and latest_message.sender_id != self.request.user.id
            )
        return conversations

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        search = self.request.GET.get("q", "").strip()
        selected_department = self.request.GET.get("department", "").strip()
        contacts = User.objects.select_related("department").exclude(id=user.id)
        if user.company_id:
            contacts = contacts.filter(company=user.company)
        if selected_department:
            contacts = contacts.filter(department_id=selected_department)
        if not user.is_manager_like and user.department_id:
            contacts = contacts.filter(department=user.department)
        if search:
            contacts = contacts.filter(
                Q(first_name__icontains=search)
                | Q(last_name__icontains=search)
                | Q(email__icontains=search)
                | Q(username__icontains=search)
                | Q(employee_code__icontains=search)
            )
        contacts_page = paginate_items(
            self.request,
            contacts.order_by("first_name", "email"),
            per_page=10,
            page_param="contact_page",
        )
        context["contacts"] = contacts_page["items"]
        context["contacts_page"] = contacts_page["page_obj"]
        context["contacts_page_numbers"] = contacts_page["page_numbers"]
        context["contacts_pagination_query"] = contacts_page["pagination_query"]
        context["contacts_page_param"] = contacts_page["page_param"]
        context["conversations_page"] = context["page_obj"]
        conversations_pagination = build_pagination_context(self.request, context["page_obj"])
        context["conversations_page_numbers"] = conversations_pagination["page_numbers"]
        context["conversations_pagination_query"] = conversations_pagination["pagination_query"]
        context["conversations_page_param"] = conversations_pagination["page_param"]
        context["search_query"] = search
        departments = []
        if user.company_id and user.is_manager_like:
            departments = list(user.company.departments.order_by("name"))
        context["departments"] = departments
        context["selected_department"] = selected_department
        return context


class ConversationDetailView(LoginRequiredMixin, DetailView):
    template_name = "messaging/conversation_detail.html"
    model = Conversation
    context_object_name = "conversation"
    pk_url_kwarg = "conversation_id"

    def get_queryset(self):
        return Conversation.objects.filter(participants__user=self.request.user).prefetch_related(
            Prefetch("messages", queryset=Message.objects.select_related("sender")),
            Prefetch("participants", queryset=ConversationParticipant.objects.select_related("user")),
        )

    def get_object(self, queryset=None):
        queryset = queryset or self.get_queryset()
        return get_object_or_404(queryset, id=self.kwargs["conversation_id"])

    def dispatch(self, request, *args, **kwargs):
        # Opening the thread marks it as read for unread badge logic.
        response = super().dispatch(request, *args, **kwargs)
        ConversationParticipant.objects.filter(
            conversation_id=self.kwargs["conversation_id"],
            user=request.user,
        ).update(last_read_at=timezone.now())
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        conversation_list = (
            Conversation.objects.filter(participants__user=self.request.user)
            .select_related("company")
            .prefetch_related("participants__user")
            .distinct()
            .order_by("-updated_at")
        )
        for item in conversation_list:
            membership = next(
                (participant for participant in item.participants.all() if participant.user_id == self.request.user.id),
                None,
            )
            latest_message = item.messages.order_by("-created_at").first()
            item.has_unread = bool(
                membership
                and latest_message
                and (membership.last_read_at is None or latest_message.created_at > membership.last_read_at)
                and latest_message.sender_id != self.request.user.id
            )
        context["conversation_list"] = conversation_list
        return context


class ConversationCreateView(LoginRequiredMixin, FormView):
    form_class = ConversationCreateForm
    template_name = "messaging/conversation_create.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_initial(self):
        initial = super().get_initial()
        recipient = self.request.GET.get("recipient")
        if recipient:
            target = User.objects.filter(id=recipient).first()
            if target:
                initial["to_lookup"] = f"@{target.username}"
        return initial

    def form_valid(self, form):
        initial_message = form.cleaned_data["initial_message"].strip()
        to_users = form.cleaned_data["to_users"]
        cc_users = form.cleaned_data["cc_users"]
        bcc_users = form.cleaned_data["bcc_users"]
        subject = form.cleaned_data["subject"].strip()
        department = form.cleaned_data.get("department")

        visible_users = []
        for user in to_users + cc_users:
            if user not in visible_users:
                visible_users.append(user)

        if len(visible_users) == 1 and not cc_users and not department:
            recipient = visible_users[0]
            existing = (
                Conversation.objects.filter(company=self.request.user.company, is_direct=True, participants__user=self.request.user)
                .filter(participants__user=recipient)
                .distinct()
                .first()
            )
            conversation = existing
            if conversation is None:
                conversation = Conversation.objects.create(
                    company=self.request.user.company,
                    title=f"{self.request.user.get_full_name() or self.request.user.email} / {recipient.get_full_name() or recipient.email}",
                    is_direct=True,
                )
                ConversationParticipant.objects.create(conversation=conversation, user=self.request.user)
                ConversationParticipant.objects.create(conversation=conversation, user=recipient)
            if initial_message:
                Message.objects.create(conversation=conversation, sender=self.request.user, body=initial_message)
                ConversationParticipant.objects.filter(conversation=conversation, user=self.request.user).update(last_read_at=timezone.now())
            messages.success(self.request, "Message sent.")
            return redirect("conversation-detail", conversation_id=conversation.id)

        title_parts = []
        if subject:
            title_parts.append(subject)
        elif department:
            title_parts.append(f"{department.name} message")
        else:
            title_parts.append("Group message")
        if to_users:
            title_parts.append("To: " + ", ".join(user.get_full_name() or user.email for user in to_users[:3]))
        if cc_users:
            title_parts.append("CC: " + ", ".join(user.get_full_name() or user.email for user in cc_users[:2]))
        conversation = Conversation.objects.create(
            company=self.request.user.company,
            title=" | ".join(title_parts),
            is_direct=False,
        )
        ConversationParticipant.objects.create(conversation=conversation, user=self.request.user, last_read_at=timezone.now())
        for recipient in visible_users:
            ConversationParticipant.objects.get_or_create(conversation=conversation, user=recipient)
        if initial_message:
            metadata = {
                "to": [user.get_full_name() or user.email for user in to_users],
                "cc": [user.get_full_name() or user.email for user in cc_users],
                "bcc_count": len(bcc_users),
                "department": department.name if department else "",
                "subject": subject,
            }
            Message.objects.create(
                conversation=conversation,
                sender=self.request.user,
                body=initial_message,
                metadata=metadata,
            )
        for recipient in bcc_users:
            direct_conversation = Conversation.objects.create(
                company=self.request.user.company,
                title=subject or f"Private message from {self.request.user.get_full_name() or self.request.user.email}",
                is_direct=True,
            )
            ConversationParticipant.objects.create(conversation=direct_conversation, user=self.request.user, last_read_at=timezone.now())
            ConversationParticipant.objects.create(conversation=direct_conversation, user=recipient)
            if initial_message:
                Message.objects.create(
                    conversation=direct_conversation,
                    sender=self.request.user,
                    body=initial_message,
                    metadata={"bcc_copy": True, "subject": subject},
                )
        messages.success(self.request, "Message sent.")
        return redirect("conversation-detail", conversation_id=conversation.id)
