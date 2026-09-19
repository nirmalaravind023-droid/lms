#!/usr/bin/env python
"""Project entry point.

Beginners:
- Run this file with `python manage.py <command>`.
- Django loads `lms_portal.settings`.
- From there, URLs -> Views -> Forms/Services -> Models -> Database.
"""
import os
import sys

from dotenv import load_dotenv


def main() -> None:
    load_dotenv()
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "lms_portal.settings")
    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
