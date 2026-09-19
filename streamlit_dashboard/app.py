from __future__ import annotations

import os

import pandas as pd
import plotly.express as px
import streamlit as st

try:
    from pygwalker.api.streamlit import StreamlitRenderer
except ImportError:  # pragma: no cover
    StreamlitRenderer = None


st.set_page_config(page_title="LMS Analytics", layout="wide")
st.title("LMS Analytics")
st.caption("Streamlit + Plotly dashboard entry point for admin and HR reporting.")

sample_data = pd.DataFrame(
    [
        {"department": "Civil", "completed": 42, "in_progress": 11, "avg_score": 82},
        {"department": "Electrical", "completed": 35, "in_progress": 14, "avg_score": 76},
        {"department": "Mechanical", "completed": 28, "in_progress": 9, "avg_score": 80},
    ]
)

left, right = st.columns(2)
with left:
    st.subheader("Department Completion")
    fig = px.bar(sample_data, x="department", y=["completed", "in_progress"], barmode="group")
    st.plotly_chart(fig, use_container_width=True)

with right:
    st.subheader("Average Score")
    score_fig = px.line(sample_data, x="department", y="avg_score", markers=True)
    st.plotly_chart(score_fig, use_container_width=True)

st.subheader("Tabular Analytics")
st.dataframe(sample_data, use_container_width=True)

if StreamlitRenderer is not None:
    st.subheader("Ad-Hoc Analysis")

    @st.cache_resource
    def get_pyg_renderer():
        return StreamlitRenderer(sample_data)

    renderer = get_pyg_renderer()
    renderer.render_explore()
else:
    st.info("Install PyGWalker to enable drag-and-drop exploration.")

st.caption(f"Database host configured for: {os.getenv('POSTGRES_HOST', '127.0.0.1')}")
