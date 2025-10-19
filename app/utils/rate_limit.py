# app/utils/rate_limit.py
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask import request
from flask_limiter.util import get_remote_address
import jwt
from app.models.database import SECRET_KEY
from app.config import Config

db_config = {
    "host": Config.DB_HOST,
    "user": Config.DB_USER,
    "password": Config.DB_PASSWORD,
    "database": Config.DB_NAME,
    "port": Config.DB_PORT,
    "Redis_URL":Config.REDIS_URL
}


def get_user_or_ip():
    token = None

    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
    else:
        token = request.cookies.get("tokenId")

    if token:
        try:
            decoded = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
            return decoded.get("emp_id")
        except Exception:
            pass  # fallback to IP

    return get_remote_address()

limiter = Limiter(
    key_func=get_user_or_ip,
    storage_uri=db_config["Redis_URL"],
    default_limits=["1000 per day", "200 per hour"])
