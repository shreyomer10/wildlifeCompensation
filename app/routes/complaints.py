import json
import logging
from flask import Blueprint, request, jsonify
from app.models.database import create_connection
import datetime
from app.utils.rate_limit import limiter
from app.utils.tokenCheck import token_required
complaints_bp = Blueprint('complaints', __name__)


@limiter.limit("5 per minute")
@complaints_bp.route('/submit_complaint', methods=['POST'])
def submit_complaint():
    data = request.json
    connection = create_connection()
    if not connection:
        return jsonify({"error": "Failed to connect to database"}), 500
    try:
        #status_history = data.get('statusHistory', [])
        status = "1"
        status_history = [{
            "timestamp": datetime.datetime.now().isoformat(),
            "status": "1",
            "comment": "Submitted Successfully by User",
            "updatedBy": data['mobile']
        }]
        status_history_json = json.dumps(status_history)
        cursor = connection.cursor(dictionary=True)
        query = """
        INSERT INTO complaints (
            name, age, fatherOrSpouseName, mobile, email,adhaar, animalList, damageDate, additionalDetails,
            address,circle_cg, division, subdivision, range_, circle1, beat, cropType, cerealCrop,
            fullHousesDamaged, partialHousesDamaged, cattleInjuryNumber, cattleInjuryEstimatedAge,
            humanDeathVictimNames, humanDeathNumber, temporaryInjuryDetails, permanentInjuryDetails,
            photoUrl, eSignUrl, incidentUrl1, incidentUrl2, incidentUrl3, status, statusHistory
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,%s,%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(query, (
            data['name'], data['age'], data['fatherOrSpouseName'], data['mobile'], data['email'], data['adhaar'],data['animalList'],
            data['damageDate'], data['additionalDetails'], data['address'], data['Circle_CG'],data['division'], data['subdivision'],
            data['range_'], data['circle1'], data['beat'], data['cropType'], data['cerealCrop'],
            data['fullHousesDamaged'], data['partialHousesDamaged'], data['cattleInjuryNumber'],
            data['cattleInjuryEstimatedAge'], data['humanDeathVictimNames'], data['humanDeathNumber'],
            data['temporaryInjuryDetails'], data['permanentInjuryDetails'], data['photoUrl'], data['eSignUrl'],
            data['incidentUrl1'], data['incidentUrl2'], data['incidentUrl3'], status, status_history_json
        ))
        complaint_id = cursor.lastrowid
        connection.commit()
        return jsonify({"message": "Complaint submitted successfully", "complaint_id": complaint_id}), 201
    except Exception as e:
        logging.error(f"Database error: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()


@limiter.limit("5 per minute")
@complaints_bp.route('/get_complaint', methods=['POST'])
def get_complaint():
    data = request.json
    complaint_id = data.get('complaint_id')
    mobile = data.get('mobile')
    if not complaint_id and not mobile:
        return jsonify({"error": "Please provide complaint_id or mobile number"}), 400
    connection = create_connection()
    if not connection:
        return jsonify({"error": "Failed to connect to database"}), 500
    try:
        cursor = connection.cursor(dictionary=True)
        query = "SELECT * FROM complaints WHERE complaint_id = %s AND mobile = %s"
        cursor.execute(query, (complaint_id, mobile))
        result = cursor.fetchone()
        if not result:
            return jsonify({"found": "no", "message": "No records found"}), 404
        try:
            status_history = json.loads(result["statusHistory"]) if result["statusHistory"] else []
        except json.JSONDecodeError:
            status_history = []
        complaint_data = {
            "complaint_id": result["complaint_id"],
            "SubmissionDateTime": result["SubmissionDateTime"],
            "name": result["name"],
            "age": result["age"],
            "fatherOrSpouseName": result["fatherOrSpouseName"],
            "mobile": result["mobile"],
            "email": result["email"],
            "adhaar":result["adhaar"],
            "animalList": result["animalList"],
            "damageDate": result["damageDate"],
            "additionalDetails": result["additionalDetails"],
            "address": result["address"],
            "Circle_CG":result["circle_cg"],
            "division": result["division"],
            "subdivision": result["subdivision"],
            "range_": result["range_"],
            "circle1": result["circle1"],
            "beat": result["beat"],
            "cropType": result["cropType"],
            "cerealCrop": result["cerealCrop"],
            "fullHousesDamaged": result["fullHousesDamaged"],
            "partialHousesDamaged": result["partialHousesDamaged"],
            "cattleInjuryNumber": result["cattleInjuryNumber"],
            "cattleInjuryEstimatedAge": result["cattleInjuryEstimatedAge"],
            "humanDeathVictimNames": result["humanDeathVictimNames"],
            "humanDeathNumber": result["humanDeathNumber"],
            "temporaryInjuryDetails": result["temporaryInjuryDetails"],
            "permanentInjuryDetails": result["permanentInjuryDetails"],
            "photoUrl": result["photoUrl"],
            "eSignUrl": result["eSignUrl"],
            "incidentUrl1": result["incidentUrl1"],
            "incidentUrl2": result["incidentUrl2"],
            "incidentUrl3": result["incidentUrl3"],
            "status": result["status"],
            "statusHistory": status_history
        }
        return jsonify({"found": "yes", "complaint": complaint_data}), 200
    except Exception as e:
        logging.error(f"Database error: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

@complaints_bp.route('/get_guard_complaints', methods=['POST'])
@token_required
def get_guard_complaints(decoded_data):
    data = request.json
    guard_id = data.get('guardId')

    if not guard_id:
        return jsonify({"error": "Missing guardId"}), 400
    print(decoded_data["emp_id"])

    if decoded_data["emp_id"] != guard_id:
        return jsonify({"error": "Unauthorized access"}), 403

    connection = create_connection()
    if not connection:
        return jsonify({"error": "Failed to connect to database"}), 500

    try:
        cursor = connection.cursor(dictionary=True)
        query = """
         SELECT Circle_CG,division, subdivision, range_, circle1, beat 
         FROM emp WHERE emp_id = %s
         """
        cursor.execute(query, (guard_id,))
        guard_info = cursor.fetchone()

        if not guard_info:
            return jsonify({"error": "Guard not found"}), 404

        #guard_info['beat'] = f"Beat {guard_info['beat']}"
        #guard_info['beat'] = f"Beat {guard_info['beat']}"

        query = """
        SELECT complaint_id, SubmissionDateTime, name, mobile, damageDate, status, statusHistory
        FROM complaints
        WHERE circle_cg =%s AND division = %s AND subdivision = %s AND range_ = %s 
            AND circle1 = %s AND beat = %s AND status = "1"
        """
        params = (
            guard_info['Circle_CG'],
            guard_info['division'],
            guard_info['subdivision'],
            guard_info['range_'],
            guard_info['circle1'],
            guard_info['beat']
        )
        cursor.execute(query, params)
        complaints = cursor.fetchall()

        if not complaints:
            return jsonify({"message": "No complaints found"}), 404

        for complaint in complaints:
            if 'statusHistory' in complaint and complaint['statusHistory']:
                try:
                    complaint['statusHistory'] = json.loads(complaint['statusHistory'])
                except json.JSONDecodeError:
                    complaint['statusHistory'] = []

        return jsonify({"found": "yes", "complaints": complaints}), 200

    except Exception as e:
        logging.error(f"Database error: {e}")
        return jsonify({"error": str(e)}), 500

    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

@complaints_bp.route('/one/<string:form_id>', methods=['GET'])
@token_required
def eachComplaint(decoded_data,form_id):
    
    connection = create_connection()
    if not connection:
        return jsonify({"error": "Failed to connect to database"}), 500

    try:
        guard_id=decoded_data["emp_id"]
        cursor = connection.cursor(dictionary=True)
        query = """
         SELECT Circle_CG,division, subdivision, range_, circle1, beat 
         FROM emp WHERE emp_id = %s
         """
        cursor.execute(query, (guard_id,))
        guard_info = cursor.fetchone()

        if not guard_info:
            return jsonify({"error": "Guard not found"}), 404

        #guard_info['beat'] = f"Beat {guard_info['beat']}"
        #guard_info['beat'] = f"Beat {guard_info['beat']}"

        query = """
        SELECT * FROM complaints
        WHERE circle_cg =%s AND division = %s AND subdivision = %s AND range_ = %s 
              AND circle1 = %s AND beat = %s AND status = "1" AND complaint_id =%s
        """
        params = (
            guard_info['Circle_CG'],
            guard_info['division'],
            guard_info['subdivision'],
            guard_info['range_'],
            guard_info['circle1'],
            guard_info['beat'],
            form_id
        )
        cursor.execute(query, params)
        complaint = cursor.fetchone()

        if not complaint:
            return jsonify({"message": "No complaints found"}), 404
        try:
            status_history = json.loads(complaint["statusHistory"]) if complaint["statusHistory"] else []
        except json.JSONDecodeError:
            status_history = []
        complaint["statusHistory"] = status_history  # Replace string with list

        return jsonify({"found": "yes", "complaint": complaint}), 200

    except Exception as e:
        logging.error(f"Database error: {e}")
        return jsonify({"error": str(e)}), 500

    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()


@complaints_bp.route('/reject_complaint', methods=['POST'])
@token_required
def reject_complaint(decoded_data):
    data = request.json
    complaint_id = data.get('complaint_id')
    guard_id = data.get('guardId')
    comment = data.get('comment')

    if not all([complaint_id, guard_id, comment]):
        return jsonify({"error": "Missing complaint_id, guardId, or comment"}), 400

    # Check if the decoded emp_id matches the provided guardId
    if str(decoded_data.get("emp_id")) != str(guard_id):
        return jsonify({"error": "Unauthorized access!"}), 403

    connection = create_connection()
    if not connection:
        return jsonify({"error": "Failed to connect to database"}), 500

    try:
        cursor = connection.cursor(dictionary=True)

        query = """
        SELECT Circle_CG,division, subdivision, range_, circle1, beat
        FROM emp WHERE emp_id = %s
        """
        cursor.execute(query, (guard_id,))
        guard_info = cursor.fetchone()
        if not guard_info:
            return jsonify({"error": "Guard not found"}), 404

        query = """
        SELECT circle_cg ,division, subdivision, range_, circle1, beat, statusHistory
        FROM complaints WHERE complaint_id = %s
        """
        cursor.execute(query, (complaint_id,))
        complaint_info = cursor.fetchone()
        if not complaint_info:
            return jsonify({"error": "Complaint not found"}), 404

        if (guard_info['Circle_CG'] != complaint_info['circle_cg'] or
            guard_info['division'] != complaint_info['division'] or
            guard_info['subdivision'] != complaint_info['subdivision'] or
            guard_info['range_'] != complaint_info['range_'] or
            guard_info['circle1'] != complaint_info['circle1'] or
            guard_info['beat'] != complaint_info['beat']):
            return jsonify({"error": "Guard does not have permission to reject this complaint"}), 403

        status_history = []
        if complaint_info['statusHistory']:
            try:
                status_history = json.loads(complaint_info['statusHistory'])
            except json.JSONDecodeError:
                pass

        rejection_entry = {
            "timestamp": datetime.datetime.now().isoformat(),
            "status": "-1",
            "comment": comment,
            "updatedBy": guard_id
        }
        status_history.append(rejection_entry)
        status_history_json = json.dumps(status_history)

        update_query = """
        UPDATE complaints 
        SET status = %s, statusHistory = %s
        WHERE complaint_id = %s
        """
        cursor.execute(update_query, ("-1", status_history_json, complaint_id))
        connection.commit()

        return jsonify({"message": "Complaint rejected successfully"}), 200

    except Exception as e:
        logging.error(f"Database error: {e}")
        return jsonify({"error": str(e)}), 500

    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()
