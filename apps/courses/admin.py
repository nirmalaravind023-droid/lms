from django.contrib import admin

from .models import CalendarEvent, Course, CourseAssignment, CourseComment, CourseNotification, Enrollment, Lesson, LessonProgress, Module


class ModuleInline(admin.TabularInline):
    model = Module
    extra = 0


class LessonInline(admin.TabularInline):
    model = Lesson
    extra = 0


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("title", "company", "department", "status", "mandatory", "certificate_enabled")
    list_filter = ("company", "department", "status", "mandatory")
    search_fields = ("title", "description")
    prepopulated_fields = {"slug": ("title",)}
    inlines = [ModuleInline]


@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):
    list_display = ("title", "course", "order", "is_mandatory")
    list_filter = ("course",)
    inlines = [LessonInline]


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ("title", "module", "lesson_type", "order", "is_mandatory")
    list_filter = ("lesson_type", "module")
    search_fields = ("title", "summary")


@admin.register(CourseAssignment)
class CourseAssignmentAdmin(admin.ModelAdmin):
    list_display = ("course", "department", "learner", "due_date", "is_required", "is_active")
    list_filter = ("company", "department", "is_required", "is_active")


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ("learner", "course", "status", "completion_percentage", "due_date")
    list_filter = ("status", "course")


@admin.register(LessonProgress)
class LessonProgressAdmin(admin.ModelAdmin):
    list_display = ("learner", "lesson", "status", "time_spent_seconds", "mandatory_checked")
    list_filter = ("status",)


@admin.register(CalendarEvent)
class CalendarEventAdmin(admin.ModelAdmin):
    list_display = ("title", "company", "department", "event_type", "start_at", "color")
    list_filter = ("company", "department", "event_type")


@admin.register(CourseComment)
class CourseCommentAdmin(admin.ModelAdmin):
    list_display = ("course", "author", "created_at")
    search_fields = ("body", "author__email", "author__username")


@admin.register(CourseNotification)
class CourseNotificationAdmin(admin.ModelAdmin):
    list_display = ("recipient", "actor", "course", "is_read", "created_at")
    list_filter = ("is_read",)
