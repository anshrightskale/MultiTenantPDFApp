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
s3 = boto3.client("s3", region_name="us-east-2")  # Replace with your region
BUCKET_NAME = "flask-pdf-upload-app"  # Replace with your actual bucket name

# Logging setup
logging.basicConfig(level=logging.INFO)

# Create DB tables if needed
with app.app_context():
    db.create_all()

# Generate a presigned S3 download URL
def generate_presigned_url(s3_path):
    parts = s3_path.replace("s3://", "").split("/", 1)
    bucket, key = parts[0], parts[1]
    return s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket, "Key": key},
        ExpiresIn=3600  # 1 hour
    )

@app.route("/", methods=["GET", "POST"])
def upload():
    if request.method == "POST":
        tenant_id = request.form.get("tenant_id")
        file = request.files.get("file")
        tags = request.form.get("tags", "")

        if not tenant_id or not file or not file.filename.endswith(".pdf"):
            return "Invalid input", 400

        # Upload to S3
        unique_name = f"{uuid.uuid4()}_{secure_filename(file.filename)}"
        s3_key = f"{tenant_id}/{unique_name}"
        s3.upload_fileobj(file, BUCKET_NAME, s3_key)

        # Save metadata
        file_path = f"s3://{BUCKET_NAME}/{s3_key}"
        document = Document(
            tenant_id=tenant_id,
            file_name=file.filename,
            file_path=file_path,
            tags=tags
        )
        db.session.add(document)
        db.session.commit()

        logging.info("Uploaded file %s for tenant %s", file.filename, tenant_id)
        return redirect(url_for("upload", tenant_id=tenant_id))

    # GET method
    tenant_id = request.args.get("tenant_id", "")
    documents = Document.query.filter_by(tenant_id=tenant_id).all() if tenant_id else []
    for doc in documents:
        doc.download_url = generate_presigned_url(doc.file_path)

    return render_template("index.html", docs=documents, tenant_id=tenant_id)