from flask import Blueprint, request, jsonify
from app.models.database import create_connection
from mysql.connector import Error
from app.utils.tokenCheck import token_required

admins_bp = Blueprint('admins', __name__)


@admins_bp.route('/add', methods=['POST'])
@token_required
def add_emp(decoded_data):
    data = request.json
    connection = create_connection()
    cursor = None  # Initialize cursor to None

    if not connection:
        return jsonify({"error": "Failed to connect to database"}), 500

    # Basic required fields
    try:
        cursor = connection.cursor(dictionary=True)

        required_base = ['emp_id', 'Name', 'roll', 'mobile_number']
        for field in required_base:
            if field not in data or not data[field]:
                return jsonify({"error": f"Missing required field: {field}"}), 400

        emp_id = data['emp_id']
        name = data['Name']
        role = data['roll'].lower()
        mobile_number = data['mobile_number']

        # Define role-based required fields
        role_required_fields = {
            'ccf': ['Circle_CG'],
            'dfo': ['Circle_CG', 'division'],
            'sdo': ['Circle_CG', 'division', 'subdivision'],
            'ranger': ['Circle_CG', 'division', 'subdivision', 'range_'],
            'deputyranger': ['Circle_CG', 'division', 'subdivision', 'range_', 'Circle1'],
            'forestguard': ['Circle_CG', 'division', 'subdivision', 'range_', 'Circle1', 'beat']
        }

        if role not in role_required_fields:
            return jsonify({"error": f"Invalid role: {role}"}), 400

        # Check if all required fields for this role are provided
        for field in role_required_fields[role]:
            if field not in data or data[field] in [None, '']:
                return jsonify({"error": f"Missing required field for role '{role}': {field}"}), 400
        # Get optional values (might be None for some roles)
        circle = data.get('Circle_CG')
        division = data.get('division')
        subdivision = data.get('subdivision')
        range_ = data.get('range_')
        circle1 = data.get('Circle1')
        beat = data.get('beat')

        # Insert into DB
        query = """
            INSERT INTO emp 
            (emp_id, Name, roll, mobile_number, Circle_CG, division, subdivision, range_, Circle1, beat) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(query, (
            emp_id,
            name,
            role,
            mobile_number,
            circle,
            division,
            subdivision,
            range_,
            circle1,
            beat
        ))

        connection.commit()
        return jsonify({"message": "Employee added successfully"}), 201

    except Error as e:
        return jsonify({"error": str(e)}), 500

    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()

@admins_bp.route('/filter', methods=['POST'])
@token_required
def filter_emps(decoded_data):
    data = request.json 
    connection = create_connection()
    cursor = None  # Initialize cursor to None

    if not connection:
        return jsonify({"error": "Failed to connect to database"}), 500

    try:
        cursor = connection.cursor(dictionary=True)

        # Allowed filter fields → DB columns
        filters = {
            'roll': 'roll',
            'Circle_CG': 'Circle_CG',
            'division': 'division'
        }

        where_clauses = []
        params = []

        # Build WHERE clauses for each provided filter
        for key, column in filters.items():
            val = data.get(key)
            if val:
                where_clauses.append(f"{column} = %s")
                params.append(val)

        # Enforce at least one filter
        if not where_clauses:
            return jsonify({
                "error": "At least one of 'roll', 'Circle_CG' or 'division' must be provided."
            }), 400

        # Compose final query
        query = """
            SELECT *
            FROM emp
            WHERE
              """ + " AND ".join(where_clauses)

        cursor.execute(query, params)
        results = cursor.fetchall()

        return jsonify({"employees": results}), 200

    except Error as e:
        return jsonify({"error": str(e)}), 500

    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()

@admins_bp.route('/delete', methods=['POST'])
@token_required
def delete_emp(decoded_data):
    data = request.json
    connection = create_connection()
    cursor = None  # Initialize cursor to None

    if not connection:
        return jsonify({"error": "Failed to connect to database"}), 500

    try:
        cursor = connection.cursor(dictionary=True)
        # Required fields for deletion
        required_fields = ['emp_id', 'roll', 'mobile_number']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({"error": f"Missing required field: {field}"}), 400

        emp_id = data['emp_id']
        role = data['roll'].lower()
        mobile_number = data['mobile_number']


        # Check if employee exists
        cursor.execute("""
            SELECT * FROM emp 
            WHERE emp_id = %s AND roll = %s AND mobile_number = %s
        """, (emp_id, role, mobile_number))
        result = cursor.fetchone()

        if not result:
            return jsonify({"error": "Employee not found or data mismatch"}), 404

        # Delete employee
        cursor.execute("""
            DELETE FROM emp 
            WHERE emp_id = %s AND roll = %s AND mobile_number = %s
        """, (emp_id, role, mobile_number))
        connection.commit()

        return jsonify({"message": "Employee deleted successfully"}), 200

    except Error as e:
        return jsonify({"error": str(e)}), 500

    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()

@admins_bp.route('/bulk_add', methods=['POST'])
@token_required
def bulk_add_emps(decoded_data):
    data = request.json or {}
    employees = data.get('employees')
    if not employees or not isinstance(employees, list):
        return jsonify({"error": "Request body must include an 'employees' list"}), 400
    #print("DECODED TOKEN:", decoded_data)
    #pull circle & division from token payload
    token_emp = decoded_data.get('employee', {})
    circle = token_emp.get('Circle_CG')
    division = token_emp.get('division')

    # circle = "CG 1"
    # division = "Raipur"
    if not circle or not division:
        return jsonify({"error": "Token missing 'circle' or 'division'"}), 400

    connection = create_connection()
    cursor = None  # Initialize cursor to None

    if not connection:
        return jsonify({"error": "Failed to connect to database"}), 500

    try:
        cursor = connection.cursor(dictionary=True)

        # Base fields every record must have
        required_base = ['emp_id', 'Name', 'roll', 'mobile_number']
        # Only these four roles are allowed in bulk now
        role_required = {
            'sdo':           ['subdivision'],
            'ranger':        ['subdivision', 'range_'],
            'deputyranger':  ['subdivision', 'range_', 'Circle1'],
            'forestguard':   ['subdivision', 'range_', 'Circle1', 'beat']
        }

        inserted = []
        for idx, emp in enumerate(employees):
            # 1) Validate base fields
            for f in required_base:
                if not emp.get(f):
                    raise ValueError(f"[item {idx}] Missing required field: {f}")

            emp_id = emp['emp_id']
            name   = emp['Name']
            roll   = emp['roll'].lower()
            mobile = emp['mobile_number']

            # 2) Check role is one of the allowed four
            if roll not in role_required:
                raise ValueError(f"[item {idx}] Invalid role for bulk upload: {roll}")

            # 3) Validate role‑specific fields
            for f in role_required[roll]:
                if not emp.get(f):
                    raise ValueError(f"[item {idx}] Missing '{f}' for role '{roll}'")

            # 4) Extract optional extras
            subdivision = emp.get('subdivision')
            range_      = emp.get('range_')
            circle1     = emp.get('Circle1')
            beat        = emp.get('beat')

            # 5) Insert using circle/division from token
            query = """
                INSERT INTO emp
                  (emp_id, Name, roll, mobile_number,
                   Circle_CG, division, subdivision,
                   range_, Circle1, beat)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            params = (
                emp_id, name, roll, mobile,
                circle, division, subdivision,
                range_, circle1, beat
            )
            cursor.execute(query, params)
            inserted.append(emp_id)

        connection.commit()
        return jsonify({
            "message":  "Bulk insert successful",
            "inserted": inserted
        }), 201

    except ValueError as ve:
        connection.rollback()
        return jsonify({"error": str(ve)}), 400

    except Error as db_err:
        connection.rollback()
        return jsonify({"error": str(db_err)}), 500

    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()


@admins_bp.route('/update', methods=['PUT'])
@token_required
def update_emp(decoded_data):
    data = request.json
    connection = create_connection()
    cursor = None  # Initialize cursor to None

    if not connection:
        return jsonify({"error": "Failed to connect to database"}), 500

    try:
        cursor = connection.cursor(dictionary=True)

        # 1) Check base fields
        required_base = ['emp_id', 'Name', 'roll', 'mobile_number' , 'Circle_CG']
        for f in required_base:
            if f not in data or not data[f]:
                return jsonify({"error": f"Missing required field: {f}"}), 400

        emp_id       = data['emp_id']
        name         = data['Name']
        role         = data['roll'].lower()
        mobile       = data['mobile_number']
        circle       = data['Circle_CG']
        division     = data.get('division')
        subdivision  = data.get('subdivision')
        range_       = data.get('range_')
        circle1      = data.get('Circle1')
        beat         = data.get('beat')

        # 2) Role‑specific requirements
        role_required_fields = {
            'ccf':           ['Circle_CG'],
            'dfo':           ['Circle_CG', 'division'],
            'sdo':           ['Circle_CG', 'division', 'subdivision'],
            'ranger':        ['Circle_CG', 'division', 'subdivision', 'range_'],
            'deputyranger':  ['Circle_CG', 'division', 'subdivision', 'range_', 'Circle1'],
            'forestguard':   ['Circle_CG', 'division', 'subdivision', 'range_', 'Circle1', 'beat']
        }
        if role not in role_required_fields:
            return jsonify({"error": f"Invalid role: {role}"}), 400
        for f in role_required_fields[role]:
            if not data.get(f):
                return jsonify({"error": f"Missing '{f}' for role '{role}'"}), 400

        # 3) Build and execute UPDATE
        query = """
            UPDATE emp SET
              Name            = %s,
              roll            = %s,
              mobile_number   = %s,
              Circle_CG       = %s,
              division        = %s,
              subdivision     = %s,
              range_          = %s,
              Circle1         = %s,
              beat            = %s
            WHERE emp_id      = %s
        """
        params = (
            name, role, mobile,
            circle, division, subdivision,
            range_, circle1, beat,
            emp_id
        )
        cursor.execute(query, params)
        if cursor.rowcount == 0:
            return jsonify({"error": "Employee not found"}), 404

        connection.commit()
        return jsonify({"message": "Employee updated successfully"}), 200

    except Error as e:
        connection.rollback()
        return jsonify({"error": str(e)}), 500

    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()
@admins_bp.route('/deletebulk', methods=['POST'])
@token_required
def delete_bulk(decoded_data):
    connection = create_connection()
    cursor = None

    if not connection:
        return jsonify({"error": "Failed to connect to database"}), 500

    try:
        data = request.json or {}
        emp_ids = data.get('emp_ids')

        if not emp_ids or not isinstance(emp_ids, list):
            return jsonify({"error": "Request body must include an 'emp_ids' list"}), 400

        token_employee = decoded_data.get('employee')
        circle = token_employee.get('Circle_CG')
        division = token_employee.get('division')

        if not circle or not division:
            return jsonify({"error": "Token missing 'circle' or 'division'"}), 400

        cursor = connection.cursor(dictionary=True)

        # 1. Fetch employees whose emp_id is in emp_ids
        format_strings = ','.join(['%s'] * len(emp_ids))
        cursor.execute(f"""
            SELECT emp_id, Circle_CG, division FROM emp
            WHERE emp_id IN ({format_strings})
        """, tuple(emp_ids))
        employees = cursor.fetchall()

        if not employees:
            return jsonify({"message": "No employees found for the provided IDs"}), 404

        # 2. Filter employees whose circle and division match the token
        matching_emp_ids = [
            emp['emp_id']
            for emp in employees
            if emp['Circle_CG'] == circle and emp['division'] == division
        ]

        if not matching_emp_ids:
            return jsonify({"message": "No employees matched your circle and division"}), 404

        # 3. Delete only the matching employees
        format_strings_del = ','.join(['%s'] * len(matching_emp_ids))
        cursor.execute(f"""
            DELETE FROM emp
            WHERE emp_id IN ({format_strings_del})
        """, tuple(matching_emp_ids))
        connection.commit()

        return jsonify({
            "message": f"{len(matching_emp_ids)} employee(s) deleted successfully",
            "deleted_emp_ids": matching_emp_ids
        }), 200

    except Error as e:
        return jsonify({"error": str(e)}), 500

    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()


# @admins_bp.route('/deletebulk', methods=['POST'])
# @token_required
# def delete_bulk(decoded_data):
    connection = create_connection()
    cursor = None  # Initialize cursor to None

    if not connection:
        return jsonify({"error": "Failed to connect to database"}), 500

    try:
        # Extract employee from token
        employee = decoded_data.get("employee")

        if not employee:
            return jsonify({"error": "Employee information missing in token"}), 400

        circle = employee.get("Circle_CG")
        division = employee.get("division")

        if not circle or not division:
            return jsonify({"error": "Token does not contain required employee data (circle or division)"}), 400

        cursor = connection.cursor()

        # Check for employees in this circle and division
        cursor.execute("""
            SELECT COUNT(*) FROM emp 
            WHERE Circle_CG = %s AND division = %s
        """, (circle, division))
        count = cursor.fetchone()[0]

        if count == 0:
            return jsonify({"message": "No employees found for the given circle and division"}), 404

        # Delete employees
        cursor.execute("""
            DELETE FROM emp 
            WHERE Circle_CG = %s AND division = %s
        """, (circle, division))
        connection.commit()

        return jsonify({
            "message": f"{count} employee(s) deleted from division '{division}' in circle '{circle}'"
        }), 200

    except Error as e:
        return jsonify({"error": str(e)}), 500

    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()