import os
import uuid
import logging
from datetime import datetime
from flask import Flask, request, render_template, redirect, url_for, session
from werkzeug.utils import secure_filename
from models import db, Document
from config import Config
import boto3

# Flask app setup
app = Flask(__name__)
app.config.from_object(Config)
app.secret_key = app.config["SECRET_KEY"]  # Required for secure sessions
db.init_app(app)

# S3 setup
s3 = boto3.client("s3", region_name="us-east-2")
BUCKET_NAME = "flask-pdf-upload-app"

# Logging setup
logging.basicConfig(level=logging.INFO)

# Create DB tables if needed
with app.app_context():
    db.create_all()

# Helper to generate a presigned download URL
def generate_presigned_url(s3_path):
    parts = s3_path.replace("s3://", "").split("/", 1)
    bucket, key = parts[0], parts[1]
    return s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket, "Key": key},
        ExpiresIn=3600  # 1 hour expiry
    )

@app.route("/", methods=["GET", "POST"])
def upload():
    if request.method == "POST":
        organization_id = request.form.get("organization_id")
        tags = request.form.get("tags", "")
        files = request.files.getlist("file")

        valid_files = [f for f in files if f and f.filename.endswith(".pdf")]

        if not organization_id or not valid_files:
            return "Invalid input", 400

        session["organization_id"] = organization_id

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

    # ✅ Reset session on every GET request (fresh start)
    session.clear()
    organization_id = ""
    documents = []

    return render_template("index.html", docs=documents, organization_id=organization_id)
