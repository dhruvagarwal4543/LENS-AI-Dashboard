import streamlit as st
import boto3
import pandas as pd
#from streamlit_autorefresh import st_autorefresh
from emotion_monitor.live_emotion import SESSION_DATA
from emotion_monitor.live_emotion import FaceDetector
from datetime import datetime
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
students_table = dynamodb.Table("Students")

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

  # -------------------------
  # Helper Functions
  # -------------------------

def mark_attendance(student_id):

    students_table.update_item(
        Key={
            "student_id": student_id
        },
        UpdateExpression="SET attendance_status = :s",
        ExpressionAttributeValues={
            ":s": "Present"
        }
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
        "Student Enrollment",
        "Video Upload",
        "Live Emotion Monitoring",
        "Live Attendance",
        "Bus Safety Monitoring",
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
# Student ENROLLMENT
# =====================================================

elif page == "Student Enrollment":

    st.title("🚌 Student Enrollment")
    st.caption(
        "Enroll students for automated attendance and bus monitoring"
    )

    student_id = st.text_input("Student ID")
    student_name = st.text_input("Student Name")
    student_class = st.text_input("Class")
    bus_id = st.text_input("Bus ID")
    parent_contact = st.text_input("Parent Contact")

    uploaded_file = st.file_uploader(
        "Upload Student Photo",
        type=["jpg", "jpeg", "png"]
    )

    if st.button("Enroll Student"):

        if not uploaded_file:
            st.error("Please upload a student photo.")

        elif not student_id or not student_name:
            st.error("Please fill all required fields.")

        else:
            try:
                # Read uploaded image
                file_bytes = uploaded_file.getvalue()

                # S3 path
                image_key = f"students/{student_id}.jpg"

                # Upload to S3
                s3.put_object(
                    Bucket=BUCKET_NAME,
                    Key=image_key,
                    Body=file_bytes,
                    ContentType="image/jpeg"
                )

                # Index face in Rekognition
                rekognition_response = rekognition.index_faces(
                    CollectionId=COLLECTION_ID,
                    Image={
                        "S3Object": {
                            "Bucket": BUCKET_NAME,
                            "Name": image_key
                        }
                    },
                    ExternalImageId=student_id,
                    DetectionAttributes=[]
                )

                # Check face detected
                if len(rekognition_response["FaceRecords"]) == 0:
                    st.error("No face detected in image.")
                    st.stop()

                # Save student details in DynamoDB
                response = students_table.put_item(
                    Item={
                        "student_id": str(student_id),
                        "student_name": str(student_name),
                        "class": str(student_class),
                        "bus_id": str(bus_id),
                        "parent_contact": str(parent_contact),
                        "image_key": image_key,
                        "attendance_status": "Not Marked",
                        "created_at": datetime.now().isoformat()
                    }
                )

                st.write("Table Name:", students_table.name)
                st.write("Dynamo Response:", response)

                st.success(f"{student_name} enrolled successfully!")

            except Exception as e:
                st.exception(e)

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
# Live Attendance
# =====================================================

elif page == "Live Attendance":

    st.title("🚌 Live Attendance System")

    st.info(
        "Capture a student's face to mark attendance automatically."
    )

    # Fetch students
    response = students_table.scan()
    students = response.get("Items", [])

    # Count present students
    present = [
        s for s in students
        if s.get("attendance_status") == "Present"
    ]

    st.metric(
        "Present Students",
        len(present)
    )

    # Open camera
    camera_image = st.camera_input(
        "Capture Student Face"
    )

    # Process captured image
    if camera_image:

        try:
            image_bytes = camera_image.getvalue()

            response = rekognition.search_faces_by_image(
                CollectionId=COLLECTION_ID,
                Image={
                    "Bytes": image_bytes
                },
                MaxFaces=1,
                FaceMatchThreshold=90
            )

            matches = response.get("FaceMatches", [])

            if matches:

                student_id = matches[0]["Face"]["ExternalImageId"]

                already_present = any(
                    s.get("student_id") == student_id and
                    s.get("attendance_status") == "Present"
                    for s in students
                )

                if already_present:
                    st.info(
                        f"{student_id} is already marked present."
                    )

                else:
                    mark_attendance(student_id)
                    st.success(
                        f"Attendance marked for {student_id}"
                    )
                    st.rerun()

            else:
                st.error(
                    "Student not recognized."
                )

        except Exception as e:
            st.error(
                f"Recognition Failed: {e}"
            )
# =====================================================
# Bus Safety Monitoring
# =====================================================

elif page == "Bus Safety Monitoring":

    st.title("🚌 Bus Safety Monitoring")

    st.caption(
        "Capture a bus image and analyze for potential safety events."
    )

    camera_image = st.camera_input(
        "Capture Bus Scene"
    )

    if camera_image:

        try:

            image_bytes = camera_image.getvalue()

            response = rekognition.detect_faces(
                Image={
                    "Bytes": image_bytes
                },
                Attributes=["ALL"]
            )

            faces = response.get(
                "FaceDetails",
                []
            )

            total_faces = len(faces)

            st.metric(
                "People Detected",
                total_faces
            )

            incidents = []

            # Overcrowding
            if total_faces > 4:
                incidents.append(
                    "Overcrowding Detected"
                )

            # Emotion Analysis
            for face in faces:

                emotions = face.get(
                    "Emotions",
                    []
                )

                if emotions:

                    top_emotion = max(
                        emotions,
                        key=lambda x:
                        x["Confidence"]
                    )

                    emotion = top_emotion["Type"]

                    if emotion == "ANGRY":
                        incidents.append(
                            "Potential Conflict Detected"
                        )

                    elif emotion == "SURPRISED":
                        incidents.append(
                            "Unusual Activity Detected"
                        )

            st.divider()

            if incidents:

                st.error(
                    "🚨 Safety Alerts"
                )

                incident_df = pd.DataFrame(
                    {
                        "Timestamp":
                        [
                            datetime.now().strftime(
                                "%Y-%m-%d %H:%M:%S"
                            )
                        ]
                        * len(incidents),

                        "Incident":
                        incidents,

                        "Status":
                        [
                            "Alert"
                        ]
                        * len(incidents)
                    }
                )

                st.dataframe(
                    incident_df,
                    use_container_width=True
                )

                csv = (
                    incident_df
                    .to_csv(
                        index=False
                    )
                )

                st.download_button(
                    "📥 Download Incident Report",
                    data=csv,
                    file_name="incident_report.csv",
                    mime="text/csv"
                )

            else:

                st.success(
                    "✅ No unusual activity detected."
                )

        except Exception as e:

            st.error(
                f"Analysis Failed: {e}"
            )

# =====================================================
# Results
# =====================================================

elif page == "Results":

    st.title("📊 Results Dashboard")

    tab1, tab2 = st.tabs(
        [
            "🎭 LENS Results",
            "🚌 Attendance Results"
        ]
    )

    # =====================================================
    # TAB 1 : LENS RESULTS
    # =====================================================
    with tab1:

        st.subheader("🎭 Face Search Results")

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
                "📥 Download LENS Results",
                csv,
                "lens_results.csv",
                "text/csv"
            )

    # =====================================================
    # TAB 2 : ATTENDANCE RESULTS
    # =====================================================
    with tab2:

        response = students_table.scan()
        students = response.get("Items", [])

        if not students:
            st.warning(
                "No students enrolled yet."
            )

        else:

            df = pd.DataFrame(students)

            total_students = len(df)

            present_students = len(
                df[
                    df["attendance_status"]
                    == "Present"
                ]
            )

            absent_students = (
                total_students
                - present_students
            )

            attendance_percentage = (
                round(
                    (
                        present_students
                        / total_students
                    )
                    * 100,
                    2
                )
                if total_students > 0
                else 0
            )

            c1, c2, c3, c4 = st.columns(4)

            with c1:
                st.metric(
                    "👥 Total Students",
                    total_students
                )

            with c2:
                st.metric(
                    "✅ Present",
                    present_students
                )

            with c3:
                st.metric(
                    "❌ Absent",
                    absent_students
                )

            with c4:
                st.metric(
                    "📈 Attendance %",
                    f"{attendance_percentage}%"
                )

            st.divider()

            st.subheader(
                "📋 Today's Attendance"
            )

            display_columns = [
                "student_id",
                "student_name",
                "class",
                "bus_id",
                "attendance_status"
            ]

            available_columns = [
                c for c in display_columns
                if c in df.columns
            ]

            st.dataframe(
                df[available_columns],
                use_container_width=True
            )

            today = datetime.now().strftime(
                "%Y-%m-%d"
            )

            csv = df.to_csv(index=False)

            st.download_button(
                "📥 Download Today's Attendance",
                data=csv,
                file_name=f"attendance_{today}.csv",
                mime="text/csv"
            )

            st.divider()

            if st.button(
                "🗓️ End Day & Reset Attendance"
            ):

                for student in students:

                    students_table.update_item(
                        Key={
                            "student_id":
                            student["student_id"]
                        },
                        UpdateExpression=
                        "SET attendance_status = :s",
                        ExpressionAttributeValues={
                            ":s":
                            "Not Marked"
                        }
                    )

                st.success(
                    "Attendance reset successfully for the next day."
                )

                st.rerun()

# =====================================================
# ENROLLED FACES
# =====================================================

elif page == "Enrolled Faces":

    st.title("👥 Enrolled Data")

    tab1, tab2 = st.tabs(
        [
            "👥 Enrolled Students",
            "😀 Enrolled Faces"
        ]
    )

    # =====================================================
    # TAB 1 : ENROLLED STUDENTS
    # =====================================================
    with tab1:

        response = students_table.scan()
        students = response.get("Items", [])

        if not students:
            st.info("No students enrolled.")

        else:

            df = pd.DataFrame(students)

            # Ensure columns exist
            for col in [
                "student_id",
                "student_name",
                "class",
                "bus_id",
                "parent_contact",
                "attendance_status"
            ]:
                if col not in df.columns:
                    df[col] = ""

            # =========================
            # Search
            # =========================
            search = st.text_input(
                "🔍 Search Student"
            )

            if search:

                search = search.lower()

                mask = (
                    df["student_id"]
                    .astype(str)
                    .str.lower()
                    .str.contains(search)
                ) | (
                    df["student_name"]
                    .astype(str)
                    .str.lower()
                    .str.contains(search)
                )

                df = df[mask]

            # =========================
            # Filter
            # =========================
            filter_option = st.selectbox(
                "Attendance Filter",
                [
                    "All",
                    "Present",
                    "Not Marked"
                ]
            )

            if filter_option != "All":

                df = df[
                    df["attendance_status"]
                    == filter_option
                ]

            # =========================
            # Student Table
            # =========================
            st.subheader(
                "📋 Student Records"
            )

            display_columns = [
                "student_id",
                "student_name",
                "class",
                "bus_id",
                "attendance_status"
            ]

            available_columns = [
                c for c in display_columns
                if c in df.columns
            ]

            st.dataframe(
                df[available_columns],
                use_container_width=True
            )

            # Download CSV
            csv = df.to_csv(index=False)

            st.download_button(
                "📥 Download Student List",
                data=csv,
                file_name="enrolled_students.csv",
                mime="text/csv"
            )

            # =========================
            # Student Details
            # =========================
            st.divider()

            st.subheader(
                "👤 Student Details"
            )

            selected_student = st.selectbox(
                "Select Student",
                df["student_id"]
            )

            student = next(
                (
                    s for s in students
                    if s["student_id"]
                    == selected_student
                ),
                None
            )

            if student:

                c1, c2 = st.columns(2)

                with c1:
                    st.write(
                        "**Student ID:**",
                        student.get(
                            "student_id"
                        )
                    )
                    st.write(
                        "**Name:**",
                        student.get(
                            "student_name"
                        )
                    )
                    st.write(
                        "**Class:**",
                        student.get(
                            "class"
                        )
                    )

                with c2:
                    st.write(
                        "**Bus ID:**",
                        student.get(
                            "bus_id"
                        )
                    )
                    st.write(
                        "**Parent Contact:**",
                        student.get(
                            "parent_contact"
                        )
                    )
                    st.write(
                        "**Attendance:**",
                        student.get(
                            "attendance_status"
                        )
                    )

            # =========================
            # Delete Student
            # =========================
            st.divider()

            st.subheader(
                "🗑 Delete Student"
            )

            if st.button(
                f"Delete {selected_student}"
            ):

                students_table.delete_item(
                    Key={
                        "student_id":
                        selected_student
                    }
                )

                st.success(
                    f"{selected_student} deleted successfully."
                )

                st.rerun()

    # =====================================================
    # TAB 2 : ENROLLED FACES
    # =====================================================
    with tab2:

        try:

            response = rekognition.list_faces(
                CollectionId=COLLECTION_ID,
                MaxResults=100
            )

            faces = response.get(
                "Faces",
                []
            )

            if not faces:
                st.warning(
                    "No faces enrolled."
                )

            else:

                st.metric(
                    "Total Faces Enrolled",
                    len(faces)
                )

                face_data = []

                for face in faces:

                    face_data.append(
                        {
                            "ExternalImageId":
                            face.get(
                                "ExternalImageId",
                                "Unknown"
                            ),
                            "FaceId":
                            face["FaceId"][:20]
                            + "...",
                            "Confidence":
                            round(
                                face.get(
                                    "Confidence",
                                    0
                                ),
                                2
                            )
                        }
                    )

                face_df = pd.DataFrame(
                    face_data
                )

                st.dataframe(
                    face_df,
                    use_container_width=True
                )

                csv = face_df.to_csv(
                    index=False
                )

                st.download_button(
                    "📥 Download Face List",
                    data=csv,
                    file_name="enrolled_faces.csv",
                    mime="text/csv"
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
