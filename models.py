from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Document(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    organization_name = db.Column(db.String(100), nullable=False)         # specify length
    file_name = db.Column(db.String(255), nullable=False)         # common file name max
    file_path = db.Column(db.String(512), nullable=False)         # longer for S3 paths
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    tags = db.Column(db.String(255))                              # space for comma-separated tags
