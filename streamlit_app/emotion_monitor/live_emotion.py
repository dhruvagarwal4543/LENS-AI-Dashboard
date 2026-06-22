import cv2
import av
import boto3
import time

from streamlit_webrtc import VideoProcessorBase

SESSION_DATA = []

rekognition = boto3.client(
    "rekognition",
    region_name="ap-south-1"
)

COLLECTION_ID = "lens-collection"


class FaceDetector(VideoProcessorBase):

    def __init__(self):

        self.current_label = "Unknown"
        self.current_emotion = "Unknown"
        self.session_data = []
        self.last_detection_time = 0
        self.start_time = time.time()

        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades +
            "haarcascade_frontalface_default.xml"
        )

    def recv(self, frame):

        img = frame.to_ndarray(format="bgr24")

        gray = cv2.cvtColor(
            img,
            cv2.COLOR_BGR2GRAY
        )

        faces = self.face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(50, 50)
        )

        for (x, y, w, h) in faces:

            face_crop = img[
                y:y+h,
                x:x+w
            ]

            label = "Unknown"
            emotion = "Unknown"

            current_time = time.time()

            if current_time - self.last_detection_time > 2:

                self.last_detection_time = current_time

                try:

                    success, buffer = cv2.imencode(
                        ".jpg",
                        face_crop
                    )

                    if success:

                        image_bytes = buffer.tobytes()

                        recognition_response = rekognition.search_faces_by_image(
                            CollectionId=COLLECTION_ID,
                            Image={
                                "Bytes": image_bytes
                            },
                            FaceMatchThreshold=85,
                            MaxFaces=1
                        )

                        matches = recognition_response.get(
                            "FaceMatches",
                            []
                        )

                        if matches:

                            label = matches[0]["Face"].get(
                                "ExternalImageId",
                                "Unknown"
                            )

                        emotion_response = rekognition.detect_faces(
                            Image={
                                "Bytes": image_bytes
                            },
                            Attributes=["ALL"]
                        )

                        face_details = emotion_response.get(
                            "FaceDetails",
                            []
                        )

                        if face_details:

                            emotions = face_details[0].get(
                                "Emotions",
                                []
                            )

                            if emotions:

                                top_emotion = max(
                                    emotions,
                                    key=lambda x: x["Confidence"]
                                )

                                emotion = top_emotion["Type"]
                                self.current_label = label
                                self.current_emotion = emotion

                except Exception as e:

                    print(
                        f"Recognition Error: {e}"
                    )

                record = {
                    "person": label,
                    "emotion": emotion,
                    "timestamp": time.strftime("%H:%M:%S")
                }

                self.session_data.append(record)
                SESSION_DATA.append(record)
                print("SESSION:", record)

            cv2.rectangle(
                img,
                (x, y),
                (x + w, y + h),
                (0, 255, 0),
                3
            )

            display_text = (
    f"{self.current_label} | {self.current_emotion}"
)

            cv2.putText(
                img,
                display_text,
                (x, y - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 0),
                2
            )

        return av.VideoFrame.from_ndarray(
            img,
            format="bgr24"
        )