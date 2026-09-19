from django.core.management.base import BaseCommand

from apps.accounts.models import User


class Command(BaseCommand):
    help = "Create or update a full-access test admin user."

    def add_arguments(self, parser):
        parser.add_argument(
            "--email",
            default="admin@example.com",
            help="Email for the test admin user.",
        )
        parser.add_argument(
            "--password",
            default="Admin@12345",
            help="Password for the test admin user.",
        )
        parser.add_argument(
            "--username",
            default="test-admin",
            help="Username for the test admin user.",
        )

    def handle(self, *args, **options):
        email = (options["email"] or "").strip().lower()
        password = options["password"]
        username = (options["username"] or "test-admin").strip()

        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                "username": username,
                "role": User.Role.SUPER_ADMIN,
                "is_superuser": True,
                "is_staff": True,
                "is_active": True,
            },
        )

        if not created:
            user.username = username or user.username
            user.role = User.Role.SUPER_ADMIN
            user.is_superuser = True
            user.is_staff = True
            user.is_active = True

        user.set_password(password)
        user.save()

        status = "created" if created else "updated"
        self.stdout.write(
            self.style.SUCCESS(
                f"Test admin {status}: email={email} password={password}"
            )
        )
