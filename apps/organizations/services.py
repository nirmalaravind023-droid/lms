"""Organization helper functions.

This file seeds the default sector list so registration, course creation,
and assignments always have department options ready to use.
"""
from apps.organizations.models import Department


DEFAULT_SECTORS = [
    ("HR", "Human Resources (HR)", "#2563eb", "Onboarding, employee training, upskilling, and performance management."),
    ("SALES", "Sales and Marketing", "#f97316", "Product knowledge, sales skills, and sales rep onboarding."),
    ("COMPLIANCE", "Compliance and Legal", "#dc2626", "Mandatory compliance, anti-harassment, security, and safety training."),
    ("IT", "IT / Technical Teams", "#0f766e", "Technical training, software rollout, and certification programs."),
    ("SUPPORT", "Customer Support", "#7c3aed", "Customer service, support workflows, and troubleshooting skills."),
    ("CUSTOMER", "Customer Education / Training", "#0891b2", "Client onboarding and customer success education."),
    ("PARTNER", "Partner / Franchisee Training", "#9333ea", "Partner enablement, franchise operations, and brand guidelines."),
    ("HEALTH", "Healthcare", "#16a34a", "Clinical training, healthcare compliance, and medical procedure updates."),
    ("RETAIL", "Retail", "#ea580c", "Rapid onboarding, product training, and store operations."),
    ("MANUFACT", "Manufacturing", "#475569", "Machine operations, quality, and safety procedures."),
    ("FINANCE", "Finance / Banking", "#1d4ed8", "Regulatory compliance and financial product knowledge."),
    ("GOV", "Government / Public Sector", "#334155", "Policy, compliance, and public-sector program training."),
]


def ensure_default_departments(company):
    # Safe helper: creates sectors only if they do not already exist.
    departments = []
    for code, name, color, description in DEFAULT_SECTORS:
        department, _ = Department.objects.get_or_create(
            company=company,
            code=code,
            defaults={
                "name": name,
                "color": color,
                "description": description,
            },
        )
        departments.append(department)
    return departments
