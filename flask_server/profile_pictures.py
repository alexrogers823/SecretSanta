import os
import uuid

from flask import current_app

# Profile pictures are stored on local disk for development. When the app moves to GCP,
# swap these functions for the private profile-pictures bucket (see GCP_MIGRATION_PLAN.md).
MAX_PROFILE_PICTURE_BYTES = 5 * 1024 * 1024

IMAGE_SIGNATURES = {
    "jpg": (b"\xff\xd8\xff",),
    "png": (b"\x89PNG\r\n\x1a\n",),
    "gif": (b"GIF87a", b"GIF89a"),
}


def profile_picture_folder():
    folder = os.path.join(current_app.instance_path, "profile_pictures")
    os.makedirs(folder, exist_ok=True)
    return folder


def detect_image_extension(data):
    for extension, signatures in IMAGE_SIGNATURES.items():
        if data.startswith(signatures):
            return extension
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    return None


def save_profile_picture(user_id, data, extension):
    filename = f"{user_id}-{uuid.uuid4().hex}.{extension}"
    with open(os.path.join(profile_picture_folder(), filename), "wb") as file:
        file.write(data)
    return filename


def delete_profile_picture(filename):
    if not filename:
        return
    path = os.path.join(profile_picture_folder(), filename)
    if os.path.exists(path):
        os.remove(path)
