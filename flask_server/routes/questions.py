from flask import Blueprint, jsonify, request

import repository
from auth import require_admin, require_user

questions_bp = Blueprint("questions", __name__, url_prefix="/api/questions")

MAX_QUESTION_LENGTH = 2000

# Questions are anonymous, even to the admin. Sign-in is required only to keep out spam:
# never store, log or return who asked, and keep g.uid/g.email out of this file entirely.


@questions_bp.route("", methods=["POST"])
@require_user
def ask_question():
    text = str((request.get_json(silent=True) or {}).get("text") or "").strip()
    if not text:
        return jsonify({"error": "question text is required"}), 400
    if len(text) > MAX_QUESTION_LENGTH:
        return jsonify({"error": f"questions can be up to {MAX_QUESTION_LENGTH} characters"}), 400

    repository.create_question(text)
    return jsonify({"sent": True}), 201


@questions_bp.route("", methods=["GET"])
@require_admin
def list_questions():
    return jsonify([repository.serialize_question(question) for question in repository.list_questions()])
