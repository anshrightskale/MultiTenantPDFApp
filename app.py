import os
import uuid
import logging
from flask import Flask, request, render_template, redirect, url_for, session
from werkzeug.utils import secure_filename
from models import db, Document
from config import Config
from dotenv import load_dotenv
import boto3

# Load environment variables
load_dotenv()

# Auth Config
USERNAME = os.environ.get("APP_USERNAME")
PASSWORD = os.environ.get("APP_PASSWORD")

# Flask app setup
app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)

# S3 setup
s3 = boto3.client("s3", region_name="us-east-2")
BUCKET_NAME = "flask-pdf-upload-app"

# Logging setup
logging.basicConfig(level=logging.INFO)

# Create DB tables if needed
with app.app_context():
    db.create_all()

# Login route
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if username == USERNAME and password == PASSWORD:
            session["logged_in"] = True
            return redirect(url_for("upload"))
        return "Invalid credentials", 401
    return render_template("login.html")

# Logout route
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# Upload route (protected)
@app.route("/", methods=["GET", "POST"])
def upload():
    if not session.get("logged_in"):
        return redirect(url_for("login"))

    if request.method == "POST":
        organization_id = request.form.get("organization_id")
        tags = request.form.get("tags", "")
        files = request.files.getlist("file")

        MAX_FILE_SIZE_MB = 10
        valid_files = []

        for f in files:
            if f and f.filename.endswith(".pdf"):
                f.seek(0, os.SEEK_END)
                size_mb = f.tell() / (1024 * 1024)
                f.seek(0)
                if size_mb > MAX_FILE_SIZE_MB:
                    return f"File {f.filename} exceeds {MAX_FILE_SIZE_MB}MB limit", 400
                valid_files.append(f)

        if not organization_id or not valid_files:
            return "Invalid input", 400

        for file in valid_files:
            unique_name = f"{uuid.uuid4()}_{secure_filename(file.filename)}"
            s3_key = f"{organization_id}/{unique_name}"
            s3.upload_fileobj(file, BUCKET_NAME, s3_key)

            file_path = f"s3://{BUCKET_NAME}/{s3_key}"
            document = Document(
                organization_id=organization_id,
                file_name=file.filename,
                file_path=file_path,
                tags=tags
            )
            db.session.add(document)

        db.session.commit()
        logging.info("Uploaded %d file(s) for org %s", len(valid_files), organization_id)
        return redirect(url_for("upload"))

    return render_template("index.html")

# Custom 413 error page
@app.errorhandler(413)
def request_entity_too_large(error):
    return render_template("error_413.html"), 413
