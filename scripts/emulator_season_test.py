"""Run the season's functions against the Firestore emulator (plan Phase 5 steps 2 and 6).

The Firebase Functions emulator only runs firebase-functions code, not our functions-framework
handlers, so this script calls them itself with the same events Scheduler and Firestore would send.
It only ever talks to the emulator, and emails are always logged here instead of sent (MAIL_MODE=log).

Start the emulators first (from the repo root: firebase emulators:start --only auth,firestore), then
from functions/:  pipenv run python ../scripts/emulator_season_test.py <command>

  status       the season, members and this year's matches
  add-users N  add N made-up members (Firestore only; they can't sign in), for a quick draw
  draw         Scheduler's generate_matches, then the match email each new assignment triggers
  reminders    Scheduler's gift_reminder (emails members with no wish list, if before the reveal)
  reveal       move the reveal to a minute ago, so the app shows matches (--default puts back Nov 25)
  exclusions   step 6: seed last year's and the year before's matches, draw, and check the rules
  reset        delete this year's matches and test seasons, and put back the default reveal
"""
import argparse
import base64
import itertools
import json
import os
import socket
import sys
from datetime import datetime, timedelta, timezone

EMULATOR = "127.0.0.1:8080"
# Before anything imports Firebase: emulator only, and never a real email
os.environ["FIRESTORE_EMULATOR_HOST"] = os.environ.get("FIRESTORE_EMULATOR_HOST") or EMULATOR
os.environ["MAIL_MODE"] = "log"
os.environ.setdefault("ADMIN_EMAILS", "admin@example.com")

REPO_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path[:0] = [os.path.join(REPO_ROOT, "functions"), REPO_ROOT]

import logging  # noqa: E402

from cloudevents.http import CloudEvent  # noqa: E402
from firebase_admin import firestore  # noqa: E402

import main  # noqa: E402
import store  # noqa: E402

_event_ids = itertools.count(1)
RUN = datetime.now(timezone.utc).strftime("%H%M%S")


def pubsub_event(action):
    data = base64.b64encode(json.dumps({"action": action}).encode()).decode()
    return CloudEvent(
        {"type": "google.cloud.pubsub.topic.v1.messagePublished", "source": "//pubsub/season-events",
         "id": f"emulator-{RUN}-{next(_event_ids)}"},
        {"message": {"data": data}},
    )


def firestore_created_event(path):
    return CloudEvent(
        {"type": "google.cloud.firestore.document.v1.created", "source": "//firestore",
         "id": f"emulator-{RUN}-{next(_event_ids)}", "subject": f"documents/{path}"},
        None,
    )


def emulator_is_running():
    host, port = os.environ["FIRESTORE_EMULATOR_HOST"].rsplit(":", 1)
    try:
        socket.create_connection((host, int(port)), timeout=2).close()
        return True
    except OSError:
        return False


def names(db):
    return {snapshot.id: (snapshot.to_dict() or {}).get("firstName") or snapshot.id for snapshot in db.collection("users").stream()}


def assignments(db, year):
    return {snapshot.id: (snapshot.to_dict() or {}).get("receiverUid")
            for snapshot in db.collection("seasons").document(str(year)).collection("assignments").stream()}


def show_pairs(db, pairs):
    who = names(db)
    for giver, receiver in sorted(pairs.items(), key=lambda pair: who.get(pair[0], pair[0])):
        print(f"    {who.get(giver, giver)} -> {who.get(receiver, receiver)}")


def delete_season(db, year):
    season = db.collection("seasons").document(str(year))
    for snapshot in season.collection("assignments").stream():
        snapshot.reference.delete()
    season.delete()


def status(db):
    year, reveal_at = store.current_season()
    config = db.collection("config").document("season").get().to_dict() or {}
    who = names(db)
    revealed = "revealed" if store.now() >= reveal_at else "not revealed yet"
    print(f"Season {year}: reveal {reveal_at.isoformat()} ({revealed}), status {config.get('status', '-')}")
    print(f"Members ({len(who)}): {', '.join(sorted(who.values())) or 'none'}")
    pairs = assignments(db, year)
    print(f"Matches for {year}: {len(pairs) or 'none'}")
    show_pairs(db, pairs)


def add_users(db, count):
    existing = names(db)
    added = 0
    for number in itertools.count(1):
        if added == count:
            break
        uid = f"test-{number}"
        if uid in existing:
            continue
        db.collection("users").document(uid).set({
            "firstName": f"Tester{number}", "lastName": "Emulator", "email": f"tester{number}@example.com",
            "address": "1 Test St", "gifts": [], "profilePicturePath": None,
            "createdAt": firestore.SERVER_TIMESTAMP, "updatedAt": firestore.SERVER_TIMESTAMP,
        })
        added += 1
    print(f"Added {count} made-up members")


def draw(db):
    year, _ = store.current_season()
    main.generate_matches(pubsub_event("generate_matches"))
    pairs = assignments(db, year)
    if not pairs:
        print("No matches were drawn (see the email above for why)")
        return
    # In production each new assignment triggers notify_match; here we send those events ourselves
    for giver in pairs:
        main.notify_match(firestore_created_event(f"seasons/{year}/assignments/{giver}"))
    print(f"Drew {len(pairs)} matches for {year} and sent each giver's email (logged above):")
    show_pairs(db, pairs)


def reveal(db, default):
    year, _ = store.current_season()
    reveal_at = (datetime(year, 11, 25, 12, tzinfo=store.EASTERN_STANDARD_TIME) if default
                 else datetime.now(timezone.utc) - timedelta(minutes=1))
    db.collection("config").document("season").set({"year": year, "revealAt": reveal_at}, merge=True)
    print(f"Reveal set to {reveal_at.isoformat()}")


def check_exclusions(db):
    """(problems with this year's draw, pairs it shares with the year before last)."""
    year, _ = store.current_season()
    this_year = set(assignments(db, year).items())
    last_year = set(assignments(db, year - 1).items())
    problems = [f"repeats last year's pair {pair}" for pair in sorted(this_year & last_year)]
    return problems, this_year & set(assignments(db, year - 2).items())


def exclusions(db):
    year, _ = store.current_season()
    uids = sorted(names(db))
    if len(uids) < 3:
        print(f"Needs at least 3 members (there are {len(uids)}); run add-users first")
        return
    if assignments(db, year):
        print(f"{year} already has matches; run reset first")
        return
    # Two different full cycles: last year a->b->c->a, the year before a->c->b->a
    forward = dict(zip(uids, uids[1:] + uids[:1]))
    backward = {receiver: giver for giver, receiver in forward.items()}
    for past_year, pairs in ((year - 1, forward), (year - 2, backward)):
        delete_season(db, past_year)
        for giver, receiver in pairs.items():
            db.collection("seasons").document(str(past_year)).collection("assignments").document(giver).set({"receiverUid": receiver})
    print(f"Seeded {year - 1} and {year - 2} matches")

    main.generate_matches(pubsub_event("generate_matches"))
    problems, older_repeats = check_exclusions(db)
    print(f"Drew {year}:")
    show_pairs(db, assignments(db, year))
    print(f"  Pairs repeated from {year - 2} (allowed): {len(older_repeats)}")
    if problems:
        print("FAIL: " + "; ".join(problems))
        sys.exit(1)
    print(f"PASS: no pair from {year - 1} repeats")
    print("No emails were sent for this draw; run reset before testing the app")


def reset(db):
    year, _ = store.current_season()
    for past_year in (year, year - 1, year - 2):
        delete_season(db, past_year)
    db.collection("config").document("season").set({"status": firestore.DELETE_FIELD}, merge=True)
    reveal(db, default=True)
    print(f"Deleted the {year}, {year - 1} and {year - 2} seasons")


def main_cli():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0], epilog=__doc__.split("\n\n", 2)[2],
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=["status", "add-users", "draw", "reminders", "reveal", "exclusions", "reset"])
    parser.add_argument("count", nargs="?", type=int, default=3, help="for add-users (default 3)")
    parser.add_argument("--default", action="store_true", help="for reveal: put back Nov 25 at 12pm Eastern")
    args = parser.parse_args()

    if not emulator_is_running():
        parser.error(f"nothing is listening on {os.environ['FIRESTORE_EMULATOR_HOST']}; "
                     "start it with `firebase emulators:start --only auth,firestore` from the repo root")
    logging.basicConfig(level=logging.WARNING, format="%(message)s")
    db = store.db()
    print(f"Firestore emulator {os.environ['FIRESTORE_EMULATOR_HOST']}, database {store.DATABASE}; emails are logged, not sent\n")

    if args.command == "status":
        status(db)
    elif args.command == "add-users":
        add_users(db, args.count)
    elif args.command == "draw":
        draw(db)
    elif args.command == "reminders":
        main.gift_reminder(pubsub_event("gift_reminder"))
        print("Sent reminders (logged above); none are sent after the reveal")
    elif args.command == "reveal":
        reveal(db, args.default)
    elif args.command == "exclusions":
        exclusions(db)
    elif args.command == "reset":
        reset(db)


if __name__ == "__main__":
    main_cli()
