# Generated manually for user lifecycle requests.

import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0002_initial"),
        ("organizations", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="UserLifecycleRequest",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("action", models.CharField(choices=[("deactivate", "Deactivate User"), ("reactivate", "Reactivate User"), ("transfer", "Transfer Department"), ("soft_delete", "Soft Delete / Reset")], max_length=30)),
                ("status", models.CharField(choices=[("pending", "Pending"), ("approved", "Approved"), ("rejected", "Rejected")], default="pending", max_length=20)),
                ("note", models.TextField(blank=True)),
                ("reviewed_at", models.DateTimeField(blank=True, null=True)),
                ("resolution_note", models.TextField(blank=True)),
                ("requested_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="requested_lifecycle_actions", to="accounts.user")),
                ("requested_department", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="requested_user_transfers", to="organizations.department")),
                ("reviewed_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="reviewed_lifecycle_actions", to="accounts.user")),
                ("target_user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="lifecycle_requests", to="accounts.user")),
            ],
            options={
                "ordering": ("-created_at",),
            },
        ),
    ]
