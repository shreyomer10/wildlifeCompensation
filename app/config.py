import os

from dotenv import load_dotenv
load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY')
    DB_HOST = os.getenv('DB_HOST')
    DB_USER = os.getenv('DB_USER')
    DB_PASSWORD = os.getenv('DB_PASSWORD')
    DB_NAME = os.getenv('DB_NAME')
    DB_PORT = os.getenv('DB_PORT')
    REDIS_URL =os.getenv('REDIS_URL')
    FirebaseKey=os.getenv('GOOGLE_APPLICATION_CREDENTIALS_JSON')
    FIREBASE_CERT_PATH = os.getenv("FIREBASE_CERT_PATH")
    PINECONE_API_KEY=os.getenv('PINECONE_API_KEY')
    PINECONE_ENV=os.getenv('PINECONE_ENV')
    PINECONE_INDEX=os.getenv('PINECONE_INDEX')
