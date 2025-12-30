# from flask import Flask, request, jsonify
# from flask_cors import CORS  # Import CORS

import mysql.connector
from mysql.connector import Error
import os
import logging
import urllib.parse
import datetime
import resend

import redis
import bcrypt
# from flask_limiter import Limiter
# from flask_limiter.util import get_remote_address

from app.utils.rate_limit import limiter
from flask import Flask,jsonify
from flask_cors import CORS
from app.routes.email import email_bp
from app.routes.admin import admins_bp
from app.routes.guards import guards_bp

from app.routes.registeration import auth_bp

from app.routes.verification import verification_bp
from app.routes.compensation import compensation_bp
from app.routes.complaints import complaints_bp
from app.routes.update_status import update_status_bp,edit_payment_bp,update_form_bp
from app.routes.analytics import analytics_bp
from app.routes.pdf import pdf_bp
from app.config import Config

from flask_limiter.errors import RateLimitExceeded

logging.basicConfig(
    level=logging.DEBUG,  # Change to DEBUG to capture debug messages
    format="%(asctime)s - %(levelname)s - %(message)s"
)

app = Flask(__name__)

limiter.init_app(app)



app.config.from_object(Config)
CORS(app, supports_credentials=True, origins=[
    "http://localhost:5173",
    "https://anugraha-nine.vercel.app",
    "https://5173-idx-anugraha-1744834663194.cluster-ancjwrkgr5dvux4qug5rbzyc2y.cloudworkstations.dev"
])



app.logger.setLevel(logging.DEBUG)


# Register blueprints
app.register_blueprint(email_bp, url_prefix='/email')
app.register_blueprint(guards_bp, url_prefix='/guard')
app.register_blueprint(admins_bp, url_prefix='/admin')
app.register_blueprint(verification_bp, url_prefix='/verify')
app.register_blueprint(compensation_bp, url_prefix='/compensationform')
app.register_blueprint(complaints_bp, url_prefix='/complaints')
app.register_blueprint(update_status_bp, url_prefix='/update_form_status')
app.register_blueprint(edit_payment_bp, url_prefix='/edit')
app.register_blueprint(update_form_bp, url_prefix='/update')

app.register_blueprint(auth_bp, url_prefix='/')
app.register_blueprint(analytics_bp, url_prefix='/')
app.register_blueprint(pdf_bp, url_prefix='/')



def get_current_timestamp():
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")

@app.errorhandler(RateLimitExceeded)
def handle_rate_limit_exceeded(e):
    return jsonify({
        "error": "Too many requests",
        "message": str(e)
    }), 429


@app.route('/')
def home():
    return "Welcome to the Compensation App!"

if __name__ == '__main__':
    app.run(debug=True)
