import os

basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    # Flask session security
    SECRET_KEY = os.environ.get('SECRET_KEY', 'change-this-in-prod')

    # PostgreSQL connection string
    SQLALCHEMY_DATABASE_URI = "postgresql://postgres:rightskaleupload@files-upload-flask-app-postgres-db.cf2cokasiq2h.us-east-2.rds.amazonaws.com:5432/flask_upload_app"


    SQLALCHEMY_TRACK_MODIFICATIONS = False
