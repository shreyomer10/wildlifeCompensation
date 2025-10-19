from flask import Blueprint, request, jsonify
from app.models.database import create_connection
from mysql.connector import Error

verification_bp = Blueprint('verification', __name__)

@verification_bp.route('/verify_guard', methods=['POST'])
def verify_guard():
    data = request.json

    # Ensure all required parameters are present
    required_fields = ['emp_id', 'mobile_number', 'roll', 'changePass']
    if not all(field in data for field in required_fields):
        return jsonify({"error": "Missing required parameters"}), 400

    changePass = data['changePass']
    if changePass not in ["0", "1"]:
        return jsonify({"error": "Invalid value for changePass"}), 400

    connection = create_connection()
    if not connection:
        return jsonify({"error": "Failed to connect to database"}), 500

    try:
        cursor = connection.cursor(dictionary=True)
        query = """
            SELECT emp_id, mobile_number, roll, password 
            FROM emp 
            WHERE emp_id = %s AND mobile_number = %s AND roll = %s
        """
        cursor.execute(query, (data['emp_id'], data['mobile_number'], data['roll']))
        result = cursor.fetchone()

        if result:
            if changePass == "0":  # Registration Page Check
                if result['password']:  # If password exists, reject registration
                    return jsonify({"message": "Already registered. Please login."}), 400
            
            # If changePass == "1", it ignores the password field and just verifies the employee
            return jsonify({"message": "Verified"}), 200

        else:
            return jsonify({"message": "Employee not found"}), 404

    except mysql.connector.Error as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

