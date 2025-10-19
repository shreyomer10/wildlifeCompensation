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

# Set up basic logging
logging.basicConfig(
    level=logging.DEBUG,  # Change to DEBUG to capture debug messages
    format="%(asctime)s - %(levelname)s - %(message)s"
)

app = Flask(__name__)

# limiter = Limiter(
#     get_remote_address,  # uses IP address
#     app=app,
#     default_limits=["200 per day", "50 per hour"]  # example limits
# )
limiter.init_app(app)



app.config.from_object(Config)
CORS(app, supports_credentials=True, origins=[
    "http://localhost:5173",
    "https://anugraha-nine.vercel.app",
    "https://5173-idx-anugraha-1744834663194.cluster-ancjwrkgr5dvux4qug5rbzyc2y.cloudworkstations.dev"
])

#CORS(app, supports_credentials=True, origins=["*"])


# Enable Flask's own debugging logs
app.logger.setLevel(logging.DEBUG)

# DATABASE_CONFIG = {
#     'host': os.getenv('DB_HOST'),
#     'user': os.getenv('DB_USER'),
#     'password': os.getenv('DB_PASSWORD'),
#     'database': os.getenv('DB_NAME'),
#     'port': os.getenv('DB_PORT'),
#     'FirebaseKey':os.getenv('GOOGLE_APPLICATION_CREDENTIALS_JSON')
# }
# resend.api_key = os.getenv("RESEND_API_KEY")


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

# @app.route('/register', methods=['POST'])
# def register():
#     data = request.json
#     emp_id = data.get('emp_id')
#     mobile_number = data.get('mobile_number')
#     roll = data.get('roll')
#     password = data.get('password')

#     if not emp_id or not mobile_number or not roll or not password:
#         return jsonify({"error": "Missing emp_id, mobile_number, roll, or password"}), 400

#     hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

#     connection = create_connection()
#     if not connection:
#         return jsonify({"error": "Database connection failed"}), 500

#     try:
#         cursor = connection.cursor(dictionary=True)

#         # Check if employee exists with matching emp_id, mobile_number, and roll
#         query = "SELECT emp_id FROM emp WHERE emp_id = %s AND mobile_number = %s AND roll = %s"
#         cursor.execute(query, (emp_id, mobile_number, roll))
#         emp = cursor.fetchone()

#         if emp:
#             # Update password if employee exists
#             update_query = "UPDATE emp SET password = %s WHERE emp_id = %s"
#             cursor.execute(update_query, (hashed_password, emp_id))
#             connection.commit()
#             return jsonify({"message": "Password updated successfully"}), 200
#         else:
#             return jsonify({"error": "Employee not found or details do not match"}), 404

#     except Error as e:
#         return jsonify({"error": str(e)}), 500
#     finally:
#         cursor.close()
#         connection.close()



# @app.route('/send_email', methods=['POST'])
# def send_email():
#     try:
#         data = request.json
#         email = data.get("email")
#         message = data.get("message")

#         if not email or not message:
#             return jsonify({"error": "Email and message are required"}), 400

#         response = resend.Emails.send({
#             "from": "onboarding@resend.dev",  # Change this if using a custom domain
#             "to": email,
#             "subject": "Regarding Compensation form",
#             "html": f"<p>{message}</p>"
#         })

#         return jsonify({"success": True, "response": response}), 200

#     except Exception as e:
#         return jsonify({"error": str(e)}), 500
# def create_connection():
#     try:
#         connection = mysql.connector.connect(**DATABASE_CONFIG)
#         if connection.is_connected():
#             print("Connected to the database")
#         return connection
#     except Error as e:
#         print(f"Error connecting to MySQL: {e}")
#         return None

# # Routes

# @app.route('/guards', methods=['GET'])
# def get_guards():
#     connection = create_connection()
#     if not connection:
#         return jsonify({"error": "Failed to connect to database"}), 500
#     try:
#         cursor = connection.cursor(dictionary=True)
#         cursor.execute("SELECT * FROM emp")
#         result = cursor.fetchall()
#         return jsonify(result)
#     except Error as e:
#         return jsonify({"error": str(e)}), 500
#     finally:
#         if connection.is_connected():
#             cursor.close()
#             connection.close()
            
# @app.route('/aguards', methods=['POST'])
# def add_guard():
#     data = request.json
#     connection = create_connection()
#     if not connection:
#         return jsonify({"error": "Failed to connect to database"}), 500
#     try:
#         cursor = connection.cursor()
#         query = """
#         INSERT INTO emp (emp_id, name, mobile_number, division, range_, beat) 
#         VALUES (%s, %s, %s, %s, %s, %s)
#     """
#         cursor.execute(query, (
#             data['emp_id'], 
#             data['name'], 
#             data['mobile_number'], 
#             data['division'], 
#             data['range_'], 
#             data['beat']
#         ))
#         connection.commit()
#         return jsonify({"message": "Guard added successfully"}), 201
#     except Error as e:
#         return jsonify({"error": str(e)}), 500
#     finally:
#         if connection.is_connected():
#             cursor.close()
#             connection.close()
            

# def encode_firebase_path(url):
#     if not url:
#         return None  # Handle None URLs gracefully

#     try:
#         base, path_query = url.split("/o/", 1)  # Split at "/o/"
#         if "?" in path_query:  
#             path, query = path_query.split("?", 1)  # Separate path from query parameters
#         else:
#             path, query = path_query, ""

#         decoded_path = urllib.parse.unquote(path)  # 🔥 Decode first to remove any existing encoding
#         encoded_path = urllib.parse.quote(decoded_path, safe="/")  # ✅ Encode properly

#         return f"{base}/o/{encoded_path}?{query}" if query else f"{base}/o/{encoded_path}"

#     except Exception as e:
#         print(f"Error encoding URL: {e}")
#         return url

# @app.route('/verify_guard', methods=['POST'])
# def verify_guard():
#     data = request.json
#     connection = create_connection()
#     if not connection:
#         return jsonify({"error": "Failed to connect to database"}), 500
#     try:
#         cursor = connection.cursor(dictionary=True)
#         query = "SELECT * FROM emp WHERE emp_id = %s AND mobile_number = %s AND roll =%s"
#         cursor.execute(query, (data['emp_id'], data['mobile_number'],data['roll']))
#         result = cursor.fetchone()
#         if result:
#             return jsonify({"message": "Verified", "employee": result}), 200
#         else:
#             return jsonify({"message": "Employee not found"}), 404
#     except Error as e:
#         return jsonify({"error": str(e)}), 500
#     finally:
#         if connection.is_connected():
#             cursor.close()
#             connection.close()

# @app.route('/compensationform', methods=['POST'])
# def insert_compensation_form():
#     data = request.json
#     connection = create_connection()
#     if not connection:
#         return jsonify({"error": "Failed to connect to database"}), 500

#     try:
#         document_url = data.get('documentURL')
#         photo_url = data.get('photoUrl')
#         e_sign_url = data.get('eSignUrl')
#         incident_url_1 = data.get('incidentUrl1')
#         incident_url_2 = data.get('incidentUrl2')
#         incident_url_3 = data.get('incidentUrl3')

#         logging.debug(f"Document URL: {document_url}")

#         if not document_url:
#             return jsonify({"error": "Document URL is missing"}), 400

#         # Ensure the URLs are encoded before storing in MySQL
#         # Ensure only the Firebase path is encoded before storing in MySQL
#         # encoded_document_url = encode_firebase_path(document_url)
#         # encoded_photo_url = encode_firebase_path(photo_url)
#         # encoded_e_sign_url = encode_firebase_path(e_sign_url)
#         # encoded_incident_url_1 = encode_firebase_path(incident_url_1)
#         # encoded_incident_url_2 = encode_firebase_path(incident_url_2)
#         # encoded_incident_url_3 = encode_firebase_path(incident_url_3)
#         encoded_document_url = document_url
#         encoded_photo_url = photo_url
#         encoded_e_sign_url = e_sign_url
#         encoded_incident_url_1 = incident_url_1
#         encoded_incident_url_2 = incident_url_2
#         encoded_incident_url_3 = incident_url_3


#         status_history = data.get('statusHistory', [])
#         status_history_json = json.dumps(status_history)  # Convert list to JSON string

#         complaint_id = data.get('complaint_id')
#         cursor = connection.cursor(dictionary=True)
#         if complaint_id:
            
#             query = """
#             INSERT INTO compensationform (
#                 ForestGuardID,complaint_id, ApplicantName, Age, FatherSpouseName, Mobile, email,
#                 AnimalName, IncidentDate, AdditionalDetails, Circle_CG, Circle1, division, 
#                 subdivision, range_, beat, Address, CropType, CerealCrop, CropDamageArea, 
#                 cropDamageAmount, FullHouseDamage, PartialHouseDamage, houseDamageAmount, 
#                 NumberOfCattlesDied, EstimatedCattleAge, catleInjuryAmount, HumanDeathVictimName, 
#                 NumberOfDeaths, TemporaryInjuryDetails, PermanentInjuryDetails, humanDeathAmount, 
#                 humanInjuryAmount, BankName, IFSCCode, BranchName, AccountHolderName, AccountNumber, 
#                 PANNumber, AadhaarNumber, totalCompensationAmount, statusHistory, Status, 
#                 documentURL, photoUrl, eSignUrl, incidentUrl1, incidentUrl2, incidentUrl3, 
#                 VerifiedBy, PaymentProcessedBy, comments
#             ) VALUES (%s, %s,%s, %s, %s, %s, %s, %s,%s, %s, %s, %s, %s, %s, %s, %s, %s, 
#                     %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 
#                     %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,%s,%s,%s)
#             """

#             cursor.execute(query, (
#                 data['forestGuardID'], data['complaint_id'],data['applicantName'], data['age'], data['fatherSpouseName'],
#                 data['mobile'],data['email'], data['animalName'], data['incidentDate'], data['additionalDetails'],
#                 data['circle_CG'], data['circle1'], data['division'], data['subdivision'], data['range_'],
#                 data['beat'], data['address'], data['cropType'], data['cerealCrop'], data['cropDamageArea'],
#                 data['cropDamageAmount'], data['fullHouseDamage'], data['partialHouseDamage'], data['houseDamageAmount'],
#                 data['numberOfCattlesDied'], data['estimatedCattleAge'], data['catleInjuryAmount'], data['humanDeathVictimName'], 
#                 data['numberOfDeaths'], data['temporaryInjuryDetails'], data['permanentInjuryDetails'], data['humanDeathAmount'], 
#                 data['humanInjuryAmount'], data['bankName'], data['ifscCode'], data['branchName'], 
#                 data['accountHolderName'], data['accountNumber'], data['panNumber'], data['aadhaarNumber'], 
#                 data['totalCompensationAmount'], status_history_json, data['status'], encoded_document_url, 
#                 encoded_photo_url, encoded_e_sign_url, encoded_incident_url_1, encoded_incident_url_2, 
#                 encoded_incident_url_3, data['verifiedBy'], data['paymentProcessedBy'], data['comments']
#             ))
#             query = "SELECT statusHistory FROM complaints WHERE complaint_id = %s"
#             cursor.execute(query, (complaint_id,))
#             complaint_info = cursor.fetchone()

#             complaint_status_history = []
#             if complaint_info and complaint_info['statusHistory']:
#                 try:
#                     complaint_status_history = json.loads(complaint_info['statusHistory'])
#                 except json.JSONDecodeError:
#                     pass  # If parsing fails, continue with an empty list
#             current_timestamp = datetime.datetime.utcnow().isoformat() + "Z"

#             # Append new status update for complaint
#             complaint_status_entry = {
#                 "status": "2",
#                 "comment": "Approved by Guard",
#                 "timestamp": current_timestamp,
#                 "updatedBy": data['forestGuardID']
#             }
#             complaint_status_history.append(complaint_status_entry)

#             # Convert back to JSON
#             updated_complaint_status_history_json = json.dumps(complaint_status_history)

#             # Update the complaint status and history
#             update_complaint_query = """
#             UPDATE complaints
#             SET status = %s, statusHistory = %s
#             WHERE complaint_id = %s
#             """
#             cursor.execute(update_complaint_query, ("2", updated_complaint_status_history_json, complaint_id))






#         else:
#             query = """
#             INSERT INTO compensationform (
#                 ForestGuardID, ApplicantName, Age, FatherSpouseName, Mobile, email,
#                 AnimalName, IncidentDate, AdditionalDetails, Circle_CG, Circle1, division, 
#                 subdivision, range_, beat, Address, CropType, CerealCrop, CropDamageArea, 
#                 cropDamageAmount, FullHouseDamage, PartialHouseDamage, houseDamageAmount, 
#                 NumberOfCattlesDied, EstimatedCattleAge, catleInjuryAmount, HumanDeathVictimName, 
#                 NumberOfDeaths, TemporaryInjuryDetails, PermanentInjuryDetails, humanDeathAmount, 
#                 humanInjuryAmount, BankName, IFSCCode, BranchName, AccountHolderName, AccountNumber, 
#                 PANNumber, AadhaarNumber, totalCompensationAmount, statusHistory, Status, 
#                 documentURL, photoUrl, eSignUrl, incidentUrl1, incidentUrl2, incidentUrl3, 
#                 VerifiedBy, PaymentProcessedBy, comments
#             ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,%s, %s, %s, %s, %s, 
#                     %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 
#                     %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,%s,%s,%s)
#             """

#             cursor.execute(query, (
#                 data['forestGuardID'], data['applicantName'], data['age'], data['fatherSpouseName'],
#                 data['mobile'],data['email'], data['animalName'], data['incidentDate'], data['additionalDetails'],
#                 data['circle_CG'], data['circle1'], data['division'], data['subdivision'], data['range_'],
#                 data['beat'], data['address'], data['cropType'], data['cerealCrop'], data['cropDamageArea'],
#                 data['cropDamageAmount'], data['fullHouseDamage'], data['partialHouseDamage'], data['houseDamageAmount'],
#                 data['numberOfCattlesDied'], data['estimatedCattleAge'], data['catleInjuryAmount'], data['humanDeathVictimName'], 
#                 data['numberOfDeaths'], data['temporaryInjuryDetails'], data['permanentInjuryDetails'], data['humanDeathAmount'], 
#                 data['humanInjuryAmount'], data['bankName'], data['ifscCode'], data['branchName'], 
#                 data['accountHolderName'], data['accountNumber'], data['panNumber'], data['aadhaarNumber'], 
#                 data['totalCompensationAmount'], status_history_json, data['status'], encoded_document_url, 
#                 encoded_photo_url, encoded_e_sign_url, encoded_incident_url_1, encoded_incident_url_2, 
#                 encoded_incident_url_3, data['verifiedBy'], data['paymentProcessedBy'], data['comments']
#             ))



#         connection.commit()
#         return jsonify({"message": "Compensation form submitted successfully"}), 201
#     except Error as e:
#         logging.error(f"Database error: {e}")
#         return jsonify({"error": str(e)}), 500
#     finally:
#         if connection.is_connected():
#             cursor.close()
#             connection.close()


# @app.route('/submit_complaint', methods=['POST'])
# def submit_complaint():
#     data = request.json
#     connection = create_connection()
#     if not connection:
#         return jsonify({"error": "Failed to connect to database"}), 500

#     try:


        
#         status_history = data.get('statusHistory', [])
#         status_history_json = json.dumps(status_history)  # Convert list to JSON string

#         cursor = connection.cursor(dictionary=True)
#         query = """
#         INSERT INTO complaints (
#             name, age, fatherOrSpouseName, mobile,email, animalList, damageDate, additionalDetails,
#             address, division, subdivision, range_, circle1, beat, cropType, cerealCrop,
#             fullHousesDamaged, partialHousesDamaged, cattleInjuryNumber, cattleInjuryEstimatedAge,
#             humanDeathVictimNames, humanDeathNumber, temporaryInjuryDetails, permanentInjuryDetails,
#             photoUrl, eSignUrl, incidentUrl1, incidentUrl2, incidentUrl3,status,statusHistory
#         ) VALUES (%s, %s, %s,%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,%s,%s)
#         """

#         cursor.execute(query, (
#             data['name'], data['age'], data['fatherOrSpouseName'], data['mobile'], data['email'],data['animalList'],
#             data['damageDate'], data['additionalDetails'], data['address'], data['division'], data['subdivision'],
#             data['range_'], data['circle1'], data['beat'], data['cropType'], data['cerealCrop'],
#             data['fullHousesDamaged'], data['partialHousesDamaged'], data['cattleInjuryNumber'],
#             data['cattleInjuryEstimatedAge'], data['humanDeathVictimNames'], data['humanDeathNumber'],
#             data['temporaryInjuryDetails'], data['permanentInjuryDetails'], data['photoUrl'], data['eSignUrl'],
#             data['incidentUrl1'], data['incidentUrl2'], data['incidentUrl3'],data['status'],status_history_json
#         ))

#         # Get the last inserted complaint_id
#         complaint_id = cursor.lastrowid
#         connection.commit()

#         return jsonify({"message": "Complaint submitted successfully", "complaint_id": complaint_id}), 201

#     except Error as e:
#         logging.error(f"Database error: {e}")
#         return jsonify({"error": str(e)}), 500

#     finally:
#         if connection.is_connected():
#             cursor.close()
#             connection.close()

# @app.route('/get_complaint', methods=['POST'])
# def get_complaint():
#     data = request.json
#     complaint_id = data.get('complaint_id')
#     mobile = data.get('mobile')
    
#     if not complaint_id and not mobile:
#         return jsonify({"error": "Please provide complaint_id or mobile number"}), 400
    
#     connection = create_connection()
#     if not connection:
#         return jsonify({"error": "Failed to connect to database"}), 500
    
#     try:
#         cursor = connection.cursor(dictionary=True)
        
#         # Ensure filtering is done correctly
#         query = "SELECT * FROM complaints WHERE complaint_id = %s AND mobile = %s"
#         params = [complaint_id, mobile]
        
#         cursor.execute(query, tuple(params))
#         result = cursor.fetchone()
        
#         if not result:
#             return jsonify({"found": "no", "message": "No records found"}), 404  # Return 404 if not found
        
#         try:
#             status_history = json.loads(result["statusHistory"]) if result["statusHistory"] else []
#         except json.JSONDecodeError:
#             status_history = []
        
#         # Mapping to UserComplaintForm
#         complaint_data = {
#             "complaint_id": result["complaint_id"],
#             "SubmissionDateTime": result["SubmissionDateTime"],
#             "name": result["name"],
#             "age": result["age"],
#             "fatherOrSpouseName": result["fatherOrSpouseName"],
#             "mobile": result["mobile"],
#             "email":result["email"],
#             "animalList": result["animalList"],
#             "damageDate": result["damageDate"],
#             "additionalDetails": result["additionalDetails"],
#             "address": result["address"],
#             "division": result["division"],
#             "subdivision": result["subdivision"],
#             "range_": result["range_"],
#             "circle1": result["circle1"],
#             "beat": result["beat"],
#             "cropType": result["cropType"],
#             "cerealCrop": result["cerealCrop"],
#             "fullHousesDamaged": result["fullHousesDamaged"],
#             "partialHousesDamaged": result["partialHousesDamaged"],
#             "cattleInjuryNumber": result["cattleInjuryNumber"],
#             "cattleInjuryEstimatedAge": result["cattleInjuryEstimatedAge"],
#             "humanDeathVictimNames": result["humanDeathVictimNames"],
#             "humanDeathNumber": result["humanDeathNumber"],
#             "temporaryInjuryDetails": result["temporaryInjuryDetails"],
#             "permanentInjuryDetails": result["permanentInjuryDetails"],
#             "photoUrl": result["photoUrl"],
#             "eSignUrl": result["eSignUrl"],
#             "incidentUrl1": result["incidentUrl1"],
#             "incidentUrl2": result["incidentUrl2"],
#             "incidentUrl3": result["incidentUrl3"],
#             "status":result["status"],
#             "statusHistory":status_history
#         }
        
#         return jsonify({"found": "yes", "complaint": complaint_data}), 200
    
#     except Exception as e:
#         logging.error(f"Database error: {e}")
#         return jsonify({"error": str(e)}), 500
    
#     finally:
#         if connection.is_connected():
#             cursor.close()
#             connection.close()

# @app.route('/get_guard_complaints', methods=['POST'])
# def get_guard_complaints():
#     data = request.json
#     guard_id = data.get('guardId')

#     if not guard_id:
#         return jsonify({"error": "Missing guardId"}), 400

#     connection = create_connection()
#     if not connection:
#         return jsonify({"error": "Failed to connect to database"}), 500

#     try:
#         cursor = connection.cursor(dictionary=True)

#         # Step 1: Get Guard's Area from `emp` Table
#         query = """
#         SELECT division, subdivision, range_, circle1, beat 
#         FROM emp WHERE emp_id = %s
#         """
#         cursor.execute(query, (guard_id,))
#         guard_info = cursor.fetchone()

#         if not guard_info:
#             return jsonify({"error": "Guard not found"}), 404

#         # Convert beat to 'Beat X' format
#         guard_info['beat'] = f"Beat {guard_info['beat']}"

#         # Step 2: Match Guard's Area with Complaints
#         query = """
#         SELECT * FROM complaints
#         WHERE division = %s AND subdivision = %s AND range_ = %s 
#               AND circle1 = %s AND beat = %s AND status ="1"
#         """
#         params = (
#             guard_info['division'],
#             guard_info['subdivision'],
#             guard_info['range_'],
#             guard_info['circle1'],
#             guard_info['beat']
#         )
#         cursor.execute(query, params)
#         complaints = cursor.fetchall()

#         if not complaints:
#             return jsonify({"message": "No complaints found"}), 404

#         # **Fix statusHistory JSON issue**
#         for complaint in complaints:
#             if 'statusHistory' in complaint and complaint['statusHistory']:
#                 try:
#                     complaint['statusHistory'] = json.loads(complaint['statusHistory'])  # Convert JSON string to list
#                 except json.JSONDecodeError:
#                     complaint['statusHistory'] = []  # Default to an empty list if parsing fails

#         return jsonify({"found": "yes", "complaints": complaints}), 200

#     except Exception as e:
#         logging.error(f"Database error: {e}")
#         return jsonify({"error": str(e)}), 500

#     finally:
#         if connection.is_connected():
#             cursor.close()
#             connection.close()


# @app.route('/guards/<mobile_number>', methods=['GET'])
# def get_guard_by_mobile_number(mobile_number):
#     connection = create_connection()
#     if not connection:
#         return jsonify({"error": "Failed to connect to database"}), 500

#     try:
#         cursor = connection.cursor(dictionary=True)
#         query = "SELECT * FROM emp WHERE mobile_number = %s"
#         cursor.execute(query, (mobile_number,))
#         result = cursor.fetchone()
#         if result:
#             return jsonify(result), 200
#         else:
#             return jsonify({"message": "Guard not found"}), 404
#     except Error as e:
#         return jsonify({"error": str(e)}), 500
#     finally:
#         if connection.is_connected():
#             cursor.close()
#             connection.close()

# @app.route('/compensationform/<string:forest_guard_id>', methods=['GET'])
# def get_compensation_forms(forest_guard_id):
#     connection = create_connection()
#     if not connection:
#         return jsonify({"error": "Failed to connect to database"}), 500

#     try:
#         cursor = connection.cursor(dictionary=True)
#         query = """
#         SELECT * FROM compensationform
#         WHERE ForestGuardID = %s
#         """
#         cursor.execute(query, (forest_guard_id,))
#         compensation_forms = cursor.fetchall()

#         if not compensation_forms:
#             return jsonify({"message": "No compensation forms found for this ForestGuardID"}), 404

#         # Convert each form into a dictionary and decode the documentURL
#         result = []
#         for form in compensation_forms:
#             # Convert statusHistory JSON string to a list
#             try:
#                 status_history = json.loads(form["statusHistory"]) if form["statusHistory"] else []
#             except json.JSONDecodeError:
#                 status_history = []

#             form_data = {
#                 "formID": form["FormID"],
#                 "submissionDateTime": form["SubmissionDateTime"],
#                 "forestGuardID": form["ForestGuardID"],
#                 "complaint_id":form["complaint_id"],
#                 "applicantName": form["ApplicantName"],
#                 "age": form["Age"],
#                 "fatherSpouseName": form["FatherSpouseName"],
#                 "mobile": form["Mobile"],
#                 "email":form["email"],
#                 "animalName": form["AnimalName"],
#                 "incidentDate": form["IncidentDate"],
#                 "additionalDetails": form["AdditionalDetails"],
#                 "circle_CG": form["Circle_CG"],
#                 "circle1": form["Circle1"],
#                 "division": form["division"],
#                 "subdivision": form["subdivision"],
#                 "range_": form["range_"],
#                 "beat": form["beat"],
#                 "address": form["Address"],
#                 "cropType": form["CropType"],
#                 "cerealCrop": form["CerealCrop"],
#                 "cropDamageAmount":form["cropDamageAmount"],
#                 "cropDamageArea": form["CropDamageArea"],
#                 "fullHouseDamage": form["FullHouseDamage"],
#                 "partialHouseDamage": form["PartialHouseDamage"],
#                 "houseDamageAmount":form["houseDamageAmount"],
#                 "numberOfCattlesDied": form["NumberOfCattlesDied"],
#                 "estimatedCattleAge": form["EstimatedCattleAge"],
#                 "catleInjuryAmount":form["catleInjuryAmount"],
#                 "humanDeathVictimName": form["HumanDeathVictimName"],
#                 "numberOfDeaths": form["NumberOfDeaths"],
#                 "temporaryInjuryDetails": form["TemporaryInjuryDetails"],
#                 "permanentInjuryDetails": form["PermanentInjuryDetails"],
#                 "humanDeathAmount": form["humanDeathAmount"],
#                 "humanInjuryAmount": form["humanInjuryAmount"], 
#                 "bankName": form["BankName"],
#                 "ifscCode": form["IFSCCode"],
#                 "branchName": form["BranchName"],
#                 "accountHolderName": form["AccountHolderName"],
#                 "accountNumber": form["AccountNumber"],
#                 "panNumber": form["PANNumber"],
#                 "aadhaarNumber": form["AadhaarNumber"],
#                 "totalCompensationAmount": form["totalCompensationAmount"], 
#                 "statusHistory": status_history ,
#                 "documentURL": form["documentURL"],
#                 "photoUrl": form["photoUrl"],
#                 "eSignUrl": form["eSignUrl"],
#                 "incidentUrl1": form["incidentUrl1"],
#                 "incidentUrl2": form["incidentUrl2"],
#                 "incidentUrl3": form["incidentUrl3"],
#                 "verifiedBy": form["VerifiedBy"],
#                 "paymentProcessedBy": form["PaymentProcessedBy"],
#                 "comments": form["comments"]
#                  # Include parsed status history
#             }
#             result.append(form_data)

#         return jsonify(result), 200
#     except Error as e:
#         logging.error(f"Database error: {e}")
#         return jsonify({"error": str(e)}), 500
#     finally:
#         if connection.is_connected():
#             cursor.close()
#             connection.close()
# import json
# import urllib.parse
# from flask import jsonify

# @app.route('/compensationform/<string:role>/<string:emp_id>', methods=['GET'])
# def get_compensation_forms_by_role(role, emp_id):
#     """Fetch compensation forms based on the role of the employee."""
#     connection = create_connection()
#     if not connection:
#         return jsonify({"error": "Failed to connect to database"}), 500

#     try:
#         cursor = connection.cursor(dictionary=True)

#         # Step 1: Get employee details from the 'emp' table
#         emp_query = """
#         SELECT Circle_CG, Circle1, division, subdivision, range_, beat
#         FROM emp 
#         WHERE emp_id = %s AND roll = %s
#         """
#         cursor.execute(emp_query, (emp_id,role))
#         emp_data = cursor.fetchone()

#         if not emp_data:
#             return jsonify({"message": "Employee not found"}), 404

#         # Extract values from emp_data
#         circle_cg = emp_data["Circle_CG"]
#         circle1 = emp_data["Circle1"]
#         division = emp_data["division"]
#         subdivision = emp_data["subdivision"]
#         range_ = emp_data["range_"]
#         beat = emp_data["beat"]

#         # Step 2: Dynamically build the query based on role
#         query = "SELECT * FROM compensationform WHERE Circle_CG = %s"
#         query_params = [circle_cg]

#         if role.lower() == "pccf" or role.lower() == "ccf":
#             pass  # No additional filtering, only Circle_CG is needed
#         elif role.lower() == "dfo":
#             query += " AND division = %s"
#             query_params.append(division)
#         elif role.lower() == "sdo":
#             query += " AND subdivision = %s AND division = %s"
#             query_params.extend([subdivision, division])
#         elif role.lower() == "ranger":
#             query += " AND range_ = %s AND division = %s"
#             query_params.extend([range_, division])
#         elif role.lower() == "deputyranger":
#             query += " AND range_ = %s AND division = %s AND Circle1 = %s"
#             query_params.extend([range_, division, circle1])
#         elif role.lower() == "forestguard":
#             query += " AND range_ = %s AND division = %s AND Circle1 = %s AND beat = %s"
#             query_params.extend([range_, division, circle1, beat])
#         else:
#             return jsonify({"error": "Invalid role"}), 400

#         # Step 3: Execute query and fetch compensation forms
#         cursor.execute(query, tuple(query_params))
#         compensation_forms = cursor.fetchall()

#         if not compensation_forms:
#             return jsonify({"message": "No matching compensation forms found"}), 404

#         # Step 4: Convert result to JSON and parse statusHistory
#         result = []
#         for form in compensation_forms:
#             # Parse statusHistory JSON string into a Python list
#             try:
#                 status_history = json.loads(form["statusHistory"]) if form["statusHistory"] else []
#             except json.JSONDecodeError:
#                 status_history = []

#             form_data = {
#                 "formID": form["FormID"],
#                 "submissionDateTime": form["SubmissionDateTime"],
#                 "forestGuardID": form["ForestGuardID"],
#                 "complaint_id":form["complaint_id"],

#                 "applicantName": form["ApplicantName"],
#                 "age": form["Age"],
#                 "fatherSpouseName": form["FatherSpouseName"],
#                 "mobile": form["Mobile"],
#                 "email":form["email"],
#                 "animalName": form["AnimalName"],
#                 "incidentDate": form["IncidentDate"],
#                 "additionalDetails": form["AdditionalDetails"],
#                 "circle_CG": form["Circle_CG"],
#                 "circle1": form["Circle1"],
#                 "division": form["division"],
#                 "subdivision": form["subdivision"],
#                 "range_": form["range_"],
#                 "beat": form["beat"],
#                 "address": form["Address"],
#                 "cropType": form["CropType"],
#                 "cerealCrop": form["CerealCrop"],
#                 "cropDamageAmount":form["cropDamageAmount"],
#                 "cropDamageArea": form["CropDamageArea"],
#                 "fullHouseDamage": form["FullHouseDamage"],
#                 "partialHouseDamage": form["PartialHouseDamage"],
#                 "houseDamageAmount":form["houseDamageAmount"],
#                 "numberOfCattlesDied": form["NumberOfCattlesDied"],
#                 "estimatedCattleAge": form["EstimatedCattleAge"],
#                 "catleInjuryAmount":form["catleInjuryAmount"],
#                 "humanDeathVictimName": form["HumanDeathVictimName"],
#                 "numberOfDeaths": form["NumberOfDeaths"],
#                 "temporaryInjuryDetails": form["TemporaryInjuryDetails"],
#                 "permanentInjuryDetails": form["PermanentInjuryDetails"],
#                 "humanDeathAmount": form["humanDeathAmount"],
#                 "humanInjuryAmount": form["humanInjuryAmount"], 
#                 "bankName": form["BankName"],
#                 "ifscCode": form["IFSCCode"],
#                 "branchName": form["BranchName"],
#                 "accountHolderName": form["AccountHolderName"],
#                 "accountNumber": form["AccountNumber"],
#                 "panNumber": form["PANNumber"],
#                 "aadhaarNumber": form["AadhaarNumber"],
#                 "totalCompensationAmount": form["totalCompensationAmount"], 
#                 "statusHistory": status_history ,
#                 "status": form["Status"],
#                 "documentURL": form["documentURL"],
#                 "photoUrl": form["photoUrl"],
#                 "eSignUrl": form["eSignUrl"],
#                 "incidentUrl1": form["incidentUrl1"],
#                 "incidentUrl2": form["incidentUrl2"],
#                 "incidentUrl3": form["incidentUrl3"],

#                 "verifiedBy": form["VerifiedBy"],
#                 "paymentProcessedBy": form["PaymentProcessedBy"],
#                 "comments": form["comments"]
#                  # Include parsed status history
#             }
#             result.append(form_data)

#         return jsonify(result), 200

#     except mysql.connector.Error as e:
#         return jsonify({"error": str(e)}), 500
#     finally:
#         if connection.is_connected():
#             cursor.close()
#             connection.close()

            
# import json
# import logging
# import datetime
# from flask import request, jsonify


# @app.route('/update_form_status/<int:form_id>', methods=['POST'])
# def update_form_status(form_id):
#     """
#     API to update the status of a compensation form and track status history.
#     Also updates the corresponding complaint status if linked.
#     """

#     data = request.json
#     emp_id = data.get("emp_id")  # Employee ID of the verifier
#     action = data.get("action")  # 'accept', 'reject', or 'send_back'
#     comments = data.get("comments", "")  # Default to empty string if not provided

#     if not emp_id or not action:
#         return jsonify({"error": "Missing required fields: emp_id or action"}), 400

#     connection = create_connection()
#     if not connection:
#         return jsonify({"error": "Failed to connect to database"}), 500

#     try:
#         cursor = connection.cursor(dictionary=True)

#         # Fetch current form details including statusHistory and complaint_id
#         query = "SELECT status, verifiedBy, statusHistory, complaint_id FROM compensationform WHERE FormID = %s"
#         cursor.execute(query, (form_id,))
#         form = cursor.fetchone()

#         if not form:
#             return jsonify({"error": "Form not found"}), 404

#         status_str, verified_by, status_history_json, complaint_id = (
#             form["status"], form["verifiedBy"], form["statusHistory"], form["complaint_id"]
#         )
#         verified_by = verified_by if verified_by else ""  # Handle null verifiedBy

#         try:
#             current_status = int(status_str)  # Convert status from string to integer
#         except ValueError:
#             return jsonify({"error": "Invalid status value in database"}), 500

#         # Determine next status based on action
#         if action == "accept":
#             next_status = current_status + 1  # Approved by ranger
#         elif action == "reject":
#             next_status = -1  # Rejected
#         elif action == "send_back":
#             next_status = max(0, current_status - 1)  # Ensure status doesn't go below 0
#         else:
#             return jsonify({"error": "Invalid action"}), 400

#         next_status_str = str(next_status)  # Convert status back to string

#         # Append verifier ID if not already included
#         if emp_id not in verified_by.split(","):
#             verified_by = (verified_by + "," + emp_id).strip(",")

#         # Parse existing statusHistory JSON
#         try:
#             status_history = json.loads(status_history_json) if status_history_json else []
#         except json.JSONDecodeError:
#             status_history = []

#         # Generate current timestamp in ISO format
#         current_timestamp = datetime.datetime.utcnow().isoformat() + "Z"

#         # Append new status update entry
#         new_status_entry = {
#             "status": next_status_str,
#             "comment": comments,
#             "timestamp": current_timestamp,
#             "updatedBy": emp_id
#         }
#         status_history.append(new_status_entry)

#         # Convert back to JSON string
#         updated_status_history_json = json.dumps(status_history)

#         # Update form status, verification details, and status history
#         update_query = """
#         UPDATE compensationform
#         SET status = %s, verifiedBy = %s, comments = COALESCE(%s, comments), statusHistory = %s
#         WHERE FormID = %s
#         """
#         cursor.execute(update_query, (next_status_str, verified_by, comments if comments else None, updated_status_history_json, form_id))

#         # If a complaint_id exists, also update the complaint status and statusHistory
#         if complaint_id:
#             # Fetch current statusHistory of the complaint
#             query = "SELECT statusHistory FROM complaints WHERE complaint_id = %s"
#             cursor.execute(query, (complaint_id,))
#             complaint_info = cursor.fetchone()

#             complaint_status_history = []
#             if complaint_info and complaint_info['statusHistory']:
#                 try:
#                     complaint_status_history = json.loads(complaint_info['statusHistory'])
#                 except json.JSONDecodeError:
#                     pass  # If parsing fails, continue with an empty list

#             # Append new status update for complaint
#             complaint_status_entry = {
#                 "status": next_status_str,
#                 "comment": comments,
#                 "timestamp": current_timestamp,
#                 "updatedBy": emp_id
#             }
#             complaint_status_history.append(complaint_status_entry)

#             # Convert back to JSON
#             updated_complaint_status_history_json = json.dumps(complaint_status_history)

#             # Update the complaint status and history
#             update_complaint_query = """
#             UPDATE complaints
#             SET status = %s, statusHistory = %s
#             WHERE complaint_id = %s
#             """
#             cursor.execute(update_complaint_query, (next_status_str, updated_complaint_status_history_json, complaint_id))

#         connection.commit()

#         return jsonify({
#             "message": f"Form {form_id} status updated successfully",
#             "new_status": next_status_str,
#             "verified_by": verified_by
#         }), 200

#     except mysql.connector.Error as e:
#         logging.error(f"Database error: {e}")
#         return jsonify({"error": str(e)}), 500

#     finally:
#         if connection.is_connected():
#             cursor.close()
#             connection.close()


# @app.route('/reject_complaint', methods=['POST'])
# def reject_complaint():
#     data = request.json
#     complaint_id = data.get('complaint_id')
#     guard_id = data.get('guardId')
#     comment = data.get('comment')

#     if not all([complaint_id, guard_id, comment]):
#         return jsonify({"error": "Missing complaint_id, guardId, or comment"}), 400

#     connection = create_connection()
#     if not connection:
#         return jsonify({"error": "Failed to connect to database"}), 500

#     try:
#         cursor = connection.cursor(dictionary=True)

#         # **Step 1: Get Guard's Area**
#         query = """
#         SELECT division, subdivision, range_, circle1, CONCAT('Beat ', beat) AS beat
#         FROM emp WHERE emp_id = %s
#         """
#         cursor.execute(query, (guard_id,))
#         guard_info = cursor.fetchone()

#         if not guard_info:
#             return jsonify({"error": "Guard not found"}), 404

#         # **Step 2: Get Complaint's Area**
#         query = """
#         SELECT division, subdivision, range_, circle1, beat, statusHistory
#         FROM complaints WHERE complaint_id = %s
#         """
#         cursor.execute(query, (complaint_id,))
#         complaint_info = cursor.fetchone()

#         if not complaint_info:
#             return jsonify({"error": "Complaint not found"}), 404

#         # **Step 3: Check if Guard and Complaint have the same area**
#         if (
#             guard_info['division'] != complaint_info['division'] or
#             guard_info['subdivision'] != complaint_info['subdivision'] or
#             guard_info['range_'] != complaint_info['range_'] or
#             guard_info['circle1'] != complaint_info['circle1'] or
#             guard_info['beat'] != complaint_info['beat']
#         ):
#             return jsonify({"error": "Guard does not have permission to reject this complaint"}), 403

#         # **Step 4: Fetch and Append to Status History**
#         status_history = []
#         if complaint_info['statusHistory']:
#             try:
#                 status_history = json.loads(complaint_info['statusHistory'])  # Convert JSON string to list
#             except json.JSONDecodeError:
#                 pass  # If parsing fails, continue with an empty list

#         # Create a new status update
#         rejection_entry = {
#             "status": "-1",
#             "comment": comment,
#             "timestamp": datetime.now().isoformat(),
#             "updatedBy": guard_id
#         }
#         status_history.append(rejection_entry)
#         status_history_json = json.dumps(status_history)

#         # **Step 5: Update Complaint Record**
#         update_query = """
#         UPDATE complaints 
#         SET status = %s, statusHistory = %s
#         WHERE complaint_id = %s
#         """
#         cursor.execute(update_query, ("-1", status_history_json, complaint_id))
#         connection.commit()

#         return jsonify({"message": "Complaint rejected successfully"}), 200

#     except Exception as e:
#         logging.error(f"Database error: {e}")
#         return jsonify({"error": str(e)}), 500

#     finally:
#         if connection.is_connected():
#             cursor.close()
#             connection.close()

