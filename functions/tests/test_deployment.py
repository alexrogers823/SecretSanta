"""Deployment configuration (Phase 3, steps 1, 3, 6 and 7).

These keep the deploy commands and Scheduler jobs in GCP_MIGRATION_PLAN.md in step with the code:
a function deployed under the wrong entry point, or a job publishing an action no function
handles, would deploy fine and then do nothing. Step 8 (IAM) is checked against the live project
with the commands in the plan, not here.
"""
import re
import shutil
import subprocess
from pathlib import Path

import pytest
from functions_framework import _function_registry

import main
import store

FUNCTIONS_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = FUNCTIONS_DIR.parent
PLAN = (REPO_ROOT / "GCP_MIGRATION_PLAN.md").read_text()
PHASE_3 = PLAN[PLAN.index("### Phase 3"):PLAN.index("### Phase 4")]
DEPLOY_STEP = PHASE_3[PHASE_3.index("6. Deploy"):PHASE_3.index("7. Create")]
SCHEDULER_STEP = PHASE_3[PHASE_3.index("7. Create"):PHASE_3.index("8. Give")]

ENTRY_POINTS = ["generate_matches", "gift_reminder", "notify_match", "notify_admin_question", "process_photo", "process_profile_picture"]


def deploy_command(name):
    """The plan's `gcloud functions deploy <name> ...` command, with line continuations joined."""
    joined = DEPLOY_STEP.replace("\\\n", " ")
    return next(line for line in joined.splitlines() if f"gcloud functions deploy {name} " in line)


# Step 1: the functions and their dependencies

def test_every_function_is_a_cloud_event_entry_point():
    for name in ENTRY_POINTS:
        assert callable(getattr(main, name))
        assert _function_registry.REGISTRY_MAP[name] == "cloudevent"


def test_requirements_have_the_runtime_packages_and_no_test_tools():
    packages = {
        line.split("==")[0].lower()
        for line in (FUNCTIONS_DIR / "requirements.txt").read_text().splitlines()
        if "==" in line
    }
    assert {"functions-framework", "firebase-admin", "google-cloud-storage", "pillow", "pillow-heif"} <= packages
    assert not {"pytest", "pytest-cov"} & packages


def test_python_version_matches_the_deployed_runtime():
    assert 'python_version = "3.12"' in (FUNCTIONS_DIR / "Pipfile").read_text()
    assert "--runtime=python312" in DEPLOY_STEP


def test_deploy_upload_leaves_out_tests_and_dev_files_but_not_shared_code():
    ignored = (FUNCTIONS_DIR / ".gcloudignore").read_text().splitlines()
    for pattern in ("tests/", "Pipfile", "Pipfile.lock", "pytest.ini", "__pycache__/"):
        assert pattern in ignored
    assert not any(line.strip().rstrip("/") in ("shared", "*.py", "main.py") for line in ignored)


# Step 3: shared/ is copied in for deploys

def test_sync_shared_copies_the_shared_package_into_functions(tmp_path):
    (tmp_path / "scripts").mkdir()
    shutil.copy(REPO_ROOT / "scripts" / "sync_shared.sh", tmp_path / "scripts" / "sync_shared.sh")
    shutil.copytree(REPO_ROOT / "shared", tmp_path / "shared", ignore=shutil.ignore_patterns("__pycache__"))
    (tmp_path / "shared" / "__pycache__").mkdir()
    (tmp_path / "functions" / "shared").mkdir(parents=True)
    (tmp_path / "functions" / "shared" / "stale.py").write_text("old copy")

    subprocess.run(["sh", str(tmp_path / "scripts" / "sync_shared.sh")], check=True)

    copied = tmp_path / "functions" / "shared"
    assert (copied / "matching.py").read_text() == (REPO_ROOT / "shared" / "matching.py").read_text()
    assert not (copied / "stale.py").exists()  # replaced, not merged
    assert not (copied / "__pycache__").exists()


def test_the_copied_shared_folder_is_never_committed():
    assert "functions/shared/" in (REPO_ROOT / ".gitignore").read_text()


# Step 6: the plan's deploy commands match the code

@pytest.mark.parametrize("name", ENTRY_POINTS)
def test_each_function_is_deployed_under_its_own_entry_point(name):
    command = deploy_command(name)
    assert f"--entry-point={name}" in command
    assert '"${COMMON[@]}"' in command


def test_common_flags_use_the_dedicated_service_account_and_named_database():
    assert "--source=functions" in DEPLOY_STEP
    assert "--service-account=$FNS" in DEPLOY_STEP and "--trigger-service-account=$FNS" in DEPLOY_STEP
    assert "FNS=secret-santa-fns@secret-santa-511801.iam.gserviceaccount.com" in DEPLOY_STEP
    assert f"FIRESTORE_DATABASE={store.DATABASE}" in DEPLOY_STEP
    assert f"--trigger-event-filters=database={store.DATABASE}" in DEPLOY_STEP


@pytest.mark.parametrize("name", ["generate_matches", "gift_reminder", "notify_match", "notify_admin_question"])
def test_functions_that_email_get_the_smtp_password(name):
    assert '"${MAIL[@]}"' in deploy_command(name)
    assert "MAIL=(--set-secrets=SMTP_PASSWORD=smtp-password:latest)" in DEPLOY_STEP
    for setting in ("ADMIN_EMAILS=", "SMTP_USER=", "SITE_URL="):
        assert setting in DEPLOY_STEP


@pytest.mark.parametrize("name", ["process_photo", "process_profile_picture"])
def test_image_functions_get_no_email_password_but_enough_memory(name):
    command = deploy_command(name)
    assert "MAIL" not in command
    assert "--memory=512Mi" in command


def test_triggers_point_at_the_right_sources():
    assert "--trigger-topic=season-events" in deploy_command("generate_matches")
    assert "--trigger-topic=season-events" in deploy_command("gift_reminder")
    assert "--trigger-bucket=secret-santa-photos " in deploy_command("process_photo") + " "
    assert "--trigger-bucket=secret-santa-profile-photos " in deploy_command("process_profile_picture") + " "


@pytest.mark.parametrize("name, pattern, example", [
    ("notify_match", "seasons/{year}/assignments/{giver}", "seasons/2026/assignments/ann"),
    ("notify_admin_question", "questions/{question}", "questions/q1"),
])
def test_firestore_path_patterns_match_what_the_code_parses(name, pattern, example, db, sent):
    command = deploy_command(name)
    assert '"${FIRESTORE_CREATED[@]}"' in command
    assert f"--trigger-event-filters-path-pattern='document={pattern}'" in command
    # The handler can parse a path of exactly that shape (it skips a missing document quietly)
    from tests.conftest import firestore_event
    getattr(main, name)(firestore_event(example))


# Step 7: every Scheduler job's action is handled by exactly one function

def scheduler_actions():
    return re.findall(r"""--message-body='\{"action": "(\w+)"\}'""", SCHEDULER_STEP)


def test_the_plan_creates_three_scheduler_jobs_on_season_events():
    assert sorted(scheduler_actions()) == ["close_season", "generate_matches", "gift_reminder"]
    assert "--topic=season-events" in SCHEDULER_STEP
    assert "--time-zone=America/New_York" in SCHEDULER_STEP


def test_schedules_match_the_season_dates():
    jobs = dict(re.findall(r"jobs create pubsub ([\w-]+) .*?--schedule='([^']+)'", SCHEDULER_STEP.replace("\\\n", " ")))
    assert jobs == {
        "generate-matches": "0 12 25 11 *",  # Nov 25, 12pm: the default reveal time
        "gift-reminder": "0 10 15,22 11 *",
        "close-season": "0 9 15 1 *",
    }


@pytest.mark.parametrize("action", ["generate_matches", "gift_reminder", "close_season"])
def test_each_scheduled_action_runs_exactly_one_handler(action, monkeypatch, db):
    from tests.conftest import pubsub_event
    ran = []
    monkeypatch.setattr(main, "_generate_matches", lambda: ran.append("generate_matches"))
    monkeypatch.setattr(main, "_send_gift_reminders", lambda event_id: ran.append("gift_reminder"))
    monkeypatch.setattr(main, "_close_season", lambda: ran.append("close_season"))

    # Both Pub/Sub functions receive every season-events message
    event = pubsub_event(action)
    main.generate_matches(event)
    main.gift_reminder(event)
    assert ran == [action]
