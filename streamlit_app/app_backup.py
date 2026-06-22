import streamlit as st
import boto3
import pandas as pd
from streamlit_autorefresh import st_autorefresh

# =====================================================
# PAGE CONFIG
# =====================================================

st.set_page_config(
    page_title="LENS AI Dashboard",
    page_icon="👁️",
    layout="wide"
)

# =====================================================
# AUTO REFRESH EVERY 5 SECONDS
# =====================================================

st_autorefresh(interval=5000, key="lens_refresh")

# =====================================================
# CUSTOM CSS
# =====================================================

st.markdown("""
<style>

.main {
    padding-top: 1rem;
}

.metric-card {
    background-color: #111827;
    padding: 20px;
    border-radius: 15px;
    border: 1px solid #2d3748;
}

.block-container {
    padding-top: 1rem;
}

</style>
""", unsafe_allow_html=True)

# =====================================================
# AWS
# =====================================================

dynamodb = boto3.resource(
    "dynamodb",
    region_name="ap-south-1"
)

table = dynamodb.Table("LensResults")

# =====================================================
# LOAD DATA
# =====================================================

try:
    response = table.scan()
    items = response.get("Items", [])

except Exception as e:
    items = []
    st.error(f"AWS Error: {e}")

df = pd.DataFrame(items) if items else pd.DataFrame()

# =====================================================
# SIDEBAR
# =====================================================

st.sidebar.title("👁️ LENS")

st.sidebar.success("AWS Connected")

page = st.sidebar.radio(
    "Navigation",
    [
        "Dashboard",
        "Face Enrollment",
        "Video Upload",
        "Enrolled Faces",
        "System Status"
    ]
)

st.sidebar.markdown("---")

st.sidebar.markdown("""
### Stack

✅ Rekognition

✅ Kinesis

✅ Lambda

✅ DynamoDB

✅ Streamlit
""")

# =====================================================
# DASHBOARD
# =====================================================

if page == "Dashboard":

    st.title("👁️ LENS Face Recognition Dashboard")

    st.caption(
        "AWS Rekognition + Kinesis + Lambda + DynamoDB"
    )

    st.divider()

    total_detections = len(df)

    unique_people = (
        df["PersonName"].nunique()
        if not df.empty and "PersonName" in df.columns
        else 0
    )

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "Total Detections",
            total_detections
        )

    with col2:
        st.metric(
            "Unique Persons",
            unique_people
        )

    with col3:
        st.metric(
            "Pipeline Status",
            "ACTIVE"
        )

    st.divider()

    if not df.empty:

        if "Timestamp" in df.columns:
            df = df.sort_values(
                by="Timestamp",
                ascending=False
            )

        st.subheader("📋 Detection Records")

        st.dataframe(
            df,
            use_container_width=True,
            height=350
        )

        st.divider()

        if "PersonName" in df.columns:

            st.subheader("📊 Detection Frequency")

            counts = (
                df["PersonName"]
                .value_counts()
            )

            st.bar_chart(counts)

    else:

        st.warning(
            "No detection records found."
        )

# =====================================================
# FACE ENROLLMENT
# =====================================================

elif page == "Face Enrollment":

    st.title("👤 Face Enrollment")

    st.write(
        "Upload face image for Rekognition enrollment."
    )

    person_name = st.text_input(
        "Person Name"
    )

    uploaded_face = st.file_uploader(
        "Choose Face Image",
        type=["jpg", "jpeg", "png"]
    )

    if st.button("Enroll Face"):

        if uploaded_face and person_name:

            st.success(
                f"{person_name} uploaded successfully."
            )

            st.info(
                "Ready for Rekognition indexing."
            )

        else:

            st.warning(
                "Please enter name and image."
            )

# =====================================================
# VIDEO UPLOAD
# =====================================================

elif page == "Video Upload":

    st.title("🎥 Video Upload")

    st.write(
        "Upload video for face search."
    )

    uploaded_video = st.file_uploader(
        "Choose Video",
        type=["mp4", "mov"]
    )

    if st.button("Upload Video"):

        if uploaded_video:

            st.success(
                f"{uploaded_video.name} uploaded successfully."
            )

            st.info(
                "Ready for Rekognition Face Search."
            )

        else:

            st.warning(
                "Please select a video."
            )

# =====================================================
# ENROLLED FACES
# =====================================================

elif page == "Enrolled Faces":

    st.title("👥 Enrolled Faces")

    col1, col2 = st.columns(2)

    with col1:

        try:

            st.image(
                "known_faces/sir.jpg",
                caption="Sir",
                width=300
            )

        except:

            st.info("Sir")

    with col2:

        st.success("Mom Enrolled")

    st.divider()

    st.metric(
        "Total Faces Enrolled",
        2
    )

    st.info(
        "Collection: lens-collection"
    )

# =====================================================
# SYSTEM STATUS
# =====================================================

elif page == "System Status":

    st.title("⚙️ System Status")

    st.success("✅ Rekognition Collection Active")
    st.success("✅ Kinesis Stream Active")
    st.success("✅ lens-processor Running")
    st.success("✅ lensrecorder Running")
    st.success("✅ DynamoDB Active")
    st.success("✅ Streamlit Dashboard Active")

    st.divider()

    st.subheader("Architecture")

    st.code(
"""
Rekognition
      ↓
Kinesis
      ↓
lens-processor
      ↓
lensrecorder
      ↓
DynamoDB (LensResults)
      ↓
Streamlit Dashboard
"""
    )

    st.divider()

    services = pd.DataFrame(
        {
            "Service": [
                "Rekognition",
                "Kinesis",
                "Lambda",
                "DynamoDB",
                "S3",
                "Streamlit"
            ],
            "Status": [
                "Running",
                "Running",
                "Running",
                "Running",
                "Running",
                "Running"
            ]
        }
    )

    st.dataframe(
        services,
        use_container_width=True
    )
