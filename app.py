"""
app.py

Flask web application for the FNOL Claims Processing Agent.
Handles file uploads, runs extraction + routing, and renders results.
"""

import os
import re
import json
from flask import Flask, render_template, request, redirect, url_for, flash
from werkzeug.utils import secure_filename

from agent import extract_fields_with_llm, find_missing_fields
from router import determine_route

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "fnol-dev-secret-2024")

ALLOWED_EXTENSIONS = {"txt"}
MAX_CONTENT_LENGTH = 2 * 1024 * 1024
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH

ROUTE_META = {
    "Fast-track": {
        "color": "green",
        "icon": "⚡",
        "description": "Eligible for automated fast-track processing"
    },
    "Specialist Queue": {
        "color": "blue",
        "icon": "🩺",
        "description": "Assigned to specialist team for injury assessment"
    },
    "Investigation Flag": {
        "color": "red",
        "icon": "🚩",
        "description": "Flagged for fraud investigation review"
    },
    "Manual Review": {
        "color": "amber",
        "icon": "📋",
        "description": "Requires manual review before processing"
    },
}


@app.template_filter("highlight_json")
def highlight_json_filter(json_str):
    """Adds HTML spans for syntax-highlighted JSON display."""
    def replacer(match):
        key      = match.group(1)
        str_val  = match.group(2)
        num_val  = match.group(3)
        null_val = match.group(4)
        bool_val = match.group(5)
        punct    = match.group(6)

        if key:
            return f'<span class="j-key">"{key}"</span>:'
        elif str_val is not None:
            return f'<span class="j-str">"{str_val}"</span>'
        elif num_val:
            return f'<span class="j-num">{num_val}</span>'
        elif null_val:
            return f'<span class="j-null">{null_val}</span>'
        elif bool_val:
            return f'<span class="j-bool">{bool_val}</span>'
        else:
            return punct

    pattern = r'"([\w_]+)"\s*:|"((?:[^"\\]|\\.)*)"|(-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)|(\bnull\b)|(\btrue\b|\bfalse\b)|([{}\[\],])'
    return re.sub(pattern, replacer, json_str)


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


@app.route("/process", methods=["POST"])
def process():
    if "fnol_file" not in request.files:
        flash("No file uploaded.")
        return redirect(url_for("index"))

    file = request.files["fnol_file"]

    if file.filename == "":
        flash("No file selected.")
        return redirect(url_for("index"))

    if not allowed_file(file.filename):
        flash("Only .txt files are supported right now.")
        return redirect(url_for("index"))

    # read the document text directly from the upload
    document_text = file.read().decode("utf-8", errors="replace")

    if not document_text.strip():
        flash("The uploaded file appears to be empty.")
        return redirect(url_for("index"))

    try:
        extracted = extract_fields_with_llm(document_text)
    except Exception as e:
        flash(f"Extraction failed: {str(e)}. Make sure GROQ_API_KEY is set correctly.")
        return redirect(url_for("index"))

    missing = find_missing_fields(extracted)
    routing = determine_route(extracted, missing)

    route_name = routing["recommendedRoute"]
    meta = ROUTE_META.get(route_name, {"color": "gray", "icon": "❓", "description": ""})

    result = {
        "filename": secure_filename(file.filename),
        "extractedFields": extracted,
        "missingFields": missing,
        "recommendedRoute": route_name,
        "reasoning": routing["reasoning"],
        "routeMeta": meta,
    }

    return render_template("result.html", result=result)


@app.route("/demo/<int:doc_id>")
def demo(doc_id):
    """
    Load one of the sample FNOL files so people can try the app
    without uploading anything. Good for demos.
    """
    sample_dir = os.path.join(os.path.dirname(__file__), "sample_fnols")
    filename = f"fnol_00{doc_id}.txt"
    filepath = os.path.join(sample_dir, filename)

    if not os.path.exists(filepath):
        flash("Demo file not found.")
        return redirect(url_for("index"))

    with open(filepath, "r", encoding="utf-8") as f:
        document_text = f.read()

    try:
        extracted = extract_fields_with_llm(document_text)
    except Exception as e:
        flash(f"Extraction failed: {str(e)}. Make sure GROQ_API_KEY is set correctly.")
        return redirect(url_for("index"))

    missing = find_missing_fields(extracted)
    routing = determine_route(extracted, missing)

    route_name = routing["recommendedRoute"]
    meta = ROUTE_META.get(route_name, {"color": "gray", "icon": "❓", "description": ""})

    result = {
        "filename": filename,
        "extractedFields": extracted,
        "missingFields": missing,
        "recommendedRoute": route_name,
        "reasoning": routing["reasoning"],
        "routeMeta": meta,
    }

    return render_template("result.html", result=result)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
