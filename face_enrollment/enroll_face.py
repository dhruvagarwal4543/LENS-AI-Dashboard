import boto3
import os

BUCKET_NAME = "lens-face-storage"
COLLECTION_ID = "lens-collection"

s3 = boto3.client("s3", region_name="ap-south-1")
rekognition = boto3.client("rekognition", region_name="ap-south-1")


def enroll_face(image_path, person_name):

    file_name = os.path.basename(image_path)

    print(f"Uploading {file_name} to S3...")

    s3.upload_file(
        image_path,
        BUCKET_NAME,
        file_name
    )

    print("Upload complete.")

    response = rekognition.index_faces(
        CollectionId=COLLECTION_ID,
        Image={
            "S3Object": {
                "Bucket": BUCKET_NAME,
                "Name": file_name
            }
        },
        ExternalImageId=person_name
    )

    face_records = response.get("FaceRecords", [])

    if len(face_records) > 0:
        face_id = face_records[0]["Face"]["FaceId"]

        print("\nFace Enrolled Successfully")
        print(f"Name: {person_name}")
        print(f"Face ID: {face_id}")

    else:
        print("No face detected.")


if __name__ == "__main__":
    enroll_face(
        image_path="known_faces/sir.jpg",
        person_name="Sir"
    )

