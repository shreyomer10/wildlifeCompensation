import json
import datetime
import logging
from flask import Blueprint, request, jsonify
from app.models.database import create_connection
import mysql.connector
from app.utils.tokenCheck import token_required

update_status_bp = Blueprint('update_status', __name__)

edit_payment_bp = Blueprint('edit_payment', __name__)
update_form_bp = Blueprint('update_form', __name__)



@update_status_bp.route('/<int:form_id>', methods=['POST'])
@token_required
def update_form_status(decoded_data, form_id):
    data = request.json
    emp_id = data.get("emp_id")
    action = data.get("action")
    comments = data.get("comments", "")
    
    # Validate required fields
    if not emp_id or not action:
        return jsonify({"error": "Missing required fields: emp_id or action"}), 400

    # JWT authorization check: the emp_id in token must match the emp_id in the request
    if str(decoded_data.get("emp_id")) != str(emp_id):
        return jsonify({"error": "Unauthorized access"}), 403
        # 1) Extract the employee's role from the token payload
    emp_roll = decoded_data.get("employee", {}).get("roll")
    if not emp_roll:
        return jsonify({"error": "Invalid token: missing employee role"}), 403

    # 2) Define the mapping of form‐status ↔ role‐levels
    role_levels = {
        "forestguard":      1,
        "deputyranger":     2,
        "ranger":           3,
        "sdo":              4,
        "dfo":              5,
        # 6 is 'accepted' final state, -1 is 'rejected' final state — 
        # these are not tied to any role.
    }
    employee_level = role_levels.get(emp_roll.lower())
    if employee_level is None:
        return jsonify({"error": f"Unknown employee role: {emp_roll}"}), 403


    connection = create_connection()
    if not connection:
        return jsonify({"error": "Failed to connect to database"}), 500

    try:
        cursor = connection.cursor(dictionary=True)
        query = "SELECT status, verifiedBy, statusHistory, complaint_id FROM compensationform WHERE FormID = %s"
        cursor.execute(query, (form_id,))
        form = cursor.fetchone()
        if not form:
            return jsonify({"error": "Form not found"}), 404

        status_str, verified_by, status_history_json, complaint_id = (
            form["status"], form["verifiedBy"], form["statusHistory"], form["complaint_id"]
        )
        verified_by = verified_by if verified_by else ""
        try:
            current_status = int(status_str)
        except ValueError:
            return jsonify({"error": "Invalid status value in database"}), 500
        
        if current_status not in role_levels.values() or current_status != employee_level:
            return jsonify({
                "error": (
                    f"Action not allowed: form is at status {current_status}, "
                    f"but your role '{emp_roll}' is level {employee_level}"
                )
            }), 403

        # Determine next status based on the action
        if action == "accept":
            next_status = current_status + 1
        elif action == "reject":
            next_status = -1
        elif action == "send_back":
            next_status = max(2, current_status - 1)
        else:
            return jsonify({"error": "Invalid action"}), 400

        next_status_str = str(next_status)
        # Add emp_id to verified_by if it's not already present
        if emp_id not in verified_by.split(","):
            verified_by = (verified_by + "," + emp_id).strip(",")

        # Load existing status history
        try:
            status_history = json.loads(status_history_json) if status_history_json else []
        except json.JSONDecodeError:
            status_history = []

        current_timestamp = datetime.datetime.utcnow().isoformat() + "Z"
        new_status_entry = {
            "timestamp": current_timestamp,
            "status": next_status_str,
            "comment": comments,
            "updatedBy": emp_id
        }
        status_history.append(new_status_entry)
        updated_status_history_json = json.dumps(status_history)

        update_query = """
        UPDATE compensationform
        SET status = %s, verifiedBy = %s, comments = COALESCE(%s, comments), statusHistory = %s
        WHERE FormID = %s
        """
        cursor.execute(update_query, (
            next_status_str,
            verified_by,
            comments if comments else None,
            updated_status_history_json,
            form_id
        ))

        # Update complaint status history if complaint_id exists
        if complaint_id:
            query = "SELECT statusHistory FROM complaints WHERE complaint_id = %s"
            cursor.execute(query, (complaint_id,))
            complaint_info = cursor.fetchone()
            complaint_status_history = []
            if complaint_info and complaint_info['statusHistory']:
                try:
                    complaint_status_history = json.loads(complaint_info['statusHistory'])
                except json.JSONDecodeError:
                    pass

            complaint_status_entry = {
                "timestamp": current_timestamp,
                "status": next_status_str,
                "comment": comments,
                "updatedBy": emp_id
            }
            complaint_status_history.append(complaint_status_entry)
            updated_complaint_status_history_json = json.dumps(complaint_status_history)
            update_complaint_query = """
            UPDATE complaints
            SET status = %s, statusHistory = %s
            WHERE complaint_id = %s
            """
            cursor.execute(update_complaint_query, (
                next_status_str,
                updated_complaint_status_history_json,
                complaint_id
            ))

        connection.commit()
        return jsonify({
            "message": f"Form {form_id} status updated successfully",
            "new_status": next_status_str,
            "verified_by": verified_by
        }), 200

    except mysql.connector.Error as e:
        logging.error(f"Database error: {e}")
        return jsonify({"error": str(e)}), 500

    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

@edit_payment_bp.route('/editForm/<int:form_id>', methods=['POST'])
@token_required
def edit_payment_fields(decoded_data ,form_id):
    data = request.json
    emp_id = data.get("emp_id")
    updates = data.get("payment_fields", {})  # dictionary of fields to update
    comments = data.get("comments", "")

    if not emp_id or not updates:
        return jsonify({"error": "Missing emp_id or payment_fields"}), 400

    if str(decoded_data.get("emp_id")) != str(emp_id):
        return jsonify({"error": "Unauthorized access"}), 403

    emp_role = decoded_data.get("employee", {}).get("roll")
    #emp_role = "deputyranger"

    role_levels = {
        "forestguard": 1,
        "deputyranger": 2,
        "ranger": 3,
        "sdo": 4,
        "dfo": 5
    }
    employee_level = role_levels.get(emp_role.lower())
    if not employee_level or employee_level <= 1:
        return jsonify({"error": "Not authorized to edit payment details"}), 403

    connection = create_connection()
    if not connection:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        cursor = connection.cursor(dictionary=True)

        cursor.execute("SELECT Status, statusHistory FROM compensationform WHERE FormID = %s", (form_id,))
        form = cursor.fetchone()
        if not form:
            return jsonify({"error": "Form not found"}), 404

        current_status = int(form["Status"])
        if current_status != employee_level:
            return jsonify({
                "error": f"Form is at status {current_status}, but your role level is {employee_level}"
            }), 403

        allowed_fields = {
            "cropDamageAmount", "houseDamageAmount", "catleInjuryAmount",
            "humanDeathAmount", "humanInjuryAmount", "PaymentProcessedBy"
        }
        set_clauses = []
        values = []

        # Initialize component amounts to 0
        compensation_fields = {
            "cropDamageAmount": 0,
            "houseDamageAmount": 0,
            "catleInjuryAmount": 0,
            "humanDeathAmount": 0,
            "humanInjuryAmount": 0
        }

        for field, value in updates.items():
            if field == "totalCompensationAmount":
                continue  # Ignore this field from request
            if field not in allowed_fields:
                return jsonify({"error": f"Field '{field}' is not editable"}), 400

            set_clauses.append(f"{field} = %s")
            values.append(value)

            if field in compensation_fields:
                compensation_fields[field] = float(value) if value else 0

        # Compute totalCompensationAmount
        total_comp = sum(compensation_fields.values())
        set_clauses.append("totalCompensationAmount = %s")
        values.append(total_comp)

        if not set_clauses:
            return jsonify({"error": "No valid fields provided to update"}), 400

        # Load and update status history
        try:
            status_history = json.loads(form["statusHistory"]) if form["statusHistory"] else []
        except json.JSONDecodeError:
            status_history = []

        current_timestamp = datetime.datetime.utcnow().isoformat() + "Z"
        status_history.append({
            "timestamp": current_timestamp,
            "status": str(current_status),
            "comment": f"Payment fields updated: {', '.join(updates.keys())}. {comments}",
            "updatedBy": emp_id
        })

        set_clauses.append("statusHistory = %s")
        values.append(json.dumps(status_history))

        values.append(form_id)

        update_query = f"""
        UPDATE compensationform
        SET {', '.join(set_clauses)}
        WHERE FormID = %s
        """
        cursor.execute(update_query, tuple(values))
        complaint_id=form["complaint_id"]


                # Update complaint status history if complaint_id exists
        if complaint_id:
            query = "SELECT statusHistory FROM complaints WHERE complaint_id = %s"
            cursor.execute(query, (complaint_id,))
            complaint_info = cursor.fetchone()
            complaint_status_history = []
            if complaint_info and complaint_info['statusHistory']:
                try:
                    complaint_status_history = json.loads(complaint_info['statusHistory'])
                except json.JSONDecodeError:
                    pass

            complaint_status_entry = {
                "timestamp": current_timestamp,
                "status": str(current_status),
                "comment": f"Payment fields updated: {', '.join(updates.keys())}. {comments}",
                "updatedBy": emp_id
            }
            complaint_status_history.append(complaint_status_entry)
            updated_complaint_status_history_json = json.dumps(complaint_status_history)
            update_complaint_query = """
            UPDATE complaints
            SET status = %s, statusHistory = %s
            WHERE complaint_id = %s
            """
            cursor.execute(update_complaint_query, (
                current_status,
                updated_complaint_status_history_json,
                complaint_id
            ))

        connection.commit()

        return jsonify({
            "message": f"Payment details updated for FormID {form_id}",
            "updated_fields": list(updates.keys()) + ["totalCompensationAmount"]
        }), 200

    except mysql.connector.Error as e:
        logging.error(f"Database error: {e}")
        return jsonify({"error": "Database error"}), 500

    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()


@update_form_bp.route('/<int:formid>', methods=['PUT'])
@token_required
def update_compensation_form(decoded_data,formid):
    data = request.json
    emp_roll = decoded_data.get("employee", {}).get("roll")


    if emp_roll != 'forestguard':
        return jsonify({"error": "Unauthorized. Only forestguards are allowed."}), 403

    forest_guard_id = data.get('forestGuardID')
    #forest_guard_id = "shrey"

    if not forest_guard_id:
        return jsonify({"error": "Missing forestGuardID"}), 400

    if str(decoded_data.get("emp_id")) != str(forest_guard_id):
        return jsonify({"error": "Unauthorized. Mismatched forestGuardID."}), 403

    connection = create_connection()
    if not connection:
        return jsonify({"error": "Failed to connect to database"}), 500

    try:
        cursor = connection.cursor(dictionary=True)

        # Check if form exists
        cursor.execute("SELECT * FROM compensationform WHERE formid = %s", (formid,))
        form = cursor.fetchone()
        if not form:
            return jsonify({"error": "Compensation form not found"}), 404

        # Allowed fields to be updated
        allowed_fields = {
            "ApplicantName": data.get('ApplicantName'),
            "Age": data.get('Age'),
            "FatherSpouseName": data.get('FatherSpouseName'),
            "Mobile": data.get('Mobile'),
            "email": data.get('email'),
            "IncidentDate": data.get('IncidentDate'),
            "AdditionalDetails": data.get('AdditionalDetails'),
            "Address": data.get('Address'),
            "nocReport": data.get('nocReport'),
            "landOwnershipReport": data.get('landOwnershipReport'),
            "rorReport": data.get('rorReport'),
            "propertyOwnerReport": data.get('propertyOwnerReport'),
            "vasCertificate": data.get('vasCertificate'),
            "deathCertificate": data.get('deathCertificate'),
            "sarpanchReport": data.get('sarpanchReport'),
            "pmReport": data.get('pmReport'),
            "medicalCertificate": data.get('medicalCertificate'),
            "IdProof": data.get('IdProof'),
            "photoUrl": data.get('photoUrl'),
            "eSignUrl": data.get('eSignUrl'),
            "comments":data.get('comments')
        }

        update_fields = {k: v for k, v in allowed_fields.items() if v is not None}
        if not update_fields:
            return jsonify({"error": "No valid fields provided for update"}), 400

        set_clause = ", ".join([f"{key} = %s" for key in update_fields])
        values = list(update_fields.values())

        # Load and update status history
        try:
            status_history = json.loads(form.get("statusHistory") or "[]")
        except json.JSONDecodeError:
            status_history = []

        current_status = form.get("Status")
        timestamp = datetime.datetime.utcnow().isoformat() + "Z"

        status_history.append({
            "timestamp": timestamp,
            "status": str(current_status),
            "comment": str(data.get('comments')),
            "updatedBy": forest_guard_id
        })

        set_clause += ", statusHistory = %s"
        values.append(json.dumps(status_history))

        values.append(formid)

        update_query = f"""
            UPDATE compensationform
            SET {set_clause}
            WHERE formid = %s
        """
        cursor.execute(update_query, values)
        complaint_id=form["complaint_id"]

        if complaint_id:
            query = "SELECT statusHistory FROM complaints WHERE complaint_id = %s"
            cursor.execute(query, (complaint_id,))
            complaint_info = cursor.fetchone()
            complaint_status_history = []
            if complaint_info and complaint_info['statusHistory']:
                try:
                    complaint_status_history = json.loads(complaint_info['statusHistory'])
                except json.JSONDecodeError:
                    pass

            complaint_status_entry = {
                "timestamp": timestamp,
                "status": str(current_status),
                "comment": str(data.get('comments')),
                "updatedBy": forest_guard_id
            }
            complaint_status_history.append(complaint_status_entry)
            updated_complaint_status_history_json = json.dumps(complaint_status_history)
            update_complaint_query = """
            UPDATE complaints
            SET status = %s, statusHistory = %s
            WHERE complaint_id = %s
            """
            cursor.execute(update_complaint_query, (
                current_status,
                updated_complaint_status_history_json,
                complaint_id
            ))
        connection.commit()

        return jsonify({
            "message": "Compensation form updated successfully",
            "updated_fields": list(update_fields.keys())
        }), 200

    except Exception as e:
        print("Error:", e)
        return jsonify({"error": "Internal server error"}), 500

    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()
