from flask import Blueprint, request, jsonify
from app.models.database import create_connection
from mysql.connector import Error

guards_bp = Blueprint('guards', __name__)

@guards_bp.route('/', methods=['GET'])
def get_guards():
    connection = create_connection()
    if not connection:
        return jsonify({"error": "Failed to connect to database"}), 500
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM emp")
        result = cursor.fetchall()
        return jsonify(result)
    except Error as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()



@guards_bp.route('/<mobile_number>', methods=['GET'])
def get_guard_by_mobile_number(mobile_number):
    connection = create_connection()
    if not connection:
        return jsonify({"error": "Failed to connect to database"}), 500
    try:
        cursor = connection.cursor(dictionary=True)
        query = "SELECT * FROM emp WHERE mobile_number = %s"
        cursor.execute(query, (mobile_number,))
        result = cursor.fetchone()
        if result:
            return jsonify(result), 200
        else:
            return jsonify({"message": "Guard not found"}), 404
    except Error as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()
