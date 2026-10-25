"""One-time copy of the old SQLite users and wish lists into Firestore (plan step 1.14).

Dry run by default; pass --write to save. It writes to the emulators when
FIRESTORE_EMULATOR_HOST / FIREBASE_AUTH_EMULATOR_HOST are set, and refuses to touch
the real project unless you also pass --production.

For each SQLite user it finds or creates a Firebase Auth account with that email (they sign in
with an email link, so there's no password), creates users/{uid} if it doesn't exist yet,
and adds the email to config/invites. Matches and local profile pictures aren't copied.

Run from flask_server/:  pipenv run python ../scripts/migrate_sqlite_to_firestore.py [--write]
"""
import argparse
import os
import sqlite3
from urllib.parse import urlparse

import firebase_admin
from firebase_admin import auth, firestore

DEFAULT_SQLITE = os.path.join(os.path.dirname(__file__), "..", "flask_server", "instance", "secret_santa.db")


def web_url_or_none(url):
    parsed = urlparse(url or "")
    return url if parsed.scheme in ("http", "https") and parsed.netloc else None


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--sqlite", default=DEFAULT_SQLITE)
    parser.add_argument("--write", action="store_true", help="save changes (default is a dry run)")
    parser.add_argument("--production", action="store_true", help="allow writing to the real project")
    args = parser.parse_args()

    using_emulators = bool(os.environ.get("FIRESTORE_EMULATOR_HOST") and os.environ.get("FIREBASE_AUTH_EMULATOR_HOST"))
    if not using_emulators and not args.production:
        parser.error("emulator env vars aren't set; pass --production to migrate into the real project")

    project = os.environ.get("GOOGLE_CLOUD_PROJECT", "secret-santa-511801")
    firebase_admin.initialize_app(options={"projectId": project})
    db = firestore.client(database_id=os.environ.get("FIRESTORE_DATABASE", "secret-santa-database"))

    sqlite = sqlite3.connect(f"file:{args.sqlite}?mode=ro", uri=True)
    sqlite.row_factory = sqlite3.Row
    users = sqlite.execute("SELECT id, first_name, last_name, email, address FROM users ORDER BY id").fetchall()

    print(f"{'Writing' if args.write else 'Dry run'}: {len(users)} users -> "
          f"{'emulators' if using_emulators else 'PRODUCTION'} ({project})")
    emails = []
    for row in users:
        email = row["email"].strip().lower()
        emails.append(email)
        gifts = []
        for gift in sqlite.execute("SELECT name, url, notes FROM gifts WHERE user_id = ? ORDER BY position", (row["id"],)):
            url = web_url_or_none(gift["url"])
            if gift["url"] and not url:
                print(f"  dropping non-http link on {email}'s gift {gift['name']!r}: {gift['url']!r}")
            gifts.append({"name": gift["name"], "url": url, "notes": gift["notes"] or None})

        if not args.write:
            print(f"  {email}: {row['first_name']} {row['last_name'] or '(no last name)'}, {len(gifts)} gifts")
            continue

        try:
            uid = auth.get_user_by_email(email).uid
        except auth.UserNotFoundError:
            uid = auth.create_user(email=email).uid

        ref = db.collection("users").document(uid)
        if ref.get().exists:
            print(f"  {email}: already in Firestore, skipped")
            continue
        ref.set({
            "firstName": row["first_name"],
            # Older rows have no last name; the member adds one when they next edit their profile
            "lastName": row["last_name"],
            "email": email,
            "address": row["address"],
            "profilePicturePath": None,
            "gifts": gifts,
            "createdAt": firestore.SERVER_TIMESTAMP,
            "updatedAt": firestore.SERVER_TIMESTAMP,
        })
        print(f"  {email}: created users/{uid} with {len(gifts)} gifts")

    if args.write:
        db.collection("config").document("invites").set({"emails": firestore.ArrayUnion(emails)}, merge=True)
        print(f"Added {len(emails)} emails to config/invites")


if __name__ == "__main__":
    main()
