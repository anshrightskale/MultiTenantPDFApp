import os
import uuid
import logging
from flask import Flask, request, render_template, redirect, url_for, send_from_directory
from werkzeug.utils import secure_filename
from models import db, Document
from config import Config

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)

# Ensure folders exist
os.makedirs(os.path.join(os.path.abspath(os.path.dirname(__file__)), "instance"), exist_ok=True)
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

logging.basicConfig(level=logging.INFO)

# Create DB tables if not exists
with app.app_context():
    db.create_all()

@app.route("/", methods=["GET", "POST"])
def upload():
    if request.method == "POST":
        tenant_id = request.form.get("tenant_id")
        files = request.files.getlist("files")
        tags = request.form.get("tags", "")

        if not tenant_id or not files:
            return "Invalid input", 400

        tenant_folder = os.path.join(app.config['UPLOAD_FOLDER'], tenant_id)
        os.makedirs(tenant_folder, exist_ok=True)

        for file in files:
            if file and file.filename.endswith(".pdf"):
                unique_name = f"{uuid.uuid4()}_{secure_filename(file.filename)}"
                file_path = os.path.join(tenant_folder, unique_name)
                file.save(file_path)

                document = Document(
                    tenant_id=tenant_id,
                    file_name=file.filename,
                    file_path=file_path,
                    tags=tags
                )
                db.session.add(document)
                logging.info("Uploaded file %s for tenant %s", file.filename, tenant_id)

        db.session.commit()
        return redirect(url_for("upload", tenant_id=tenant_id))

    tenant_id = request.args.get("tenant_id", "")
    documents = Document.query.filter_by(tenant_id=tenant_id).order_by(Document.uploaded_at.desc()).all()if tenant_id else []
    return render_template("index.html", docs=documents, tenant_id=tenant_id)

@app.route("/uploads/<tenant_id>/<filename>")
def serve_pdf(tenant_id, filename):
    folder = os.path.join(app.config['UPLOAD_FOLDER'], tenant_id)
    return send_from_directory(folder, filename)