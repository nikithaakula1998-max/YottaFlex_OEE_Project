
import os
import json
import html

import requests
import streamlit as st


# ----------------------------------------
# PAGE CONFIGURATION
# ----------------------------------------

st.set_page_config(
    page_title="Factory OEE Monitor",
    page_icon="🏭",
    layout="wide"
)


# ----------------------------------------
# BACKEND CONNECTION
# ----------------------------------------

DEFAULT_API = os.getenv(
    "OEE_API_URL",
    "http://127.0.0.1:8000"
)

st.sidebar.title("🏭 Factory OEE")

api_url = st.sidebar.text_input(
    "Backend API",
    value=DEFAULT_API
).rstrip("/")


def fetch_data(endpoint):
    """Fetch JSON data from the FastAPI backend."""

    try:
        response = requests.get(
            f"{api_url}{endpoint}",
            timeout=15
        )

        response.raise_for_status()

        return response.json()

    except requests.exceptions.RequestException as error:
        st.error(
            f"Unable to fetch {endpoint}: {error}"
        )
        return None

    except ValueError:
        st.error(
            f"The backend returned invalid JSON for {endpoint}."
        )
        return None


def normalize_rows(data):
    """Convert API responses into a list of records."""

    if isinstance(data, list):
        return data

    if isinstance(data, dict):
        for key in (
            "rows",
            "data",
            "results",
            "items",
            "records"
        ):
            value = data.get(key)

            if isinstance(value, list):
                return value

    return []


def display_records(records, max_rows=30):
    """
    Display records without using Pandas or
    Streamlit's dataframe component.
    """

    if not records:
        st.info("No records available.")
        return

    st.caption(
        f"Showing {min(len(records), max_rows)} "
        f"of {len(records)} records"
    )

    for index, record in enumerate(
        records[:max_rows],
        start=1
    ):
        with st.expander(f"Record {index}"):
            st.code(
                json.dumps(
                    record,
                    indent=2,
                    default=str
                ),
                language="json"
            )


def show_metric(label, value):
    st.metric(label, value)


# ----------------------------------------
# MAIN DASHBOARD
# ----------------------------------------

st.title("🏭 Factory OEE Monitor")

st.write(
    "Monitor machine efficiency, production "
    "performance, quality and anomalies."
)

health = fetch_data("/health")

if health is None:
    st.warning(
        "Start your FastAPI backend on port 8000 "
        "before using the dashboard."
    )
    st.stop()

st.sidebar.success("Backend connected")


# ----------------------------------------
# FETCH SUMMARY
# ----------------------------------------

summary = fetch_data("/summary") or {}

machines_response = fetch_data("/machines")
oee_response = fetch_data("/oee")
anomalies_response = fetch_data("/anomalies")

machines = normalize_rows(machines_response)
oee_records = normalize_rows(oee_response)
anomalies = normalize_rows(anomalies_response)

# Support APIs that return lists directly.
if isinstance(machines_response, list):
    machines = machines_response

if isinstance(oee_response, list):
    oee_records = oee_response

if isinstance(anomalies_response, list):
    anomalies = anomalies_response


# ----------------------------------------
# SUMMARY METRICS
# ----------------------------------------

col1, col2, col3, col4 = st.columns(4)

machine_count = summary.get(
    "machines",
    len(machines)
)

shift_count = summary.get(
    "machine_shifts",
    len(oee_records)
)

average_oee = summary.get("average_oee", 0)

anomaly_count = summary.get(
    "labelled_anomalies",
    len(anomalies)
)

with col1:
    show_metric("Machines", machine_count)

with col2:
    show_metric("Machine shifts", shift_count)

with col3:
    try:
        oee_value = float(average_oee)

        # API may return a fraction or percentage.
        if 0 <= oee_value <= 1:
            oee_value *= 100

        st.metric(
            "Average OEE",
            f"{oee_value:.1f}%"
        )

    except (ValueError, TypeError):
        st.metric(
            "Average OEE",
            str(average_oee)
        )

with col4:
    show_metric(
        "Labelled anomalies",
        anomaly_count
    )


# ----------------------------------------
# MACHINE FILTER
# ----------------------------------------

st.divider()

st.subheader("Machine Filter")

machine_ids = sorted({
    str(record["machine_id"])
    for record in oee_records
    if isinstance(record, dict)
    and record.get("machine_id") is not None
})

selected_machine = st.selectbox(
    "Select machine",
    ["All machines"] + machine_ids
)

if selected_machine == "All machines":
    filtered_oee = oee_records
else:
    filtered_oee = [
        record
        for record in oee_records
        if isinstance(record, dict)
        and str(record.get("machine_id"))
        == selected_machine
    ]


# ----------------------------------------
# OEE RESULTS
# ----------------------------------------

st.divider()

st.subheader("📊 OEE by Machine and Shift")

st.info(
    "OEE = Availability × Performance × Quality"
)

display_records(filtered_oee, max_rows=30)


# ----------------------------------------
# OEE COMPONENT EXPLANATION
# ----------------------------------------

st.divider()

st.subheader("Understanding OEE")

col_a, col_b, col_c = st.columns(3)

with col_a:
    st.markdown("### Availability")
    st.write(
        "Measures how much planned production "
        "time the machine was actually running."
    )

with col_b:
    st.markdown("### Performance")
    st.write(
        "Measures how quickly the machine "
        "produced compared with its ideal speed."
    )

with col_c:
    st.markdown("### Quality")
    st.write(
        "Measures the proportion of "
        "good products produced."
    )


# ----------------------------------------
# ANOMALY MONITORING
# ----------------------------------------

st.divider()

st.subheader("⚠️ Known Anomalies")

st.write(
    "These are labelled exception cases "
    "provided by the synthetic data generator."
)

display_records(anomalies, max_rows=30)


# ----------------------------------------
# MACHINE MASTER DATA
# ----------------------------------------

st.divider()

st.subheader("⚙️ Machine Master Data")

display_records(machines, max_rows=30)


# ----------------------------------------
# SOURCE MANIFEST
# ----------------------------------------

st.divider()

st.subheader("📁 Data Generation Manifest")

manifest = fetch_data("/manifest")

if manifest is not None:
    st.json(manifest)
else:
    st.info("Manifest is not available.")


# ----------------------------------------
# FOOTER
# ----------------------------------------

st.divider()

st.caption(
    "YottaFlex OEE Project | "
    "Python + FastAPI + Streamlit"
)
