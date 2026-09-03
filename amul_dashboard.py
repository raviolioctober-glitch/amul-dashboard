"""
Amul Gen-Z Survey — Interactive Dashboard
==========================================
Run with:
    pip install streamlit plotly pandas wordcloud
    streamlit run amul_dashboard.py

Place "Amul_Gen_Z_Short_Survey.csv" in the same folder as this script,
or upload it from within the app.
"""

import re
from collections import Counter

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# --------------------------------------------------------------------------
# PAGE CONFIG
# --------------------------------------------------------------------------
st.set_page_config(
    page_title="Amul Gen-Z Survey Dashboard",
    page_icon="🥛",
    layout="wide",
)

CSV_DEFAULT_PATH = "Amul_Gen_Z_Short_Survey.csv"

# Q4–Q10 rating columns, in survey order (note: the source file has two
# columns both prefixed "10)" — Brand recall and Brand Loyalty)
RATING_COLS = [
    "4) Awareness",
    "5) Emotional Connection",
    "6) Trust",
    "7) Innovation",
    "8) Digital presence",
    "9) Gen-Z Appeal",
    "10) Brand recall",
    "10) Brand Loyalty",
]

OPEN_COLS = {
    "1) What is the first word that comes to mind when you hear 'Amul'?": "Top-of-mind word",
    "2) What makes you choose Amul over other brands?": "Reason for choosing Amul",
    "3) If Amul disappeared from the market, what would you miss the most?": "What would be missed",
}

STOPWORDS = {
    "the", "a", "an", "of", "and", "to", "in", "is", "it", "for", "on",
    "with", "its", "their", "amul", "brand", "brands", "that", "this",
    "are", "be", "as", "or", "i", "my", "we", "our",
}


# --------------------------------------------------------------------------
# DATA LOADING
# --------------------------------------------------------------------------
@st.cache_data
def load_data(file) -> pd.DataFrame:
    df = pd.read_csv(file)
    df.columns = [c.strip() for c in df.columns]
    for col in RATING_COLS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    if "Timestamp" in df.columns:
        df["Timestamp"] = pd.to_datetime(df["Timestamp"], errors="coerce")
    return df


def tokenize(series: pd.Series) -> Counter:
    words = []
    for text in series.dropna().astype(str):
        for w in re.findall(r"[A-Za-z']+", text.lower()):
            if w not in STOPWORDS and len(w) > 2:
                words.append(w)
    return Counter(words)


# --------------------------------------------------------------------------
# SIDEBAR — DATA SOURCE
# --------------------------------------------------------------------------
st.sidebar.title("🥛 Amul Survey")
uploaded = st.sidebar.file_uploader("Upload survey CSV", type="csv")

if uploaded is not None:
    df = load_data(uploaded)
else:
    try:
        df = load_data(CSV_DEFAULT_PATH)
        st.sidebar.success(f"Loaded default file: {CSV_DEFAULT_PATH}")
    except FileNotFoundError:
        st.sidebar.warning("Upload the survey CSV to get started.")
        st.stop()

rating_cols_present = [c for c in RATING_COLS if c in df.columns]

st.sidebar.markdown("---")
st.sidebar.metric("Total responses", len(df))
st.sidebar.markdown("---")

selected_questions = st.sidebar.multiselect(
    "Filter rating questions (Q4–Q10)",
    options=rating_cols_present,
    default=rating_cols_present,
)
if not selected_questions:
    selected_questions = rating_cols_present

sort_choice = st.sidebar.radio(
    "Rank questions by",
    ["Mean score (desc)", "Mean score (asc)", "Consistency (low std first)"],
)

# --------------------------------------------------------------------------
# HEADER
# --------------------------------------------------------------------------
st.title("🥛 Amul Gen-Z Perception Survey — Dashboard")
st.info("This dashboard analyzes Gen Z perception of Amul across awareness, trust, innovation, and brand loyalty.")
st.caption(
    "Interactive summary of open-ended brand associations (Q1–Q3) and "
    "rated brand-health metrics (Q4–Q10)."
)

tab_overview, tab_ratings, tab_open, tab_raw = st.tabs(
    ["📊 Overview", "🏆 Q4–Q10 Ratings & Ranking", "💬 Q1–Q3 Open Responses", "🗂️ Raw Data"]
)

# --------------------------------------------------------------------------
# TAB 1 — OVERVIEW
# --------------------------------------------------------------------------
with tab_overview:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Responses", len(df))
    if rating_cols_present:
        overall_mean = df[rating_cols_present].mean().mean()
        c2.metric("Overall avg rating (1–5)", f"{overall_mean:.2f}")
        best_q = df[rating_cols_present].mean().idxmax()
        worst_q = df[rating_cols_present].mean().idxmin()
        c3.metric("Strongest metric", best_q.split(") ", 1)[-1])
        c4.metric("Weakest metric", worst_q.split(") ", 1)[-1])
        st.markdown("### 🔍 Key Insights")

best_label = best_q.split(") ", 1)[-1]
worst_label = worst_q.split(") ", 1)[-1]

st.success(f"Amul performs strongest in **{best_label}** among Gen Z respondents.")
st.warning(f"Relatively weaker perception in **{worst_label}**, indicating scope for improvement.")

    st.markdown("### Average score per question (Q4–Q10)")
    means = df[selected_questions].mean().sort_values(ascending=False)
    fig = px.bar(
        means,
        x=means.values,
        y=[c.split(") ", 1)[-1] for c in means.index],
        orientation="h",
        text=[f"{v:.2f}" for v in means.values],
        labels={"x": "Average rating (1–5)", "y": ""},
        color=means.values,
        color_continuous_scale="Blues",
    )
    fig.update_layout(coloraxis_showscale=False, yaxis=dict(autorange="reversed"))
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("### Top-of-mind words (Q1)")
    top_words = tokenize(df[list(OPEN_COLS.keys())[0]]).most_common(10)
    if top_words:
        wdf = pd.DataFrame(top_words, columns=["Word", "Count"])
        fig2 = px.bar(wdf, x="Count", y="Word", orientation="h", color="Count",
                       color_continuous_scale="Oranges")
        fig2.update_layout(coloraxis_showscale=False, yaxis=dict(autorange="reversed"))
        st.plotly_chart(fig2, use_container_width=True)

# --------------------------------------------------------------------------
# TAB 2 — Q4–Q10 RATINGS: ROW/COLUMN MATRIX + RANKING
# --------------------------------------------------------------------------
with tab_ratings:
    st.subheader("Question-level ranking (summary table)")

    summary = pd.DataFrame({
        "Question": [c.split(") ", 1)[-1] for c in selected_questions],
        "Mean": df[selected_questions].mean().values,
        "Median": df[selected_questions].median().values,
        "Std Dev": df[selected_questions].std().values,
        "Min": df[selected_questions].min().values,
        "Max": df[selected_questions].max().values,
        "Responses": df[selected_questions].count().values,
    })

    if sort_choice == "Mean score (desc)":
        summary = summary.sort_values("Mean", ascending=False)
    elif sort_choice == "Mean score (asc)":
        summary = summary.sort_values("Mean", ascending=True)
    else:
        summary = summary.sort_values("Std Dev", ascending=True)

    summary.insert(0, "Rank", range(1, len(summary) + 1))
    summary[["Mean", "Median", "Std Dev"]] = summary[["Mean", "Median", "Std Dev"]].round(2)

    st.dataframe(
        summary.style.background_gradient(subset=["Mean"], cmap="Greens")
        .background_gradient(subset=["Std Dev"], cmap="Reds_r"),
        use_container_width=True,
        hide_index=True,
    )

    st.markdown("---")
    st.subheader("Respondent × Question matrix (row = respondent, column = question)")
    st.caption(
        "Each cell is a respondent's 1–5 rating. Rightmost columns show that "
        "respondent's average and rank among all respondents."
    )

    matrix = df[selected_questions].copy()
    matrix.columns = [c.split(") ", 1)[-1] for c in matrix.columns]
    matrix.index = [f"Respondent {i+1}" for i in range(len(matrix))]
    matrix["Row Avg"] = matrix.mean(axis=1).round(2)
    matrix["Row Rank"] = matrix["Row Avg"].rank(ascending=False, method="min").astype(int)
    matrix = matrix.sort_values("Row Rank")

    st.dataframe(
        matrix.style.background_gradient(
            subset=[c for c in matrix.columns if c not in ("Row Avg", "Row Rank")],
            cmap="Blues", vmin=1, vmax=5,
        ),
        use_container_width=True,
    )

    st.markdown("---")
    st.subheader("Heatmap view")
    heat_df = df[selected_questions].copy()
    heat_df.columns = [c.split(") ", 1)[-1] for c in heat_df.columns]
    heat_df.index = [f"R{i+1}" for i in range(len(heat_df))]
    fig3 = px.imshow(
        heat_df.T,
        color_continuous_scale="RdYlGn",
        aspect="auto",
        labels=dict(x="Respondent", y="Question", color="Rating"),
        zmin=1, zmax=5,
    )
    st.plotly_chart(fig3, use_container_width=True)

    st.markdown("---")
    st.subheader("Distribution per question")
    dist_choice = st.selectbox("Choose a question", selected_questions,
                                format_func=lambda c: c.split(") ", 1)[-1])
    counts = df[dist_choice].value_counts().sort_index()
    fig4 = px.bar(
        x=counts.index.astype(str), y=counts.values,
        labels={"x": "Rating (1–5)", "y": "Number of respondents"},
        color=counts.values, color_continuous_scale="Purples",
        text=counts.values,
    )
    fig4.update_layout(coloraxis_showscale=False)
    st.plotly_chart(fig4, use_container_width=True)

    # Radar chart comparing all selected questions at once
    st.markdown("---")
    st.subheader("Radar view — all metrics at a glance")
    radar_means = df[selected_questions].mean()
    fig5 = go.Figure()
    fig5.add_trace(go.Scatterpolar(
        r=list(radar_means.values) + [radar_means.values[0]],
        theta=[c.split(") ", 1)[-1] for c in radar_means.index] + [radar_means.index[0].split(") ", 1)[-1]],
        fill="toself", name="Average rating",
    ))
    fig5.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 5])), showlegend=False)
    st.plotly_chart(fig5, use_container_width=True)

# --------------------------------------------------------------------------
# TAB 3 — OPEN-ENDED QUESTIONS (Q1–Q3)
# --------------------------------------------------------------------------
with tab_open:
    for col, label in OPEN_COLS.items():
        if col not in df.columns:
            continue
        st.subheader(f"{label}")
        colA, colB = st.columns([1, 1])

        with colA:
            st.markdown("**Most common words**")
            counts = tokenize(df[col]).most_common(10)
            if counts:
                wdf = pd.DataFrame(counts, columns=["Word", "Count"])
                figw = px.bar(wdf, x="Count", y="Word", orientation="h",
                               color="Count", color_continuous_scale="Teal")
                figw.update_layout(coloraxis_showscale=False, yaxis=dict(autorange="reversed"))
                st.plotly_chart(figw, use_container_width=True)
            else:
                st.info("No text responses.")

        with colB:
            st.markdown("**All responses**")
            st.dataframe(df[[col]].dropna().reset_index(drop=True), use_container_width=True, hide_index=True)

        st.markdown("---")

# --------------------------------------------------------------------------
# TAB 4 — RAW DATA
# --------------------------------------------------------------------------
with tab_raw:
    st.subheader("Full survey data")
    st.dataframe(df, use_container_width=True)
    st.download_button(
        "Download filtered data as CSV",
        df.to_csv(index=False).encode("utf-8"),
        file_name="amul_survey_filtered.csv",
        mime="text/csv",
    )
