import mysql.connector
import os
from mysql.connector import Error
# from dotenv import load_dotenv
# load_dotenv()
DATABASE_CONFIG = {
    'host': os.getenv('DB_HOST'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'database': os.getenv('DB_NAME'),
    'port': os.getenv('DB_PORT')
}
SECRET_KEY = os.getenv('SECRET_KEY')

def create_connection():
    try:
        connection = mysql.connector.connect(**DATABASE_CONFIG)
        if connection.is_connected():
            print("Connected to the database")
        return connection
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
        return None
