"""Seed config/invites and config/season (plan Phase 5 step 1).

config/invites is the sign-up allowlist: only these emails (and ADMIN_EMAILS) can finish
registering, so it needs each member's real email, the one they'll sign in with. The emails
come from a text file, one per line ('#' starts a comment), which is kept out of git.
Emails are added to the list, never removed; remove one in the Firestore console.

config/season gets the year and reveal time. Re-running only updates those two fields.

Dry run by default; pass --write to save. It writes to the emulator when FIRESTORE_EMULATOR_HOST
is set, and refuses to touch the real project unless you also pass --production.

Run from flask_server/:  pipenv run python ../scripts/seed_config.py [--write]
For production:          PIPENV_DONT_LOAD_ENV=1 pipenv run python ../scripts/seed_config.py --production [--write]
(pipenv loads flask_server/.env, which points at the emulators.)
"""
import argparse
import os
from datetime import datetime

import firebase_admin
from firebase_admin import firestore

DEFAULT_INVITES = os.path.join(os.path.dirname(__file__), "invites.txt")
DEFAULT_REVEAL = "2026-11-25T12:00-05:00"


def read_emails(path):
    """The file's emails, lowercased and de-duplicated, in file order. Raises ValueError on a bad line."""
    emails = []
    with open(path) as file:
        for number, line in enumerate(file, 1):
            email = line.split("#", 1)[0].strip().lower()
            if not email:
                continue
            local, _, domain = email.partition("@")
            if not local or "." not in domain or " " in email:
                raise ValueError(f"{path} line {number}: {email!r} isn't an email address")
            if email not in emails:
                emails.append(email)
    return emails


def parse_reveal(text):
    reveal_at = datetime.fromisoformat(text)
    if reveal_at.tzinfo is None:
        raise ValueError(f"--reveal {text!r} needs a UTC offset, e.g. {DEFAULT_REVEAL}")
    return reveal_at


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--invites", default=DEFAULT_INVITES, help="file of emails, one per line")
    parser.add_argument("--reveal", default=DEFAULT_REVEAL, help=f"reveal time with UTC offset (default {DEFAULT_REVEAL})")
    parser.add_argument("--write", action="store_true", help="save changes (default is a dry run)")
    parser.add_argument("--production", action="store_true", help="allow writing to the real project")
    args = parser.parse_args()

    using_emulator = bool(os.environ.get("FIRESTORE_EMULATOR_HOST"))
    if not using_emulator and not args.production:
        parser.error("FIRESTORE_EMULATOR_HOST isn't set; pass --production to seed the real project")
    if using_emulator and args.production:
        # pipenv loads flask_server/.env, which points at the emulator; the Firebase SDK would obey it
        parser.error("--production was passed but FIRESTORE_EMULATOR_HOST is set (pipenv loads it from "
                     "flask_server/.env). Run with PIPENV_DONT_LOAD_ENV=1 to seed the real project.")
    try:
        emails = read_emails(args.invites)
        reveal_at = parse_reveal(args.reveal)
    except (OSError, ValueError) as error:
        parser.error(str(error))
    if not emails:
        parser.error(f"{args.invites} has no emails")

    project = os.environ.get("GOOGLE_CLOUD_PROJECT", "secret-santa-511801")
    print(f"{'Writing' if args.write else 'Dry run'}: {'emulator' if using_emulator else 'PRODUCTION'} ({project})")
    print(f"  config/invites: add {len(emails)} emails")
    for email in emails:
        print(f"    {email}")
    print(f"  config/season: year {reveal_at.year}, revealAt {reveal_at.isoformat()}")
    if not args.write:
        print("Nothing saved. Pass --write to save.")
        return

    firebase_admin.initialize_app(options={"projectId": project})
    db = firestore.client(database_id=os.environ.get("FIRESTORE_DATABASE", "secret-santa-database"))
    db.collection("config").document("invites").set({"emails": firestore.ArrayUnion(emails)}, merge=True)
    db.collection("config").document("season").set({"year": reveal_at.year, "revealAt": reveal_at}, merge=True)
    print("Saved.")


if __name__ == "__main__":
    main()
