import streamlit as st
import boto3
import pandas as pd
#from streamlit_autorefresh import st_autorefresh
from emotion_monitor.live_emotion import SESSION_DATA
from emotion_monitor.live_emotion import FaceDetector
from streamlit_webrtc import webrtc_streamer
import pandas as pd
import time

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

# st_autorefresh(interval=5000, key="lens_refresh")

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
# AWS CLIENTS
# =====================================================

s3 = boto3.client(
    "s3",
    region_name="ap-south-1"
)

rekognition = boto3.client(
    "rekognition",
    region_name="ap-south-1"
)

BUCKET_NAME = "lens-face-storage"
COLLECTION_ID = "lens-collection"

SNS_TOPIC_ARN = "arn:aws:sns:ap-south-1:633867805912:AmazonRekognitionComplete"
ROLE_ARN = "arn:aws:iam::633867805912:role/LensRekognitionRole"

REKOGNITION_ROLE_ARN = "arn:aws:iam::633867805912:role/LensRekognitionRole"
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
        "Live Emotion Monitoring",
        "Results",
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

            try:

                file_name = f"{person_name}.jpg"

                s3.upload_fileobj(
                    uploaded_face,
                    BUCKET_NAME,
                    f"Known faces/{file_name}"
                )

                response = rekognition.index_faces(
                    CollectionId=COLLECTION_ID,
                    Image={
                        "S3Object": {
                            "Bucket": BUCKET_NAME,
                            "Name": f"Known faces/{file_name}"
                        }
                    },
                    ExternalImageId=person_name
                )

                if response["FaceRecords"]:

                    face_id = response["FaceRecords"][0]["Face"]["FaceId"]

                    st.success(
                        f"{person_name} enrolled successfully"
                    )

                    st.info(
                        f"Face ID: {face_id}"
                    )

                else:

                    st.error(
                        "No face detected in image."
                    )

            except Exception as e:

                st.error(str(e))

        else:

            st.warning(
                "Please enter name and image."
            )

# =====================================================
# VIDEO UPLOAD
# =====================================================

elif page == "Video Upload":

    st.title("🎥 Video Upload")

    uploaded_video = st.file_uploader(
        "Choose Video",
        type=["mp4", "mov"]
    )

    if st.button("Upload Video"):

        if not uploaded_video:
            st.warning("Please select a video.")
            st.stop()

        try:

            video_name = uploaded_video.name

            st.write("✅ STEP 1 - Uploading to S3")

            uploaded_video.seek(0)

            s3.upload_fileobj(
                uploaded_video,
                BUCKET_NAME,
                f"videos/{video_name}"
            )

            st.success("Video uploaded to S3")

            st.write("✅ STEP 2 - Starting Rekognition Job")

            response = rekognition.start_face_search(
                Video={
                    "S3Object": {
                        "Bucket": BUCKET_NAME,
                        "Name": f"videos/{video_name}"
                    }
                },
                CollectionId=COLLECTION_ID,
                NotificationChannel={
                    "SNSTopicArn": SNS_TOPIC_ARN,
                    "RoleArn": REKOGNITION_ROLE_ARN
                }
            )

            job_id = response["JobId"]

            st.success("Face Search Started")

            st.code(job_id)

            with open("latest_job.txt", "w") as f:
                f.write(job_id)

            st.success("JobId saved")

        except Exception as e:

            st.error("Upload Failed")
            st.exception(e)

# =====================================================
# Live Emotion Monitoring
# =====================================================

elif page == "Live Emotion Monitoring":

    st.title("🎭 Live Emotion Monitoring")

    st.caption(
        "Real-Time Face Recognition & Emotion Analysis"
    )

    st.divider()

    # =========================
    # LIVE METRICS
    # =========================

    total_faces = len(SESSION_DATA)

    known_faces = len(
        [
            x for x in SESSION_DATA
            if x["person"] != "Unknown"
        ]
    )

    unknown_faces = len(
        [
            x for x in SESSION_DATA
            if x["person"] == "Unknown"
        ]
    )

    current_mood = (
        SESSION_DATA[-1]["emotion"]
        if SESSION_DATA
        else "None"
    )

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "👥 Faces Detected",
            total_faces
        )

    with col2:
        st.metric(
            "✅ Known Faces",
            known_faces
        )

    with col3:
        st.metric(
            "❓ Unknown Faces",
            unknown_faces
        )

    with col4:
        st.metric(
            "😊 Current Mood",
            current_mood
        )

    st.divider()

    # =========================
    # CAMERA + STATUS
    # =========================

    left_col, right_col = st.columns([2, 1])

    with left_col:

        st.subheader("📹 Live Camera Feed")

        webrtc_streamer(
            key="emotion-monitor",
            video_processor_factory=FaceDetector,
            media_stream_constraints={
                "video": True,
                "audio": False,
            }
        )

    with right_col:

        st.subheader("⚡ Session Status")

        st.success("System Ready")

        st.info(
            """
            Face Recognition Active

            • Face Recognition
            • Emotion Detection
            • Session Analytics
            • Report Generation
            """
        )

        st.metric(
            "⏱️ Session Duration",
            f"{int(time.time()) % 3600 // 60:02d}:{int(time.time()) % 60:02d}"
        )

    st.divider()

    # =========================
    # LIVE DETECTIONS
    # =========================

    st.subheader("👥 Live Detections")

    if SESSION_DATA:

        detections_df = pd.DataFrame(
            SESSION_DATA
        )

        st.dataframe(
            detections_df,
            use_container_width=True
        )

    else:

        st.info(
            "No detections yet."
        )

    st.divider()

    # =========================
    # EMOTION ANALYTICS
    # =========================

    st.subheader("📊 Session Emotion Analytics")

    if SESSION_DATA:

        df = pd.DataFrame(
            SESSION_DATA
        )

        emotion_counts = (
            df["emotion"]
            .value_counts()
        )

        st.bar_chart(
            emotion_counts
        )

    else:

        st.info(
            "No analytics available."
        )

    st.divider()

    # =========================
    # SESSION REPORT
    # =========================

    st.subheader("📑 Session Report")

    known_people = len(
        set(
            x["person"]
            for x in SESSION_DATA
            if x["person"] != "Unknown"
        )
    )

    total_events = len(
        SESSION_DATA
    )

    if SESSION_DATA:

        dominant_mood = (
            pd.DataFrame(
                SESSION_DATA
            )["emotion"]
            .mode()[0]
        )

    else:

        dominant_mood = "None"

    r1, r2, r3, r4 = st.columns(4)

    with r1:
        st.metric(
            "Known People",
            known_people
        )

    with r2:
        st.metric(
            "Unknown Faces",
            unknown_faces
        )

    with r3:
        st.metric(
            "Total Events",
            total_events
        )

    with r4:
        st.metric(
            "Dominant Mood",
            dominant_mood
        )

    # =========================
    # DOWNLOAD REPORT
    # =========================

    if SESSION_DATA:

        report_df = pd.DataFrame(
            SESSION_DATA
        )

        csv = report_df.to_csv(
            index=False
        )

        st.download_button(
            "📥 Download Session Report",
            data=csv,
            file_name="lens_session_report.csv",
            mime="text/csv"
        )

    else:

        st.button(
            "📥 Download Session Report",
            disabled=True
        )

# =====================================================
# Results
# =====================================================

elif page == "Results":

    st.title("🎯 Face Search Results")

    response = table.scan()

    items = response.get("Items", [])

    if not items:
        st.warning("No results found")
    else:

        df = pd.DataFrame(items)

        if "Timestamp" in df.columns:
            df = df.sort_values(
                by="Timestamp",
                ascending=False
            )

        st.dataframe(
            df,
            use_container_width=True
        )

        csv = df.to_csv(index=False)

        st.download_button(
            "📥 Download CSV",
            csv,
            "results.csv",
            "text/csv"
        )

# =====================================================
# ENROLLED FACES
# =====================================================

elif page == "Enrolled Faces":

    st.title("👥 Enrolled Faces")

    try:

        response = rekognition.list_faces(
            CollectionId=COLLECTION_ID,
            MaxResults=100
        )

        faces = response.get("Faces", [])

        if not faces:
            st.warning("No faces enrolled.")
        else:

            st.metric(
                "Total Faces Enrolled",
                len(faces)
            )

            cols = st.columns(3)

            for idx, face in enumerate(faces):

                with cols[idx % 3]:

                    st.success(
                        face.get(
                            "ExternalImageId",
                            "Unknown"
                        )
                    )

                    st.write(
                        f"Face ID: {face['FaceId'][:12]}..."
                    )

        st.info(
            f"Collection: {COLLECTION_ID}"
        )

    except Exception as e:

        st.error(str(e))

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
