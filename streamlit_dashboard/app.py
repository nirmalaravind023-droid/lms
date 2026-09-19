from __future__ import annotations

import os
import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

try:
    from pygwalker.api.streamlit import StreamlitRenderer
except ImportError:  # pragma: no cover
    StreamlitRenderer = None


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "lms_portal.settings")


def _sample_department_data() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"department": "Civil", "completed": 42, "in_progress": 11, "avg_score": 82.0},
            {"department": "Electrical", "completed": 35, "in_progress": 14, "avg_score": 76.0},
            {"department": "Mechanical", "completed": 28, "in_progress": 9, "avg_score": 80.0},
        ]
    )


@st.cache_data(ttl=300)
def load_department_analytics() -> tuple[pd.DataFrame, str]:
    try:
        import django
        from django.db.models import Avg, Count, Q

        django.setup()

        from apps.assessments.models import QuizAttempt
        from apps.courses.models import Enrollment
        from apps.organizations.models import Department

        rows = []
        departments = Department.objects.select_related("company").order_by("company__name", "name")
        for department in departments:
            enrollments = Enrollment.objects.filter(learner__department=department)
            attempts = QuizAttempt.objects.filter(learner__department=department)
            rows.append(
                {
                    "department": f"{department.company.name} / {department.name}",
                    "completed": enrollments.filter(status=Enrollment.Status.COMPLETED).count(),
                    "in_progress": enrollments.filter(
                        Q(status=Enrollment.Status.ASSIGNED) | Q(status=Enrollment.Status.IN_PROGRESS)
                    ).count(),
                    "avg_score": float(attempts.aggregate(value=Avg("percentage"))["value"] or 0),
                    "learners": department.users.count(),
                    "attempts": attempts.count(),
                }
            )

        if not rows:
            return _sample_department_data(), "sample"
        return pd.DataFrame(rows), "live"
    except Exception as exc:  # pragma: no cover - protects standalone dashboard launches
        sample = _sample_department_data()
        sample["load_error"] = str(exc)
        return sample, "sample"


st.set_page_config(page_title="LMS analytics", layout="wide")
st.title("LMS analytics")
st.caption("Live Django LMS analytics when the app can connect to the project database; sample data is used as a fallback.")

data, source = load_department_analytics()
if source == "live":
    st.success("Using live LMS database data.")
else:
    st.warning("Using sample analytics data. Configure Django database access to show live LMS data.")

with st.container(horizontal=True):
    st.metric("Departments", len(data), border=True)
    st.metric("Completed enrollments", int(data["completed"].sum()), border=True)
    st.metric("In-progress enrollments", int(data["in_progress"].sum()), border=True)
    st.metric("Average quiz score", f"{data['avg_score'].mean():.1f}%", border=True)

left, right = st.columns(2)
with left:
    with st.container(border=True):
        st.subheader("Department completion")
        fig = px.bar(data, x="department", y=["completed", "in_progress"], barmode="group")
        st.plotly_chart(fig)

with right:
    with st.container(border=True):
        st.subheader("Average score")
        score_fig = px.line(data, x="department", y="avg_score", markers=True)
        st.plotly_chart(score_fig)

with st.container(border=True):
    st.subheader("Tabular analytics")
    st.dataframe(data, hide_index=True)

if StreamlitRenderer is not None:
    with st.container(border=True):
        st.subheader("Ad-hoc analysis")

        @st.cache_resource
        def get_pyg_renderer(_frame: pd.DataFrame):
            return StreamlitRenderer(_frame)

        renderer = get_pyg_renderer(data)
        renderer.render_explore()
else:
    st.info("Install PyGWalker to enable drag-and-drop exploration.")

st.caption(f"Database host configured for: {os.getenv('POSTGRES_HOST', '127.0.0.1')}")
