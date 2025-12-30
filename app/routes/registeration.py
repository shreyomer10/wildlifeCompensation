from flask import Blueprint, request, jsonify,make_response
from flask_cors import CORS
import mysql.connector
import os
import bcrypt
import jwt
import datetime
from functools import wraps
from app.models.database import create_connection
import datetime
from app.models.database import SECRET_KEY
from app.utils.tokenCheck import token_required
from app.utils.rate_limit import limiter
auth_bp = Blueprint('auth', __name__)


@limiter.limit("5 per minute")
@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.json
    emp_id = data.get('emp_id')
    mobile_number = data.get('mobile_number')
    roll = data.get('roll')
    raw_password = data.get('password')

    if not emp_id or not mobile_number or not roll or not raw_password:
        return jsonify({"error": "Missing emp_id, mobile_number, roll, or password"}), 400

    connection = create_connection()
    if not connection:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        cursor = connection.cursor(dictionary=True)

        # Check if employee exists and fetch their password
        query = "SELECT emp_id, password FROM emp WHERE emp_id = %s AND mobile_number = %s AND roll = %s"
        cursor.execute(query, (emp_id, mobile_number, roll))
        emp = cursor.fetchone()

        if emp:
            # If password is already set, return an error
            if emp['password']:
                return jsonify({"error": "Employee already registered. Please login."}), 400

            # Hash the password before storing it
            hashed_password = bcrypt.hashpw(raw_password.encode('utf-8'), bcrypt.gensalt())

            # Update password in the emp table
            update_query = "UPDATE emp SET password = %s WHERE emp_id = %s"
            cursor.execute(update_query, (hashed_password, emp_id))
            connection.commit()

            # Store password in password_history table
            insert_history_query = "INSERT INTO password_history (emp_id, previous_password) VALUES (%s, %s)"
            cursor.execute(insert_history_query, (emp_id, hashed_password))
            connection.commit()

            return jsonify({"message": "Registration successful. Please login."}), 200
        else:
            return jsonify({"error": "Employee not found. Please contact admin."}), 404

    except mysql.connector.Error as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        connection.close()

@limiter.limit("1 per day")
@auth_bp.route('/updatePassword', methods=['POST'])
def updatePass():
    data = request.json
    emp_id = data.get('emp_id')
    mobile_number = data.get('mobile_number')
    roll = data.get('roll')
    raw_password = data.get('password')

    if not emp_id or not mobile_number or not roll or not raw_password:
        return jsonify({"error": "Missing emp_id, mobile_number, roll, or password"}), 400

    connection = create_connection()
    if not connection:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        cursor = connection.cursor(dictionary=True)

        # Fetch the current password
        query = "SELECT emp_id, password FROM emp WHERE emp_id = %s AND mobile_number = %s AND roll = %s"
        cursor.execute(query, (emp_id, mobile_number, roll))
        emp = cursor.fetchone()

        if not emp:
            return jsonify({"error": "Employee not found. Please contact admin."}), 404

        current_password = emp['password']

        # Fetch all previous passwords from password_history
        history_query = "SELECT previous_password FROM password_history WHERE emp_id = %s"
        cursor.execute(history_query, (emp_id,))
        previous_passwords = [row['previous_password'] for row in cursor.fetchall()]

        # Check if new password matches any previous ones
        for old_password in previous_passwords:
            if bcrypt.checkpw(raw_password.encode('utf-8'), old_password.encode('utf-8')):
                return jsonify({"error": "New password cannot be the same as any previous passwords."}), 400

        # Hash the new password
        hashed_password = bcrypt.hashpw(raw_password.encode('utf-8'), bcrypt.gensalt())

        # Store password in password_history table
        insert_history_query = "INSERT INTO password_history (emp_id, previous_password) VALUES (%s, %s)"
        cursor.execute(insert_history_query, (emp_id, hashed_password))
        connection.commit()

        # Update new password in emp table
        update_query = "UPDATE emp SET password = %s WHERE emp_id = %s"
        cursor.execute(update_query, (hashed_password, emp_id))
        connection.commit()

        return jsonify({"message": "Password updated successfully. Please login."}), 200

    except mysql.connector.Error as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        connection.close()

@limiter.limit("5 per minute")
@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.json
    user_agent = request.headers.get('User-Agent')
    ip_address = request.headers.get('X-Forwarded-For', request.remote_addr)
    emp_id = data.get('emp_id')
    roll = data.get('roll')
    mobile_number = data.get('mobile_number')
    raw_password = data.get('password')
    is_app = data.get('is_app', False)  # <-- client flag

    if not emp_id or not roll or not raw_password or not mobile_number:
        return jsonify({"message": "Missing emp_id, roll, password, or mobile_number"}), 400

    connection = create_connection()
    if not connection:
        return jsonify({"message": "Database connection failed"}), 500

    login_status = "failed"  # Ensure login_status is always initialized

    try:
        cursor = connection.cursor(dictionary=True)

        query = """
            SELECT * FROM emp 
            WHERE emp_id = %s AND mobile_number = %s AND roll = %s
        """
        cursor.execute(query, (emp_id, mobile_number, roll))
        emp = cursor.fetchone()

        if not emp:
            return jsonify({"message": "Employee not found"}), 404

        passDb = emp.get('password')
        if not passDb:
            return jsonify({"message": "Not yet Registered"}), 400

        stored_password = passDb.encode('utf-8')

        if bcrypt.checkpw(raw_password.encode('utf-8'), stored_password):



            # Get the last successful login before this one
            cursor.execute("""
                SELECT login_time, ip_address, user_agent 
                FROM login_history 
                WHERE emp_id = %s AND status = 'success' 
                ORDER BY login_time DESC 
                LIMIT 1 OFFSET 1
            """, (emp_id,))
            last_login = cursor.fetchone()

            login_status = "success"

            emp.pop('password', None)  # Remove password from the employee data
            
            token_payload = {
                "emp_id": emp_id,
                "employee": emp,
                "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=2)
            }
            token = jwt.encode(
                token_payload,
                SECRET_KEY,
                algorithm="HS256"
            )
            if is_app:
                # ✅ Return token in JSON for mobile apps
                return jsonify({
                    "message": "Login successful",
                    "token": token,
                    "employee": emp,
                    "last_login": last_login

                }), 200
            else:
                # ✅ Set token in secure HttpOnly cookie for web
                response = make_response(jsonify({
                    "message": "Login successful",
                    "employee": emp,
                    "last_login": last_login

                }))
                response.set_cookie(
                    "tokenId",
                    token,
                    httponly=True,
                    secure=True,
                    samesite='None',
                    max_age=2 * 60 * 60  # 2 hours
                )
                return response, 200
        else:
            return jsonify({"message": "Incorrect password"}), 401

    except mysql.connector.Error as e:
        return jsonify({"message": str(e)}), 500

    finally:
        try:

            if connection and connection.is_connected():
                cursor = connection.cursor()
                insert_login_history = """
                    INSERT INTO login_history (emp_id, login_time, status, ip_address, user_agent)
                    VALUES (%s, NOW(), %s, %s, %s)
                """
                cursor.execute(insert_login_history, (emp_id, login_status, ip_address, user_agent))

                connection.commit()
                cursor.close()
        except mysql.connector.Error as e:
            print("Error logging login attempt:", e)
        finally:
            if connection and connection.is_connected():
                connection.close()


@auth_bp.route('/refresh', methods=['POST'])
@token_required
@limiter.limit("5 per minute")
def refresh_token(decoded_data):
    try:
        new_payload = {
            "emp_id": decoded_data.get("emp_id"),
            "employee": decoded_data.get("employee"),
            "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=2)  # New token valid for 1 minute
        }
        new_token = jwt.encode(new_payload, SECRET_KEY, algorithm="HS256")
        return jsonify({"message": "Token refreshed successfully", "token": new_token, "employee": decoded_data["employee"]}), 200
    except Exception as e:
       # logging.error(f"Error refreshing token: {e}")
        return jsonify({"error": "Failed to refresh token", "details": str(e)}), 500
