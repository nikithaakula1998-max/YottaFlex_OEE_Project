
"""YottaFlex Manufacturing OEE Analytics Dashboard."""

import os
import json

import pandas as pd
import requests
import streamlit as st


st.set_page_config(
    page_title="YottaFlex | Manufacturing OEE Analytics",
    page_icon="🏭",
    layout="wide",
)

DEFAULT_API = os.getenv("OEE_API_URL", "http://127.0.0.1:8000")

st.sidebar.title("🏭 YottaFlex OEE")
api_url = st.sidebar.text_input(
    "Backend API",
    value=DEFAULT_API,
).rstrip("/")


@st.cache_data(ttl=60, show_spinner=False)
def fetch_data(base_url, endpoint):
    """Retrieve JSON from the FastAPI backend."""
    response = requests.get(
        f"{base_url}{endpoint}",
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def get_data(endpoint):
    try:
        return fetch_data(api_url, endpoint)
    except requests.exceptions.RequestException as error:
        st.error(f"API request failed ({endpoint}): {error}")
        return None
    except ValueError:
        st.error(f"Invalid JSON returned by {endpoint}")
        return None


def as_dataframe(records):
    if isinstance(records, list):
        return pd.DataFrame(records)
    return pd.DataFrame()


def show_records(records, title, max_rows=30):
    st.subheader(title)
    if not records:
        st.info("No records available.")
        return

    st.caption(f"Showing {min(len(records), max_rows)} of {len(records)} records")
    st.dataframe(
        pd.DataFrame(records[:max_rows]),
        use_container_width=True,
        hide_index=True,
    )


def to_percent(value):
    """Convert a fractional OEE metric to a percentage."""
    try:
        number = float(value)
        return number * 100 if 0 <= number <= 1 else number
    except (ValueError, TypeError):
        return 0.0


ANOMALY_EXPLANATIONS = {
    "OVERLAPPING_STATE": (
        "Two machine-state events overlap in time. "
        "The affected record should be flagged to avoid "
        "incorrect running-time calculations."
    ),
    "NEGATIVE_COUNT_WITHOUT_CORRECTION": (
        "A negative production count has no valid correction "
        "reference. It requires investigation."
    ),
    "SCRAP_EXCEEDS_TOTAL": (
        "Scrap quantity exceeds the recorded production total. "
        "This makes quality calculations unreliable."
    ),
    "WRONG_IDEAL_CYCLE_TIME": (
        "The observed ideal cycle time differs from the expected "
        "machine-product configuration."
    ),
    "DOWNTIME_OVERLAPS_BREAK": (
        "A downtime event overlaps a planned break, potentially "
        "causing downtime to be counted incorrectly."
    ),
}


st.title("🏭 Manufacturing OEE Analytics")
st.caption(
    "Machine effectiveness, production efficiency, "
    "quality monitoring and data reliability"
)

health = get_data("/health")

if health is None:
    st.warning("Start the FastAPI backend on port 8000.")
    st.stop()

if not health.get("dataset_ready", False):
    st.error("Backend is reachable, but the SQLite dataset is not ready.")
    st.stop()

st.sidebar.success("Backend connected")
st.sidebar.caption("Data source: SQLite via FastAPI")

if st.sidebar.button("Refresh dashboard"):
    fetch_data.clear()
    st.rerun()

summary = get_data("/summary")
machines = get_data("/machines")
oee_records = get_data("/oee")
anomalies = get_data("/anomalies")

if any(
    result is None
    for result in (summary, machines, oee_records, anomalies)
):
    st.error("Some API requests failed. Dashboard data is incomplete.")
    st.stop()

if not isinstance(summary, dict):
    st.error("Unexpected summary response.")
    st.stop()

if not all(
    isinstance(result, list)
    for result in (machines, oee_records, anomalies)
):
    st.error("Unexpected API record format.")
    st.stop()

oee_df = as_dataframe(oee_records)
machine_df = as_dataframe(machines)

if oee_df.empty:
    st.warning("No OEE records available.")
    st.stop()

required_columns = [
    "machine_id",
    "shift_id",
    "availability",
    "performance",
    "quality",
    "oee",
]

missing_columns = [
    column for column in required_columns
    if column not in oee_df.columns
]

if missing_columns:
    st.error(f"Missing OEE columns: {missing_columns}")
    st.stop()

for column in [
    "availability",
    "performance",
    "quality",
    "oee",
]:
    oee_df[column] = pd.to_numeric(
        oee_df[column],
        errors="coerce",
    )

st.divider()

machine_count = summary.get("machines", len(machines))
shift_count = summary.get("machine_shifts", len(oee_records))
average_oee = to_percent(summary.get("average_oee", 0))
anomaly_count = len(anomalies)

col1, col2, col3, col4 = st.columns(4)

col1.metric("Machines", f"{machine_count:,}")
col2.metric("Machine shifts", f"{shift_count:,}")
col3.metric("Average OEE", f"{average_oee:.2f}%")
col4.metric("Known anomalies", anomaly_count)

st.divider()

st.subheader("🔎 Machine Performance Explorer")

machine_ids = sorted(
    oee_df["machine_id"].dropna().astype(str).unique()
)

selected_machine = st.selectbox(
    "Select machine",
    ["All machines"] + machine_ids,
)

if selected_machine == "All machines":
    filtered_df = oee_df.copy()
else:
    filtered_df = oee_df[
        oee_df["machine_id"].astype(str) == selected_machine
    ].copy()

st.caption(
    f"Showing analytics for {len(filtered_df):,} "
    "machine-shift records"
)

st.subheader("📊 OEE Component Analysis")

component_columns = [
    "availability",
    "performance",
    "quality",
    "oee",
]

component_means = (
    filtered_df[component_columns].mean() * 100
)

metric_cols = st.columns(4)

for index, column in enumerate(component_columns):
    value = component_means[column]
    metric_cols[index].metric(
        column.replace("_", " ").title(),
        f"{value:.2f}%" if pd.notna(value) else "N/A",
    )

st.bar_chart(
    component_means.rename("Percentage"),
    y_label="Percentage (%)",
)

st.caption(
    "These values are averages of individual OEE components. "
    "Average OEE is not necessarily equal to the product "
    "of the average components."
)

st.divider()

st.subheader("🏭 Machine-wise OEE Comparison")

machine_comparison = (
    oee_df.groupby("machine_id", as_index=False)["oee"]
    .mean()
)

machine_comparison["oee_percent"] = (
    machine_comparison["oee"] * 100
)

machine_comparison = machine_comparison.sort_values(
    "oee_percent",
    ascending=False,
)

st.bar_chart(
    machine_comparison.set_index("machine_id")[
        "oee_percent"
    ],
    y_label="Average OEE (%)",
)

with st.expander("View machine ranking"):
    st.dataframe(
        machine_comparison[
            ["machine_id", "oee_percent"]
        ].rename(
            columns={"oee_percent": "Average OEE (%)"}
        ),
        use_container_width=True,
        hide_index=True,
    )

st.divider()

st.subheader("📈 OEE Trend by Shift")

if "shift_id" in filtered_df.columns:
    trend = (
        filtered_df.groupby("shift_id")["oee"]
        .mean()
        .sort_index()
        * 100
    )

    st.line_chart(
        trend,
        y_label="Average OEE (%)",
        x_label="Shift ID",
    )

    st.caption(
        "Shift IDs are sorted lexicographically. "
        "This chart is exploratory and does not replace "
        "a timestamp-based time-series analysis."
    )

st.divider()

st.subheader("⚠️ Known Data Quality Anomalies")

st.info(
    "These are ground-truth labels from the synthetic generator, "
    "not anomalies independently discovered by this dashboard."
)

if anomalies:
    anomaly_df = pd.DataFrame(anomalies)

    if "issue_type" in anomaly_df.columns:
        counts = anomaly_df["issue_type"].value_counts()
        st.bar_chart(counts, y_label="Number of anomalies")

    for index, anomaly in enumerate(anomalies, start=1):
        issue_type = str(anomaly.get("issue_type", "UNKNOWN"))
        issue_id = anomaly.get("issue_id", f"Record {index}")

        with st.expander(f"{issue_id} — {issue_type}"):
            st.write(
                ANOMALY_EXPLANATIONS.get(
                    issue_type,
                    "Review this anomaly against the validation rules.",
                )
            )
            st.write(
                "**Expected decision:**",
                anomaly.get("expected_decision", "Not specified"),
            )
            st.json(anomaly)
else:
    st.info("No labelled anomalies found.")

st.divider()

with st.expander("📋 Detailed OEE records"):
    st.caption(
        f"Displaying up to 100 of {len(filtered_df):,} "
        "filtered records"
    )
    st.dataframe(
        filtered_df.head(100),
        use_container_width=True,
        hide_index=True,
    )

with st.expander("⚙️ Machine master data"):
    st.dataframe(
        machine_df,
        use_container_width=True,
        hide_index=True,
    )

with st.expander("📁 Data generation manifest"):
    manifest = get_data("/manifest")
    if manifest is not None:
        st.json(manifest)

st.divider()

st.caption(
    "YottaFlex OEE Analytics | "
    "Streamlit → FastAPI → SQLite | "
    "Synthetic manufacturing dataset"
)
