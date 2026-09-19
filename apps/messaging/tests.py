from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.messaging.models import Conversation, ConversationParticipant, Message
from apps.organizations.models import Company, Department


class MessagingFlowTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Demo Company", company_code="DEMO")
        self.department = Department.objects.create(company=self.company, name="Sales", code="SAL")
        self.other_department = Department.objects.create(company=self.company, name="Support", code="SUP")
        self.sender = User.objects.create_user(
            username="sender",
            email="sender@example.com",
            password="pass1234",
            company=self.company,
            department=self.department,
            role=User.Role.HR_MANAGER,
        )
        self.recipient = User.objects.create_user(
            username="recipient",
            email="recipient@example.com",
            password="pass1234",
            company=self.company,
            department=self.department,
            role=User.Role.LEARNER,
        )
        self.other_contact = User.objects.create_user(
            username="other",
            email="other@example.com",
            password="pass1234",
            company=self.company,
            department=self.other_department,
            role=User.Role.LEARNER,
        )

    def test_create_direct_message_creates_conversation_and_message(self):
        self.client.force_login(self.sender)

        response = self.client.post(
            reverse("conversation-create"),
            data={
                "to_lookup": "@recipient",
                "cc_lookup": "",
                "bcc_lookup": "",
                "subject": "",
                "initial_message": "Hello from HR",
            },
        )

        self.assertEqual(response.status_code, 302)
        conversation = Conversation.objects.get()
        self.assertTrue(conversation.is_direct)
        self.assertEqual(conversation.participants.count(), 2)
        self.assertTrue(Message.objects.filter(conversation=conversation, body="Hello from HR").exists())

    def test_opening_conversation_marks_membership_as_read(self):
        conversation = Conversation.objects.create(company=self.company, title="HR / Learner", is_direct=True)
        ConversationParticipant.objects.create(conversation=conversation, user=self.sender, last_read_at=timezone.now())
        recipient_membership = ConversationParticipant.objects.create(conversation=conversation, user=self.recipient)
        Message.objects.create(conversation=conversation, sender=self.sender, body="Please review")

        self.client.force_login(self.recipient)
        response = self.client.get(reverse("conversation-detail", kwargs={"conversation_id": conversation.id}))

        self.assertEqual(response.status_code, 200)
        recipient_membership.refresh_from_db()
        self.assertIsNotNone(recipient_membership.last_read_at)

    def test_conversation_list_filters_contacts_by_selected_department_for_manager(self):
        self.client.force_login(self.sender)

        response = self.client.get(reverse("conversation-list"), {"department": str(self.other_department.id)})

        self.assertEqual(response.status_code, 200)
        contacts = list(response.context["contacts"])
        self.assertEqual(contacts, [self.other_contact])
