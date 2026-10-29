"""F6 process_photo and F7 process_profile_picture."""
import io

import pytest
from PIL import Image

import main
from tests.conftest import image_bytes, storage_event
from tests.test_images import exif_with_gps

PHOTOS = "secret-santa-photos"
PICTURES = "secret-santa-profile-photos"


def webp_size(data):
    image = Image.open(io.BytesIO(data))
    assert image.format == "WEBP"
    return image.size


@pytest.fixture
def pending_photo(db):
    db.put("photos/p1", {"ownerUid": "ann", "season": 2026, "status": "pending", "contentType": "image/jpeg"})
    return "uploads/2026/ann/p1"


# F6 process_photo

def test_photo_becomes_safe_display_and_thumb_copies(db, buckets, pending_photo):
    photos = buckets(PHOTOS)
    photos.blob(pending_photo).upload_from_string(image_bytes((4032, 3024), exif=exif_with_gps()), "image/jpeg")

    main.process_photo(storage_event(PHOTOS, pending_photo))

    photo = db.data("photos/p1")
    assert photo["status"] == "ready" and photo["processedAt"]
    assert photo["displayPath"] == "display/2026/ann/p1.webp"
    assert photo["thumbPath"] == "thumbs/2026/ann/p1.webp"
    display, thumb = photos.objects[photo["displayPath"]], photos.objects[photo["thumbPath"]]
    assert webp_size(display["data"]) == (1600, 1200) and webp_size(thumb["data"]) == (400, 300)
    for output in (display, thumb):
        assert output["content_type"] == "image/webp"
        assert output["cache_control"] == "private, max-age=3600"
        assert b"GPS" not in output["data"]
    # The original, location data and all, is gone
    assert pending_photo not in photos.objects


def test_its_own_output_does_not_retrigger_it(db, buckets, pending_photo):
    photos = buckets(PHOTOS)
    photos.blob("display/2026/ann/p1.webp").upload_from_string(b"webp", "image/webp")
    main.process_photo(storage_event(PHOTOS, "display/2026/ann/p1.webp"))
    main.process_photo(storage_event(PHOTOS, "thumbs/2026/ann/p1.webp"))
    assert db.data("photos/p1")["status"] == "pending"
    assert "display/2026/ann/p1.webp" in photos.objects


@pytest.mark.parametrize("name", [
    "uploads/2026/ann/unknown",  # no photo record
    "uploads/2026/bo/p1",  # someone else's photo id
    "uploads/2025/ann/p1",  # wrong season
    "uploads/stray-file",  # not a photo path at all
])
def test_unrequested_uploads_are_deleted(db, buckets, pending_photo, name):
    photos = buckets(PHOTOS)
    photos.blob(name).upload_from_string(image_bytes(), "image/jpeg")
    main.process_photo(storage_event(PHOTOS, name))
    assert name not in photos.objects
    assert db.data("photos/p1")["status"] == "pending"


def test_non_images_are_rejected_and_deleted(db, buckets, pending_photo):
    photos = buckets(PHOTOS)
    photos.blob(pending_photo).upload_from_string(b"<html>not a photo</html>", "image/jpeg")
    main.process_photo(storage_event(PHOTOS, pending_photo))
    assert db.data("photos/p1")["status"] == "rejected"
    assert photos.objects == {}


def test_redelivery_of_a_processed_photo_only_cleans_up(db, buckets, pending_photo):
    photos = buckets(PHOTOS)
    photos.blob(pending_photo).upload_from_string(image_bytes(), "image/jpeg")
    main.process_photo(storage_event(PHOTOS, pending_photo))
    first = dict(db.data("photos/p1"))

    # Same event again after the original is gone: nothing changes, nothing breaks
    main.process_photo(storage_event(PHOTOS, pending_photo))
    assert db.data("photos/p1") == first

    # The original still there (e.g. its delete failed): it's removed, the photo isn't reprocessed
    photos.blob(pending_photo).upload_from_string(image_bytes(), "image/jpeg")
    main.process_photo(storage_event(PHOTOS, pending_photo))
    assert pending_photo not in photos.objects and db.data("photos/p1") == first


def test_photo_deleted_by_its_owner_during_processing_leaves_nothing_behind(db, buckets, pending_photo, monkeypatch):
    photos = buckets(PHOTOS)
    photos.blob(pending_photo).upload_from_string(image_bytes(), "image/jpeg")
    original_variants = main.images.photo_variants

    def delete_meanwhile(raw):
        del db.docs["photos/p1"]
        return original_variants(raw)
    monkeypatch.setattr(main.images, "photo_variants", delete_meanwhile)

    main.process_photo(storage_event(PHOTOS, pending_photo))
    assert photos.objects == {}


# F7 process_profile_picture

@pytest.fixture
def user(db):
    db.put("users/ann", {"firstName": "Ann", "email": "ann@example.com", "profilePicturePath": None})


def test_picture_becomes_a_safe_square_avatar(db, buckets, user):
    pictures = buckets(PICTURES)
    pictures.blob("uploads/ann/pic1").upload_from_string(image_bytes((1200, 800), exif=exif_with_gps()), "image/jpeg")

    main.process_profile_picture(storage_event(PICTURES, "uploads/ann/pic1"))

    assert db.data("users/ann")["profilePicturePath"] == "avatars/ann/pic1.webp"
    avatar = pictures.objects["avatars/ann/pic1.webp"]
    assert webp_size(avatar["data"]) == (512, 512)
    assert avatar["content_type"] == "image/webp" and b"GPS" not in avatar["data"]
    assert "uploads/ann/pic1" not in pictures.objects


def test_a_new_picture_replaces_and_deletes_the_previous_one(db, buckets, user):
    pictures = buckets(PICTURES)
    for picture_id in ("pic1", "pic2"):
        pictures.blob(f"uploads/ann/{picture_id}").upload_from_string(image_bytes(), "image/jpeg")
        main.process_profile_picture(storage_event(PICTURES, f"uploads/ann/{picture_id}"))
    assert db.data("users/ann")["profilePicturePath"] == "avatars/ann/pic2.webp"
    assert list(pictures.objects) == ["avatars/ann/pic2.webp"]


def test_redelivery_does_not_reprocess(db, buckets, user):
    pictures = buckets(PICTURES)
    pictures.blob("uploads/ann/pic1").upload_from_string(image_bytes(), "image/jpeg")
    main.process_profile_picture(storage_event(PICTURES, "uploads/ann/pic1"))
    avatar = pictures.objects["avatars/ann/pic1.webp"]["data"]
    pictures.blob("uploads/ann/pic1").upload_from_string(image_bytes(color=(0, 0, 255)), "image/jpeg")
    main.process_profile_picture(storage_event(PICTURES, "uploads/ann/pic1"))
    assert pictures.objects["avatars/ann/pic1.webp"]["data"] == avatar
    assert "uploads/ann/pic1" not in pictures.objects


@pytest.mark.parametrize("name", ["uploads/nobody/pic1", "uploads/too/many/parts"])
def test_pictures_for_unknown_users_are_deleted(db, buckets, user, name):
    pictures = buckets(PICTURES)
    pictures.blob(name).upload_from_string(image_bytes(), "image/jpeg")
    main.process_profile_picture(storage_event(PICTURES, name))
    assert pictures.objects == {}


def test_unreadable_pictures_are_deleted_and_the_old_avatar_kept(db, buckets, user):
    pictures = buckets(PICTURES)
    db.docs["users/ann"]["profilePicturePath"] = "avatars/ann/old.webp"
    pictures.blob("avatars/ann/old.webp").upload_from_string(b"old", "image/webp")
    pictures.blob("uploads/ann/pic1").upload_from_string(b"not an image", "image/jpeg")
    main.process_profile_picture(storage_event(PICTURES, "uploads/ann/pic1"))
    assert db.data("users/ann")["profilePicturePath"] == "avatars/ann/old.webp"
    assert list(pictures.objects) == ["avatars/ann/old.webp"]


def test_avatars_do_not_retrigger_it(db, buckets, user):
    pictures = buckets(PICTURES)
    pictures.blob("avatars/ann/pic1.webp").upload_from_string(b"webp", "image/webp")
    main.process_profile_picture(storage_event(PICTURES, "avatars/ann/pic1.webp"))
    assert "avatars/ann/pic1.webp" in pictures.objects


def test_account_deleted_during_processing_leaves_no_avatar(db, buckets, user, monkeypatch):
    pictures = buckets(PICTURES)
    pictures.blob("uploads/ann/pic1").upload_from_string(image_bytes(), "image/jpeg")
    original_avatar = main.images.avatar

    def delete_meanwhile(raw):
        del db.docs["users/ann"]
        return original_avatar(raw)
    monkeypatch.setattr(main.images, "avatar", delete_meanwhile)

    main.process_profile_picture(storage_event(PICTURES, "uploads/ann/pic1"))
    assert pictures.objects == {}


# Uploads that disappear mid-way (step 4: redeliveries and races must not fail)

def test_pending_photo_whose_upload_is_already_gone_is_left_alone(db, buckets, pending_photo):
    # E.g. a duplicate delivery racing the first one, which already deleted the original
    main.process_photo(storage_event(PHOTOS, pending_photo))
    assert db.data("photos/p1")["status"] == "pending"
    assert buckets(PHOTOS).objects == {}


def test_unreadable_photo_whose_record_was_deleted_meanwhile_is_still_cleaned_up(db, buckets, pending_photo, monkeypatch):
    photos = buckets(PHOTOS)
    photos.blob(pending_photo).upload_from_string(b"not an image", "image/jpeg")
    original_variants = main.images.photo_variants

    def delete_then_fail(raw):
        del db.docs["photos/p1"]
        return original_variants(raw)
    monkeypatch.setattr(main.images, "photo_variants", delete_then_fail)

    main.process_photo(storage_event(PHOTOS, pending_photo))
    assert photos.objects == {} and db.data("photos/p1") is None


def test_profile_picture_whose_upload_is_already_gone_is_left_alone(db, buckets, user):
    main.process_profile_picture(storage_event(PICTURES, "uploads/ann/pic1"))
    assert db.data("users/ann")["profilePicturePath"] is None
    assert buckets(PICTURES).objects == {}


def test_profile_picture_update_also_stamps_updated_at(db, buckets, user):
    buckets(PICTURES).blob("uploads/ann/pic1").upload_from_string(image_bytes(), "image/jpeg")
    main.process_profile_picture(storage_event(PICTURES, "uploads/ann/pic1"))
    assert db.data("users/ann")["updatedAt"]
