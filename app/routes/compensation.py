import json
import datetime
from flask import Blueprint, request, jsonify
from app.models.database import create_connection
from app.utils.firebase import encode_firebase_path
import logging
from mysql.connector import Error
from app.utils.tokenCheck import token_required


from app.utils.form_text import build_canonical_form_text
from app.utils.embeddings import embed_text
from app.utils.pinecone_store import ensure_index, fetch_vector, upsert_form_vector,query_similar
from app.utils.simalirtyScores import compute_final_score

compensation_bp = Blueprint('compensation', __name__)

@compensation_bp.route('', methods=['POST'])
@token_required
def insert_compensation_form(decoded_data):
    data = request.json

    # Validate that forestGuardID exists in the request body
    forestGuardID = data.get('forestGuardID')
    if not forestGuardID:
        return jsonify({"error": "Missing forestGuardID"}), 400

    # Compare JWT emp_id with forestGuardID from request
    if str(decoded_data.get("emp_id")) != str(forestGuardID):
        return jsonify({"error": "Unauthorized access"}), 403

    connection = create_connection()
    if not connection:
        return jsonify({"error": "Failed to connect to database"}), 500

    try:
        # Encode Firebase URLs
        encoded_document_url = data.get('idProof')
        encoded_photo_url = data.get('photoUrl')
        encoded_e_sign_url = data.get('eSignUrl')
        encoded_cropdamagePhoto = data.get('cropdamagePhoto')
        encoded_nocReport = data.get('nocReport')
        encoded_landOwnershipReport = data.get('landOwnershipReport')
        encoded_rorReport = data.get('rorReport')
        encoded_housedamagePhoto1 = data.get('housedamagePhoto1')
        encoded_housedamagePhoto2 = data.get('housedamagePhoto2')
        encoded_propertyOwnerReport = data.get('propertyOwnerReport')
        encoded_cattlePhoto = data.get('cattlePhoto')
        encoded_vasCertificate = data.get('vasCertificate')
        encoded_humanPhoto1 = data.get('humanPhoto1')
        encoded_humanPhoto2 = data.get('humanPhoto2')
        encoded_deathCertificate = data.get('deathCertificate')
        encoded_sarpanchReport = data.get('sarpanchReport')
        encoded_pmReport = data.get('pmReport')
        encoded_humanInjuryPhoto = data.get('humanInjuryPhoto')
        encoded_medicalCertificate = data.get('medicalCertificate')
        status_history = [{
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
            "status": "2",
            "comment": "Submitted by Forest Guard",
            "updatedBy": data['forestGuardID']
        }]
        status_history_json = json.dumps(status_history)

        status = "2"  # force in backend

        # status_history_json = json.dumps(status_history)

        # status = "2"  # force in backend


        # status_history = data.get('statusHistory', [])
        # status_history_json = json.dumps(status_history)

        complaint_id = data.get('complaint_id')
        cursor = connection.cursor(dictionary=True)

        if complaint_id:
            query = """
            INSERT INTO compensationform (
                ForestGuardID, complaint_id,ApplicantName, Age, FatherSpouseName, Mobile, email, AnimalName, 
                IncidentDate, AdditionalDetails, Circle_CG, Circle1, division, subdivision, range_, beat, Address, 
                CropType, CerealCrop, CropDamageArea, cropDamageAmount, cropdamagePhoto, nocReport, 
                landOwnershipReport, rorReport, FullHouseDamage, PartialHouseDamage, houseDamageAmount, 
                housedamagePhoto1, housedamagePhoto2, propertyOwnerReport, NumberOfCattlesDied, EstimatedCattleAge, 
                catleInjuryAmount, cattlePhoto, vasCertificate, HumanDeathVictimName, NumberOfDeaths, 
                TemporaryInjuryDetails, PermanentInjuryDetails, humanDeathAmount, humanPhoto1, humanPhoto2, 
                deathCertificate, sarpanchReport, pmReport, humanInjuryAmount, humanInjuryPhoto, medicalCertificate, 
                BankName, IFSCCode, BranchName, AccountHolderName, AccountNumber, PANNumber, AadhaarNumber, 
                totalCompensationAmount, statusHistory, Status, IdProof, photoUrl, eSignUrl, VerifiedBy, 
                PaymentProcessedBy, comments,lat,longitude
            ) VALUES (%s, %s, %s,%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 
                      %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 
                      %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,%s,%s)
            """

            cursor.execute(query, (
                data['forestGuardID'], data['complaint_id'],data['applicantName'], data['age'],
                data['fatherSpouseName'], data['mobile'], data['email'], data['animalName'], data['incidentDate'],
                data['additionalDetails'], data['circle_CG'], data['circle1'], data['division'], data['subdivision'],
                data['range_'], data['beat'], data['address'], data['cropType'], data['cerealCrop'], data['cropDamageArea'],
                data['cropDamageAmount'], encoded_cropdamagePhoto, encoded_nocReport, encoded_landOwnershipReport,
                encoded_rorReport, data['fullHouseDamage'], data['partialHouseDamage'], data['houseDamageAmount'],
                encoded_housedamagePhoto1, encoded_housedamagePhoto2, encoded_propertyOwnerReport,
                data['numberOfCattlesDied'], data['estimatedCattleAge'], data['catleInjuryAmount'], encoded_cattlePhoto,
                encoded_vasCertificate, data['humanDeathVictimName'], data['numberOfDeaths'], data['temporaryInjuryDetails'],
                data['permanentInjuryDetails'], data['humanDeathAmount'], encoded_humanPhoto1, encoded_humanPhoto2,
                encoded_deathCertificate, encoded_sarpanchReport, encoded_pmReport, data['humanInjuryAmount'],
                encoded_humanInjuryPhoto, encoded_medicalCertificate, data['bankName'], data['ifscCode'],
                data['branchName'], data['accountHolderName'], data['accountNumber'], data['panNumber'],
                data['aadhaarNumber'], data['totalCompensationAmount'], status_history_json, status,
                encoded_document_url, encoded_photo_url, encoded_e_sign_url, str(forestGuardID),
                "", data['comments'],data['lat'],data['long']
            ))


            # Update complaint status history
            query = "SELECT statusHistory FROM complaints WHERE complaint_id = %s"
            cursor.execute(query, (complaint_id,))
            complaint_info = cursor.fetchone()

            complaint_status_history = []
            if complaint_info and complaint_info['statusHistory']:
                try:
                    complaint_status_history = json.loads(complaint_info['statusHistory'])
                except json.JSONDecodeError:
                    pass

            current_timestamp = datetime.datetime.utcnow().isoformat() + "Z"
            complaint_status_entry = {
                "status": "2",
                "comment": "Approved by Guard",
                "timestamp": current_timestamp,
                "updatedBy": data['forestGuardID']
            }
            complaint_status_history.append(complaint_status_entry)
            updated_complaint_status_history_json = json.dumps(complaint_status_history)

            update_complaint_query = """
            UPDATE complaints
            SET status = %s, statusHistory = %s
            WHERE complaint_id = %s
            """
            cursor.execute(update_complaint_query, ("2", updated_complaint_status_history_json, complaint_id))
        else:
            query = """
            INSERT INTO compensationform (
                ForestGuardID, ApplicantName, Age, FatherSpouseName, Mobile, email, AnimalName, 
                IncidentDate, AdditionalDetails, Circle_CG, Circle1, division, subdivision, range_, beat, Address, 
                CropType, CerealCrop, CropDamageArea, cropDamageAmount, cropdamagePhoto, nocReport, 
                landOwnershipReport, rorReport, FullHouseDamage, PartialHouseDamage, houseDamageAmount, 
                housedamagePhoto1, housedamagePhoto2, propertyOwnerReport, NumberOfCattlesDied, EstimatedCattleAge, 
                catleInjuryAmount, cattlePhoto, vasCertificate, HumanDeathVictimName, NumberOfDeaths, 
                TemporaryInjuryDetails, PermanentInjuryDetails, humanDeathAmount, humanPhoto1, humanPhoto2, 
                deathCertificate, sarpanchReport, pmReport, humanInjuryAmount, humanInjuryPhoto, medicalCertificate, 
                BankName, IFSCCode, BranchName, AccountHolderName, AccountNumber, PANNumber, AadhaarNumber, 
                totalCompensationAmount, statusHistory, Status, IdProof, photoUrl, eSignUrl, VerifiedBy, 
                PaymentProcessedBy, comments,lat,longitude
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 
                      %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 
                      %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,%s,%s)
            """

            cursor.execute(query, (
                data['forestGuardID'], data['applicantName'], data['age'],
                data['fatherSpouseName'], data['mobile'], data['email'], data['animalName'], data['incidentDate'],
                data['additionalDetails'], data['circle_CG'], data['circle1'], data['division'], data['subdivision'],
                data['range_'], data['beat'], data['address'], data['cropType'], data['cerealCrop'], data['cropDamageArea'],
                data['cropDamageAmount'], encoded_cropdamagePhoto, encoded_nocReport, encoded_landOwnershipReport,
                encoded_rorReport, data['fullHouseDamage'], data['partialHouseDamage'], data['houseDamageAmount'],
                encoded_housedamagePhoto1, encoded_housedamagePhoto2, encoded_propertyOwnerReport,
                data['numberOfCattlesDied'], data['estimatedCattleAge'], data['catleInjuryAmount'], encoded_cattlePhoto,
                encoded_vasCertificate, data['humanDeathVictimName'], data['numberOfDeaths'], data['temporaryInjuryDetails'],
                data['permanentInjuryDetails'], data['humanDeathAmount'], encoded_humanPhoto1, encoded_humanPhoto2,
                encoded_deathCertificate, encoded_sarpanchReport, encoded_pmReport, data['humanInjuryAmount'],
                encoded_humanInjuryPhoto, encoded_medicalCertificate, data['bankName'], data['ifscCode'],
                data['branchName'], data['accountHolderName'], data['accountNumber'], data['panNumber'],
                data['aadhaarNumber'], data['totalCompensationAmount'], status_history_json,status,
                encoded_document_url, encoded_photo_url, encoded_e_sign_url, str(forestGuardID),
                "", data['comments'],data['lat'],data['long']
            ))

        # --- commit the insert first ---
        connection.commit()

        # --- reliably obtain inserted FormID ---
        new_form_id = None
        try:
            new_form_id = cursor.lastrowid or None
        except Exception:
            new_form_id = None

        if not new_form_id:
            # fallback to LAST_INSERT_ID() in case driver didn't populate lastrowid
            try:
                tmp_cursor = connection.cursor(dictionary=True)
                tmp_cursor.execute("SELECT LAST_INSERT_ID() AS id")
                row = tmp_cursor.fetchone()
                tmp_cursor.close()
                new_form_id = row.get("id") if row else None
            except Exception as e:
                logging.exception("Failed to fetch LAST_INSERT_ID(): %s", e)
                return jsonify({"error": "Failed to determine inserted form id"}), 500

        if not new_form_id:
            logging.error("insert_compensation_form: could not determine new FormID after insert")
            return jsonify({"error": "Could not determine new FormID after insert"}), 500

        # --- fetch the newly inserted row and validate ---
        cursor2 = connection.cursor(dictionary=True)
        cursor2.execute("SELECT * FROM compensationform WHERE FormID = %s", (new_form_id,))
        new_form = cursor2.fetchone()
        cursor2.close()

        if not new_form:
            logging.error("insert_compensation_form: inserted form not found for FormID=%s", new_form_id)
            return jsonify({"error": f"Inserted form (FormID={new_form_id}) not found"}), 500

        # --- build canonical text and embedding from the DB row ---
        try:
            text = build_canonical_form_text(new_form)
            vector = embed_text(text)
        except Exception as e:
            logging.exception("Embedding creation failed for FormID=%s : %s", new_form_id, e)
            # continue (we still succeeded inserting into DB), but return success with warning
            return jsonify({
                "message": "Compensation form submitted successfully (but embedding failed)",
                "formID": new_form_id,
                "embedding_error": str(e)
            }), 201

        metadata = {
            "formID": str(new_form["FormID"]),

            "SubmissionDateTime": str(new_form.get("SubmissionDateTime")),
            "ApplicantName": new_form.get("ApplicantName"),
            "FatherSpouseName": new_form.get("FatherSpouseName"),

            "IncidentDate": new_form.get("IncidentDate"),   # keep exact DB key

            "lat": float(new_form.get("lat")) if new_form.get("lat") else None,
            "longitude": float(new_form.get("longitude")) if new_form.get("longitude") else None,

            "Mobile": new_form.get("Mobile"),
            "IFSCCode": new_form.get("IFSCCode"),
            "AadhaarNumber": new_form.get("AadhaarNumber"),
            "AccountNumber": new_form.get("AccountNumber"),
        }


        # ---- UPSERT INTO PINECONE ----
        try:
            upsert_form_vector(new_form["FormID"], vector, metadata)
        except Exception as e:
            logging.exception("Pinecone upsert failed for FormID=%s : %s", new_form_id, e)
            # respond success for DB insert but warn about vector upsert
            return jsonify({
                "message": "Compensation form submitted successfully (DB OK, Pinecone upsert failed)",
                "formID": new_form_id,
                "pinecone_error": str(e)
            }), 201

        return jsonify({"message": "Compensation form submitted successfully", "formID": new_form_id}), 201

    except Error as e:
        logging.error(f"Database error: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

@compensation_bp.route('/<string:forest_guard_id>', methods=['GET'])
@token_required
def get_compensation_forms(decoded_data, forest_guard_id):
    # Check if JWT emp_id matches the forest_guard_id from URL
    if str(decoded_data.get("emp_id")) != str(forest_guard_id):
        return jsonify({"error": "Unauthorized access"}), 403

    connection = create_connection()
    if not connection:
        return jsonify({"error": "Failed to connect to database"}), 500

    try:
        cursor = connection.cursor(dictionary=True)
        query = """
        SELECT * FROM compensationform
        WHERE ForestGuardID = %s
        """
        cursor.execute(query, (forest_guard_id,))
        compensation_forms = cursor.fetchall()

        if not compensation_forms:
            return jsonify({"message": "No compensation forms found for this ForestGuardID"}), 404

        # Convert each form into a dictionary and parse JSON fields
        result = []
        for form in compensation_forms:
            try:
                status_history = json.loads(form["statusHistory"]) if form["statusHistory"] else []
            except json.JSONDecodeError:
                status_history = []

            form_data = {
                "formID": form["FormID"],
                "submissionDateTime":form["SubmissionDateTime"],

                "forestGuardID": form["ForestGuardID"],
                "complaint_id": form["complaint_id"],
                "applicantName": form["ApplicantName"],
                # "age": form["Age"],
                # "fatherSpouseName": form["FatherSpouseName"],
                "mobile": form["Mobile"],
                # "email": form["email"],
                "animalName": form["AnimalName"],
                "incidentDate": form["IncidentDate"],
                # "additionalDetails": form["AdditionalDetails"],
                "circle_CG": form["Circle_CG"],
                "circle1": form["Circle1"],
                "division": form["division"],
                "subdivision": form["subdivision"],
                "range_": form["range_"],
                "beat": form["beat"],
                # "address": form["Address"],
                # "cropType": form["CropType"],
                # "cerealCrop": form["CerealCrop"],
                # "cropDamageAmount": form["cropDamageAmount"],
                # "cropDamageArea": form["CropDamageArea"],
                # "cropdamagePhoto": form["cropdamagePhoto"],
                # "nocReport": form["nocReport"],
                # "landOwnershipReport": form["landOwnershipReport"],
                # "rorReport": form["rorReport"],
                # "fullHouseDamage": form["FullHouseDamage"],
                # "partialHouseDamage": form["PartialHouseDamage"],
                # "houseDamageAmount": form["houseDamageAmount"],
                # "housedamagePhoto1": form["housedamagePhoto1"],
                # "housedamagePhoto2": form["housedamagePhoto2"],
                # "propertyOwnerReport": form["propertyOwnerReport"],
                # "numberOfCattlesDied": form["NumberOfCattlesDied"],
                # "estimatedCattleAge": form["EstimatedCattleAge"],
                # "catleInjuryAmount": form["catleInjuryAmount"],
                # "cattlePhoto": form["cattlePhoto"],
                # "vasCertificate": form["vasCertificate"],
                # "humanDeathVictimName": form["HumanDeathVictimName"],
                # "numberOfDeaths": form["NumberOfDeaths"],
                # "temporaryInjuryDetails": form["TemporaryInjuryDetails"],
                # "permanentInjuryDetails": form["PermanentInjuryDetails"],
                # "humanDeathAmount": form["humanDeathAmount"],
                # "humanPhoto1": form["humanPhoto1"],
                # "humanPhoto2": form["humanPhoto2"],
                # "deathCertificate": form["deathCertificate"],
                # "sarpanchReport": form["sarpanchReport"],
                # "pmReport": form["pmReport"],
                # "humanInjuryAmount": form["humanInjuryAmount"],
                # "humanInjuryPhoto": form["humanInjuryPhoto"],
                # "medicalCertificate": form["medicalCertificate"],
                # "bankName": form["BankName"],
                # "ifscCode": form["IFSCCode"],
                # "branchName": form["BranchName"],
                # "accountHolderName": form["AccountHolderName"],
                # "accountNumber": form["AccountNumber"],
                # "panNumber": form["PANNumber"],
                # "aadhaarNumber": form["AadhaarNumber"],
                "totalCompensationAmount": form["totalCompensationAmount"],
                "statusHistory": status_history,
                "lat":form["lat"],
                "long":form["longitude"],
                # "status": form["Status"],
                # "idProof": form["IdProof"],
                # "photoUrl": form["photoUrl"],
                # "eSignUrl": form["eSignUrl"],
                # "verifiedBy": form["VerifiedBy"],
                # "paymentProcessedBy": form["PaymentProcessedBy"],
                # "comments": form["comments"]
            }
            result.append(form_data)

        return jsonify(result), 200
    except Error as e:
        logging.error(f"Database error: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

@compensation_bp.route('/<string:role>/<string:emp_id>', methods=['GET'])
@token_required
def get_compensation_forms_by_role(decoded_data, role, emp_id):
    # JWT authorization check: decoded emp_id must match the emp_id from URL
    if str(decoded_data.get("emp_id")) != str(emp_id):
        return jsonify({"error": "Unauthorized access"}), 403

    connection = create_connection()
    if not connection:
        return jsonify({"error": "Failed to connect to database"}), 500

    try:
        cursor = connection.cursor(dictionary=True)

        # Step 1: Get employee details from the 'emp' table
        emp_query = """
        SELECT Circle_CG, Circle1, division, subdivision, range_, beat
        FROM emp 
        WHERE emp_id = %s AND roll = %s
        """
        cursor.execute(emp_query, (emp_id, role))
        emp_data = cursor.fetchone()

        if not emp_data:
            return jsonify({"message": "Employee not found"}), 404

        # Extract values from emp_data
        circle_cg = emp_data["Circle_CG"]
        circle1 = emp_data["Circle1"]
        division = emp_data["division"]
        subdivision = emp_data["subdivision"]
        range_ = emp_data["range_"]
        beat = emp_data["beat"]

        # Step 2: Dynamically build the query based on role
        query = "SELECT * FROM compensationform WHERE Circle_CG = %s"
        query_params = [circle_cg]

        if role.lower() == "ccf" or role.lower() == "ccf":
            pass  # No additional filtering, only Circle_CG is needed
        elif role.lower() == "dfo":
            query += " AND division = %s"
            query_params.append(division)
        elif role.lower() == "sdo":
            query += " AND subdivision = %s AND division = %s"
            query_params.extend([subdivision, division])
        elif role.lower() == "ranger":
            query += " AND range_ = %s AND division = %s"
            query_params.extend([range_, division])
        elif role.lower() == "deputyranger":
            query += " AND range_ = %s AND division = %s AND Circle1 = %s"
            query_params.extend([range_, division, circle1])
        elif role.lower() == "forestguard":
            query += " AND range_ = %s AND division = %s AND Circle1 = %s AND beat = %s"
            query_params.extend([range_, division, circle1, beat])
        else:
            return jsonify({"error": "Invalid role"}), 400

        # Step 3: Execute query and fetch compensation forms
        cursor.execute(query, tuple(query_params))
        compensation_forms = cursor.fetchall()

        if not compensation_forms:
            return jsonify({"message": "No matching compensation forms found"}), 404

        # Step 4: Convert result to JSON and parse statusHistory
        result = []
        for form in compensation_forms:
            # Parse statusHistory JSON string into a Python list
            try:
                status_history = json.loads(form["statusHistory"]) if form["statusHistory"] else []
            except json.JSONDecodeError:
                status_history = []

            form_data = {
                "formID": form["FormID"],
                "submissionDateTime":form["SubmissionDateTime"],
                "forestGuardID": form["ForestGuardID"],
                "complaint_id": form["complaint_id"],
                "applicantName": form["ApplicantName"],
                # "age": form["Age"],
                # "fatherSpouseName": form["FatherSpouseName"],
                "mobile": form["Mobile"],
                #"email": form["email"],
                "animalName": form["AnimalName"],
                "incidentDate": form["IncidentDate"],
                # "additionalDetails": form["AdditionalDetails"],
                "circle_CG": form["Circle_CG"],
                "circle1": form["Circle1"],
                "division": form["division"],
                "subdivision": form["subdivision"],
                "range_": form["range_"],
                "beat": form["beat"],
                "lat":form["lat"],
                "long":form["longitude"],
                # "address": form["Address"],
                # "cropType": form["CropType"],
                # "cerealCrop": form["CerealCrop"],
                # "cropDamageAmount": form["cropDamageAmount"],
                # "cropDamageArea": form["CropDamageArea"],
                # "cropdamagePhoto": form["cropdamagePhoto"],
                # "nocReport": form["nocReport"],
                # "landOwnershipReport": form["landOwnershipReport"],
                # "rorReport": form["rorReport"],
                # "fullHouseDamage": form["FullHouseDamage"],
                # "partialHouseDamage": form["PartialHouseDamage"],
                # "houseDamageAmount": form["houseDamageAmount"],
                # "housedamagePhoto1": form["housedamagePhoto1"],
                # "housedamagePhoto2": form["housedamagePhoto2"],
                # "propertyOwnerReport": form["propertyOwnerReport"],
                # "numberOfCattlesDied": form["NumberOfCattlesDied"],
                # "estimatedCattleAge": form["EstimatedCattleAge"],
                # "catleInjuryAmount": form["catleInjuryAmount"],
                # "cattlePhoto": form["cattlePhoto"],
                # "vasCertificate": form["vasCertificate"],
                # "humanDeathVictimName": form["HumanDeathVictimName"],
                # "numberOfDeaths": form["NumberOfDeaths"],
                # "temporaryInjuryDetails": form["TemporaryInjuryDetails"],
                # "permanentInjuryDetails": form["PermanentInjuryDetails"],
                # "humanDeathAmount": form["humanDeathAmount"],
                # "humanPhoto1": form["humanPhoto1"],
                # "humanPhoto2": form["humanPhoto2"],
                # "deathCertificate": form["deathCertificate"],
                # "sarpanchReport": form["sarpanchReport"],
                # "pmReport": form["pmReport"],
                # "humanInjuryAmount": form["humanInjuryAmount"],
                # "humanInjuryPhoto": form["humanInjuryPhoto"],
                # "medicalCertificate": form["medicalCertificate"],
                # "bankName": form["BankName"],
                # "ifscCode": form["IFSCCode"],
                # "branchName": form["BranchName"],
                # "accountHolderName": form["AccountHolderName"],
                # "accountNumber": form["AccountNumber"],
                # "panNumber": form["PANNumber"],
                # "aadhaarNumber": form["AadhaarNumber"],
                "totalCompensationAmount": form["totalCompensationAmount"],
                "statusHistory": status_history,
                "status": form["Status"],
                # "idProof": form["IdProof"],
                # "photoUrl": form["photoUrl"],
                # "eSignUrl": form["eSignUrl"],
                # "verifiedBy": form["VerifiedBy"],
                # "paymentProcessedBy": form["PaymentProcessedBy"],
                # "comments": form["comments"]
            }
            result.append(form_data)

        return jsonify(result), 200

    except Error as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

@compensation_bp.route('/one/<string:form_id>', methods=['GET'])
@token_required
def get_compensation_form(decoded_data,form_id):
    # Check if JWT emp_id matches the forest_guard_id from URL
    connection = create_connection()
    if not connection:
        return jsonify({"error": "Failed to connect to database"}), 500

    try:
        cursor = connection.cursor(dictionary=True)
        query = "SELECT * FROM compensationform WHERE FormID = %s"
        cursor.execute(query, (form_id,))
        form = cursor.fetchone()

        if not form:
            return jsonify({"message": "Compensation form not found"}), 404

        try:
            status_history = json.loads(form["statusHistory"]) if form["statusHistory"] else []
        except json.JSONDecodeError:
            status_history = []

        form_data = {
            "formID": form["FormID"],
            "submissionDateTime":form["SubmissionDateTime"],

            "forestGuardID": form["ForestGuardID"],
            "complaint_id": form["complaint_id"],
            "applicantName": form["ApplicantName"],
            "age": form["Age"],
            "fatherSpouseName": form["FatherSpouseName"],
            "mobile": form["Mobile"],
            "email": form["email"],
            "animalName": form["AnimalName"],
            "incidentDate": form["IncidentDate"],
            "additionalDetails": form["AdditionalDetails"],
            "circle_CG": form["Circle_CG"],
            "circle1": form["Circle1"],
            "division": form["division"],
            "subdivision": form["subdivision"],
            "range_": form["range_"],
            "beat": form["beat"],
            "address": form["Address"],
            "cropType": form["CropType"],
            "cerealCrop": form["CerealCrop"],
            "cropDamageAmount": form["cropDamageAmount"],
            "cropDamageArea": form["CropDamageArea"],
            "cropdamagePhoto": form["cropdamagePhoto"],
            "nocReport": form["nocReport"],
            "landOwnershipReport": form["landOwnershipReport"],
            "rorReport": form["rorReport"],
            "fullHouseDamage": form["FullHouseDamage"],
            "partialHouseDamage": form["PartialHouseDamage"],
            "houseDamageAmount": form["houseDamageAmount"],
            "housedamagePhoto1": form["housedamagePhoto1"],
            "housedamagePhoto2": form["housedamagePhoto2"],
            "propertyOwnerReport": form["propertyOwnerReport"],
            "numberOfCattlesDied": form["NumberOfCattlesDied"],
            "estimatedCattleAge": form["EstimatedCattleAge"],
            "catleInjuryAmount": form["catleInjuryAmount"],
            "cattlePhoto": form["cattlePhoto"],
            "vasCertificate": form["vasCertificate"],
            "humanDeathVictimName": form["HumanDeathVictimName"],
            "numberOfDeaths": form["NumberOfDeaths"],
            "temporaryInjuryDetails": form["TemporaryInjuryDetails"],
            "permanentInjuryDetails": form["PermanentInjuryDetails"],
            "humanDeathAmount": form["humanDeathAmount"],
            "humanPhoto1": form["humanPhoto1"],
            "humanPhoto2": form["humanPhoto2"],
            "deathCertificate": form["deathCertificate"],
            "sarpanchReport": form["sarpanchReport"],
            "pmReport": form["pmReport"],
            "humanInjuryAmount": form["humanInjuryAmount"],
            "humanInjuryPhoto": form["humanInjuryPhoto"],
            "medicalCertificate": form["medicalCertificate"],
            "bankName": form["BankName"],
            "ifscCode": form["IFSCCode"],
            "branchName": form["BranchName"],
            "accountHolderName": form["AccountHolderName"],
            "accountNumber": form["AccountNumber"],
            "panNumber": form["PANNumber"],
            "aadhaarNumber": form["AadhaarNumber"],
            "totalCompensationAmount": form["totalCompensationAmount"],
            "statusHistory": status_history,
            "status": form["Status"],
            "idProof": form["IdProof"],
            "photoUrl": form["photoUrl"],
            "eSignUrl": form["eSignUrl"],
            "verifiedBy": form["VerifiedBy"],
            "paymentProcessedBy": form["PaymentProcessedBy"],
            "comments": form["comments"],
            "lat":form["lat"],
            "long":form["longitude"]
        }

        return jsonify(form_data), 200

    except Error as e:
        logging.error(f"Database error: {e}")
        return jsonify({"error": str(e)}), 500

    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

@compensation_bp.route('/similar/<string:form_id>/<int:top_k>', methods=['GET'])
@token_required
def get_similar_compensation_forms(decoded_data, form_id, top_k):
    try:
        # Fetch embedding vector of the query form
        vector = fetch_vector(form_id)
        if not vector:
            return jsonify({"error": "Embedding not found for this form"}), 404

        # Fetch metadata of query form directly from Pinecone
        try:
            idx = ensure_index(len(vector))
            fetch_res = idx.fetch([str(form_id)])
            query_meta = fetch_res["vectors"][str(form_id)]["metadata"]
        except Exception as e:
            logging.error(f"Failed to fetch query form metadata: {e}")
            return jsonify({"error": "Failed to load form metadata"}), 500

        # Stage 1: vector similarity
        matches = query_similar(vector, top_k=top_k)

        # Remove self
        matches = [m for m in matches if m["formID"] != str(form_id)]

        scored_results = []

        # Stage 2: compute final combined score
        for m in matches:
            match_meta = m.get("metadata", {})
            rag_score = m.get("score", 0)

            try:
                final_score, top_field, contribs = compute_final_score(query_meta, match_meta, rag_score)
            except Exception as e:
                logging.error(f"Failed to compute score for form {m['formID']}: {e}")
                final_score = 0.0

            scored_results.append({
                "formID": m["formID"],
                "metadata":m["metadata"],
                "score": final_score,
                "top_field":top_field,
                "contibs":contribs
            })

        return jsonify({
            "formID": str(form_id),
            "similar_forms": scored_results
        }), 200

    except Exception as e:
        logging.exception("Unexpected error in similarity API")
        return jsonify({"error": "Internal server error", "details": str(e)}), 500
