import os
import uuid
import logging
from datetime import datetime
from flask import Flask, request, render_template, redirect, url_for
from werkzeug.utils import secure_filename
from models import db, Document
from config import Config
import boto3

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

def generate_presigned_url(s3_path):
    parts = s3_path.replace("s3://", "").split("/", 1)
    bucket, key = parts[0], parts[1]
    return s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket, "Key": key},
        ExpiresIn=3600
    )

@app.route("/", methods=["GET", "POST"])
def upload():
    if request.method == "POST":
        organization_name = request.form.get("organization_name")  # ✅ updated field name
        tags = request.form.get("tags", "")
        files = request.files.getlist("file")

        valid_files = [f for f in files if f and f.filename.endswith(".pdf")]

        if not organization_name or not valid_files:
            return "Invalid input", 400

        for file in valid_files:
            unique_name = f"{uuid.uuid4()}_{secure_filename(file.filename)}"
            s3_key = f"{organization_name}/{unique_name}"
            s3.upload_fileobj(file, BUCKET_NAME, s3_key)

            file_path = f"s3://{BUCKET_NAME}/{s3_key}"
            document = Document(
                organization_name=organization_name,  # ✅ updated field name
                file_name=file.filename,
                file_path=file_path,
                tags=tags
            )
            db.session.add(document)

        db.session.commit()
        logging.info("Uploaded %d file(s) for tenant %s", len(valid_files), organization_name)
        return redirect(url_for("upload", organization_name=organization_name))

    # GET method
    organization_name = request.args.get("organization_name", "")  # ✅ updated field name
    documents = Document.query.filter_by(organization_name=organization_name).order_by(Document.uploaded_at.desc()).all()
    for doc in documents:
        doc.download_url = generate_presigned_url(doc.file_path)

    return render_template("index.html", docs=documents, organization_name=organization_name)
