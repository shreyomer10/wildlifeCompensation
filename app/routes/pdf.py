import os,json
from io import BytesIO
from datetime import datetime
from flask import Flask, request, jsonify, abort,Blueprint
from app.models.database import create_connection 

import mysql.connector
import firebase_admin
from firebase_admin import credentials, storage
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from app.utils.tokenCheck import token_required
from app.utils.rate_limit import limiter

# ── Flask App Initialization ──────────────────────────────────────────────────

from app.config import Config

db_config = {
    "host": Config.DB_HOST,
    "user": Config.DB_USER,
    "password": Config.DB_PASSWORD,
    "database": Config.DB_NAME,
    "port": Config.DB_PORT,
    "Redis_URL":Config.REDIS_URL,
    "Firebase_Key":Config.FirebaseKey
}


# Firebase Admin SDK JSON (downloaded from Firebase Console)
FIREBASE_CERT_PATH = db_config["Firebase_Key"]
#FIREBASE_CERT_PATH1="compensation-app-4b6fa-firebase-adminsdk-j16ov-73c4c86418.json"
FIREBASE_BUCKET_NAME = "compensation-app-4b6fa.firebasestorage.app"  # e.g. "my-project.appspot.com"

try:
    cred = credentials.Certificate(json.loads(FIREBASE_CERT_PATH))
    #cred = credentials.Certificate(FIREBASE_CERT_PATH1)

    firebase_admin.initialize_app(cred, {
        "storageBucket": FIREBASE_BUCKET_NAME
    })
    bucket = storage.bucket()
except Exception as e:
    # If initialization fails, the app won’t start correctly; log and re-raise
    raise RuntimeError(f"Failed to initialize Firebase Admin SDK: {e}")


pdf_bp = Blueprint('pdf', __name__)

def generate_pdf_bytes(
    form_type: str,
    personal_info: dict,
    details: dict
) -> BytesIO:
    """
    form_type: "complaint" or "compensation"
    personal_info: common fields (name, age, mobile, etc.)
    details: all other form‐specific fields (animalList, damageDate, etc.)
    Returns a BytesIO buffer containing the PDF.
    """
    buffer = BytesIO()
    width, height = A4
    p = canvas.Canvas(buffer, pagesize=A4)
    
    # Styles
    title_font = ("Helvetica-Bold", 18)
    section_font = ("Helvetica-Bold", 14, '#1a5276')  # Dark blue for section titles
    field_font = ("Helvetica", 11)
    field_label_font = ("Helvetica-Bold", 11)
    url_font = ("Helvetica", 11, '#1a5276')  # Blue for URLs
    
    # Margins and spacing
    left_margin = 40
    right_margin = width - 40
    top_margin = height - 50
    line_height = 16
    box_padding = 8
    section_spacing = 30
    
    # Current y position
    y = top_margin
    
    # --- Helper Functions ---
    def draw_section_title(title):
        nonlocal y
        y -= section_spacing  # Space before section
        p.setFont(*section_font)
        p.setFillColor(section_font[2])
        p.drawString(left_margin, y, title)
        y -= line_height + 8  # Space after title
        p.setFillColor('black')  # Reset to black
    
    def draw_field(label, value, is_url=False):
        nonlocal y
        if y < 100:  # Near bottom of page
            p.showPage()
            y = top_margin
        
        # Calculate text width and height needed
        p.setFont(*field_label_font)
        label_width = p.stringWidth(f"{label}: ", *field_label_font)
        
        value_str = str(value) if value is not None else "-"
        p.setFont(*field_font)
        
        if is_url and value:
            # Handle URL fields
            url_text = value_str if len(value_str) < 50 else value_str[:47] + "..."
            value_width = p.stringWidth(url_text, *field_font)
            total_width = label_width + value_width
            
            # Draw field in one line (label + value)
            p.setFont(*field_label_font)
            p.drawString(left_margin, y, f"{label}: ")
            p.setFont(*url_font)
            p.setFillColor(url_font[2])
            p.drawString(left_margin + label_width, y, url_text)
            p.linkURL(value, (left_margin + label_width, y, 
                     left_margin + label_width + value_width, y + line_height))
            p.setFillColor('black')
            y -= line_height + 4
        else:
            # Handle regular fields
            text_obj = p.beginText(left_margin, y)
            text_obj.setFont(*field_label_font)
            text_obj.textOut(f"{label}: ")
            text_obj.setFont(*field_font)
            
            if value:
                words = value_str.split()
                current_line = ""
                first_line = True
                
                for word in words:
                    test_line = f"{current_line} {word}".strip()
                    test_width = p.stringWidth(test_line, *field_font)
                    
                    if test_width < (right_margin - left_margin - label_width):
                        current_line = test_line
                    else:
                        if first_line:
                            # First line continues after label
                            remaining_width = right_margin - left_margin - label_width
                            text_obj.textLine(current_line)
                            first_line = False
                        else:
                            # Subsequent lines are indented
                            text_obj.textLine("")
                            text_obj.textOut(" " * (len(label) + 2))  # Align with first line
                            text_obj.textLine(current_line)
                        current_line = word
                
                if current_line:
                    if first_line:
                        text_obj.textLine(current_line)
                    else:
                        text_obj.textLine("")
                        text_obj.textOut(" " * (len(label) + 2))
                        text_obj.textLine(current_line)
            else:
                text_obj.textLine("-")
            
            p.drawText(text_obj)
            
            # Calculate how much space was used
            lines_used = len(str(value_str).split('\n')) if '\n' in str(value_str) else 1
            if len(str(value_str)) > 30:  # Estimate multi-line
                lines_used = max(lines_used, len(str(value_str)) // 30 + 1)
            y -= lines_used * line_height + 4
    
    def draw_header():
        nonlocal y
        # Draw Chhattisgarh logo (will be added from backend)
        # try:
        #     logo_path = os.path.join(os.getcwd(), "logo.png")
        #     p.drawImage(logo_path, left_margin, height - 80, width=80, height=80, preserveAspectRatio=True, mask='auto')
        # except Exception:
        #     pass
        
        # Government header text
        p.setFont("Helvetica-Bold", 14)
        p.drawCentredString(width / 2, height - 60, "Government of Chhattisgarh")
        p.setFont("Helvetica-Bold", 12)
        p.drawCentredString(width / 2, height - 80, "Forest Department")
        
        # Form title
        p.setFont(*title_font)
        title = "COMPLAINT FORM" if form_type == "complaint" else "COMPENSATION CLAIM FORM"
        p.drawCentredString(width / 2, height - 110, title)
        
        # Horizontal lines
        p.setLineWidth(1)
        p.line(left_margin, height - 120, right_margin, height - 120)
        p.setLineWidth(0.5)
        p.line(left_margin, height - 122, right_margin, height - 122)
        
        y = height - 140
    
    # --- 1) Draw Header ---
    draw_header()
    
    # --- 2) Section: Personal Details ---
    draw_section_title("1. PERSONAL DETAILS")
    
    personal_fields = [
        ("Name", personal_info.get("name")),
        ("Age", personal_info.get("age")),
        ("Father/Spouse Name", personal_info.get("fatherOrSpouseName")),
        ("Mobile", personal_info.get("mobile")),
        ("Email", personal_info.get("email")),
        ("Aadhaar", personal_info.get("adhaar"))
    ]
    
    for label, value in personal_fields:
        draw_field(label, value)

    # --- 3) Section: Incident & Location Details ---
    draw_section_title("2. INCIDENT & LOCATION DETAILS")
    
    incident_fields = [
        ("Incident Date", details.get("damageDate") or details.get("IncidentDate")),
        ("Circle (CG)", details.get("circle_cg") or details.get("Circle_CG")),
        ("Division", details.get("division")),
        ("Subdivision", details.get("subdivision")),
        ("Range", details.get("range_")),
        ("Circle1", details.get("circle1") or details.get("Circle1")),
        ("Beat", details.get("beat")),
        ("Address", details.get("address") or details.get("Address"))
    ]
    
    for label, value in incident_fields:
        draw_field(label, value)

    # --- 4) Section: Form‐Specific Details ---
    draw_section_title("3. DETAILS & DAMAGES")
    
    if form_type == "complaint":
        complaint_fields = [
            ("Animals Involved", details.get("animalList")),
            ("Additional Details", details.get("additionalDetails")),
            ("Crop Type", details.get("cropType")),
            ("Cereal Crop", details.get("cerealCrop")),
            ("Full Houses Damaged", details.get("fullHousesDamaged")),
            ("Partial Houses Damaged", details.get("partialHousesDamaged")),
            ("Cattle Injured", 
             f"{details.get('cattleInjuryNumber', '')} (Age: {details.get('cattleInjuryEstimatedAge', '')})" 
             if details.get("cattleInjuryNumber") or details.get("cattleInjuryEstimatedAge") else None),
            ("Human Death Victims", details.get("humanDeathVictimNames")),
            ("Number of Deaths", details.get("humanDeathNumber")),
            ("Temporary Injuries", details.get("temporaryInjuryDetails")),
            ("Permanent Injuries", details.get("permanentInjuryDetails")),
            ("Photo URL", details.get("photoUrl"), True),
            ("E-Sign URL", details.get("eSignUrl"), True),
            ("Incident URL 1", details.get("incidentUrl1"), True),
            ("Incident URL 2", details.get("incidentUrl2"), True),
            ("Incident URL 3", details.get("incidentUrl3"), True)
        ]
        
        for field in complaint_fields:
            if len(field) == 3:  # Has URL flag
                draw_field(field[0], field[1], field[2])
            else:
                draw_field(field[0], field[1])
    
    else:  # Compensation form
        compensation_fields = [
            ("Crop Damage Amount", details.get("cropdamageAmount")),
            ("Crop Damage Area", details.get("CropDamageArea")),
            ("Additional Details", details.get("AdditionalDetails")),
            ("NOC Report", details.get("nocReport"), True),
            ("Land Ownership Report", details.get("landOwnershipReport"), True),
            ("ROR Report", details.get("rorReport"), True),
            ("Full House Damage", details.get("FullHouseDamage")),
            ("Partial House Damage", details.get("PartialHouseDamage")),
            ("House Damage Amount", details.get("houseDamageAmount")),
            ("Cattle Died", 
             f"{details.get('NumberOfCattlesDied', '')} (Age: {details.get('EstimatedCattleAge', '')})" 
             if details.get("NumberOfCattlesDied") or details.get("EstimatedCattleAge") else None),
            ("Cattle Injury Amount", details.get("catleInjuryAmount")),
            ("Cattle Photo", details.get("cattlePhoto"), True),
            ("VAS Certificate", details.get("vasCertificate"), True),
            ("Human Death Victim", details.get("HumanDeathVictimName")),
            ("Number of Deaths", details.get("NumberOfDeaths")),
            ("Temporary Injuries", details.get("TemporaryInjuryDetails")),
            ("Permanent Injuries", details.get("PermanentInjuryDetails")),
            ("Human Photo 1", details.get("humanPhoto1"), True),
            ("Human Photo 2", details.get("humanPhoto2"), True),
            ("Death Certificate", details.get("deathCertificate"), True),
            ("Medical Certificate", details.get("medicalCertificate"), True),
            ("Bank Name", details.get("BankName")),
            ("IFSC Code", details.get("IFSCCode")),
            ("Branch Name", details.get("BranchName")),
            ("Account Holder", details.get("AccountHolderName")),
            ("Account Number", details.get("AccountNumber")),
            ("PAN Number", details.get("PANNumber")),
            ("Aadhaar Number", details.get("AadhaarNumber")),
            ("Total Compensation", details.get("totalCompensationAmount")),
            ("Comments", details.get("comments"))
        ]
        
        for field in compensation_fields:
            if len(field) == 3:  # Has URL flag
                draw_field(field[0], field[1], field[2])
            else:
                draw_field(field[0], field[1])

    # --- 5) Footer ---
    p.setFont("Helvetica-Oblique", 9)
    p.drawString(left_margin, 30, f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    p.showPage()
    p.save()
    buffer.seek(0)
    return buffer


# # ── Helper: Generate a PDF BytesIO from SQL row data ─────────────────────────────
# def generate_pdf_bytes(
#     form_type: str,
#     personal_info: dict,
#     details: dict
# ) -> BytesIO:
#     """
#     form_type: "complaint" or "compensation"
#     personal_info: common fields (name, age, mobile, etc.)
#     details: all other form‐specific fields (animalList, damageDate, etc.)
#     Returns a BytesIO buffer containing the PDF.
#     """
#     buffer = BytesIO()
#     width, height = A4
#     p = canvas.Canvas(buffer, pagesize=A4)
    
#     # Styles
#     title_font = ("Helvetica-Bold", 18)
#     section_font = ("Helvetica-Bold", 14)
#     field_font = ("Helvetica", 11)
#     url_font = ("Helvetica", 11)
    
#     # Margins and spacing
#     left_margin = 40
#     right_margin = width - 40
#     top_margin = height - 50
#     line_height = 16
#     box_padding = 5
#     section_spacing = 24
    
#     # Current y position
#     y = top_margin
    
#     # --- Helper Functions ---
#     def draw_section_title(title):
#         nonlocal y
#         p.setFont(*section_font)
#         p.drawString(left_margin, y, title)
#         y -= line_height + 4
    
#     def draw_field(label, value, is_url=False):
#         nonlocal y
#         if y < 100:  # Near bottom of page
#             p.showPage()
#             y = top_margin
        
#         p.setFont(*field_font)
#         text = f"{label}: {value}" if value else f"{label}: -"
        
#         # Handle URLs
#         if is_url and value:
#             p.setFillColorRGB(0, 0, 1)  # Blue for links
#             p.setFont(*url_font)
#             p.drawString(left_margin + box_padding, y, f"{label}: ")
#             text_width = p.stringWidth(f"{label}: ", *url_font)
#             url_text = value if len(value) < 50 else value[:47] + "..."
#             p.drawString(left_margin + box_padding + text_width, y, url_text)
#             p.linkURL(value, (left_margin + box_padding + text_width, y, 
#                      left_margin + box_padding + text_width + p.stringWidth(url_text, *url_font), y + line_height))
#             p.setFillColorRGB(0, 0, 0)  # Reset to black
#         else:
#             # Handle long text with text wrapping
#             text_obj = p.beginText(left_margin + box_padding, y)
#             text_obj.setFont(*field_font)
#             text_obj.textLine(f"{label}:")
            
#             lines = []
#             if value:
#                 words = str(value).split()
#                 current_line = ""
#                 for word in words:
#                     test_line = f"{current_line} {word}".strip()
#                     if p.stringWidth(test_line, *field_font) < (right_margin - left_margin - 2 * box_padding):
#                         current_line = test_line
#                     else:
#                         lines.append(current_line)
#                         current_line = word
#                 if current_line:
#                     lines.append(current_line)
            
#             if lines:
#                 for line in lines:
#                     text_obj.textLine(line)
#             else:
#                 text_obj.textLine("-")
            
#             p.drawText(text_obj)
        
#         # Adjust y position
#         if value and len(str(value)) > 60 or '\n' in str(value):
#             y -= (len(lines) if lines else 1) * line_height + 4
#         else:
#             y -= line_height
    
#     def draw_boxed_field(label, value, is_url=False):
#         nonlocal y
#         if y < 100:  # Near bottom of page
#             p.showPage()
#             y = top_margin
        
#         # Calculate height needed
#         text_height = line_height
#         if value and (len(str(value)) > 60 or '\n' in str(value)):
#             lines = str(value).split('\n')
#             wrapped_lines = []
#             for line in lines:
#                 words = line.split()
#                 current_line = ""
#                 for word in words:
#                     test_line = f"{current_line} {word}".strip()
#                     if p.stringWidth(test_line, *field_font) < (right_margin - left_margin - 2 * box_padding):
#                         current_line = test_line
#                     else:
#                         wrapped_lines.append(current_line)
#                         current_line = word
#                 if current_line:
#                     wrapped_lines.append(current_line)
#             text_height = len(wrapped_lines) * line_height if wrapped_lines else line_height
        
#         # Draw box
#         p.rect(left_margin, y - text_height - 2 * box_padding, 
#                right_margin - left_margin, text_height + 2 * box_padding)
        
#         # Draw content
#         p.setFont(*field_font)
#         text_obj = p.beginText(left_margin + box_padding, y - box_padding)
#         text_obj.setFont(*field_font)
#         text_obj.textLine(f"{label}:")
        
#         if value:
#             if is_url:
#                 p.setFillColorRGB(0, 0, 1)  # Blue for links
#                 text_obj.textLine(value)
#                 p.drawText(text_obj)
#                 p.linkURL(value, (left_margin + box_padding, y - box_padding - line_height, 
#                          left_margin + box_padding + p.stringWidth(value, *field_font), y - box_padding))
#                 p.setFillColorRGB(0, 0, 0)  # Reset to black
#             else:
#                 lines = str(value).split('\n')
#                 for line in lines:
#                     words = line.split()
#                     current_line = ""
#                     for word in words:
#                         test_line = f"{current_line} {word}".strip()
#                         if p.stringWidth(test_line, *field_font) < (right_margin - left_margin - 2 * box_padding):
#                             current_line = test_line
#                         else:
#                             text_obj.textLine(current_line)
#                             current_line = word
#                     if current_line:
#                         text_obj.textLine(current_line)
#                 p.drawText(text_obj)
#         else:
#             text_obj.textLine("-")
#             p.drawText(text_obj)
        
#         y -= text_height + 2 * box_padding + 4
    
#     # --- 1) Draw Logo & Header ---
#     try:
#         logo_path = os.path.join(os.getcwd(), "logo.png")
#         p.drawImage(logo_path, left_margin, height - 80, width=120, height=40, preserveAspectRatio=True)
#     except Exception:
#         pass

#     # Title
#     p.setFont(*title_font)
#     title = "Complaint Form" if form_type == "complaint" else "Compensation Form"
#     p.drawCentredString(width / 2, height - 50, title)
#     p.line(left_margin, height - 60, right_margin, height - 60)
#     y -= 40

#     # --- 2) Section: Personal Details ---
#     draw_section_title("1. Personal Details")
    
#     personal_fields = [
#         ("Name", personal_info.get("name")),
#         ("Age", personal_info.get("age")),
#         ("Father/Spouse Name", personal_info.get("fatherOrSpouseName")),
#         ("Mobile", personal_info.get("mobile")),
#         ("Email", personal_info.get("email")),
#         ("Aadhaar", personal_info.get("adhaar"))
#     ]
    
#     for label, value in personal_fields:
#         draw_boxed_field(label, value)

#     # --- 3) Section: Incident & Location Details ---
#     draw_section_title("2. Incident & Location Details")
    
#     incident_fields = [
#         ("Incident Date", details.get("damageDate") or details.get("IncidentDate")),
#         ("Circle (CG)", details.get("circle_cg") or details.get("Circle_CG")),
#         ("Division", details.get("division")),
#         ("Subdivision", details.get("subdivision")),
#         ("Range", details.get("range_")),
#         ("Circle1", details.get("circle1") or details.get("Circle1")),
#         ("Beat", details.get("beat")),
#         ("Address", details.get("address") or details.get("Address"))
#     ]
    
#     for label, value in incident_fields:
#         draw_boxed_field(label, value)

#     # --- 4) Section: Form‐Specific Details ---
#     draw_section_title("3. Details & Damages")
    
#     if form_type == "complaint":
#         complaint_fields = [
#             ("Animals Involved", details.get("animalList")),
#             ("Additional Details", details.get("additionalDetails")),
#             ("Crop Type", details.get("cropType")),
#             ("Cereal Crop", details.get("cerealCrop")),
#             ("Full Houses Damaged", details.get("fullHousesDamaged")),
#             ("Partial Houses Damaged", details.get("partialHousesDamaged")),
#             ("Cattle Injured", 
#              f"{details.get('cattleInjuryNumber', '')} (Est. Age: {details.get('cattleInjuryEstimatedAge', '')})" 
#              if details.get("cattleInjuryNumber") or details.get("cattleInjuryEstimatedAge") else None),
#             ("Human Death Victims", details.get("humanDeathVictimNames")),
#             ("Number of Deaths", details.get("humanDeathNumber")),
#             ("Temporary Injuries", details.get("temporaryInjuryDetails")),
#             ("Permanent Injuries", details.get("permanentInjuryDetails")),
#             ("Photo URL", details.get("photoUrl"), True),
#             ("E-Sign URL", details.get("eSignUrl"), True),
#             ("Incident URL 1", details.get("incidentUrl1"), True),
#             ("Incident URL 2", details.get("incidentUrl2"), True),
#             ("Incident URL 3", details.get("incidentUrl3"), True)
#         ]
        
#         for field in complaint_fields:
#             if len(field) == 3:  # Has URL flag
#                 draw_boxed_field(field[0], field[1], field[2])
#             else:
#                 draw_boxed_field(field[0], field[1])
    
#     else:  # Compensation form
#         compensation_fields = [
#             ("Crop Damage Amount", details.get("cropdamageAmount")),
#             ("Crop Damage Area", details.get("CropDamageArea")),
#             ("Additional Details", details.get("AdditionalDetails")),
#             ("NOC Report", details.get("nocReport"), True),
#             ("Land Ownership Report", details.get("landOwnershipReport"), True),
#             ("ROR Report", details.get("rorReport"), True),
#             ("Full House Damage", details.get("FullHouseDamage")),
#             ("Partial House Damage", details.get("PartialHouseDamage")),
#             ("House Damage Amount", details.get("houseDamageAmount")),
#             ("Cattle Died", 
#              f"{details.get('NumberOfCattlesDied', '')} (Est. Age: {details.get('EstimatedCattleAge', '')})" 
#              if details.get("NumberOfCattlesDied") or details.get("EstimatedCattleAge") else None),
#             ("Cattle Injury Amount", details.get("catleInjuryAmount")),
#             ("Cattle Photo", details.get("cattlePhoto"), True),
#             ("VAS Certificate", details.get("vasCertificate"), True),
#             ("Human Death Victim", details.get("HumanDeathVictimName")),
#             ("Number of Deaths", details.get("NumberOfDeaths")),
#             ("Temporary Injuries", details.get("TemporaryInjuryDetails")),
#             ("Permanent Injuries", details.get("PermanentInjuryDetails")),
#             ("Human Photo 1", details.get("humanPhoto1"), True),
#             ("Human Photo 2", details.get("humanPhoto2"), True),
#             ("Death Certificate", details.get("deathCertificate"), True),
#             ("Medical Certificate", details.get("medicalCertificate"), True),
#             ("Bank Name", details.get("BankName")),
#             ("IFSC Code", details.get("IFSCCode")),
#             ("Branch Name", details.get("BranchName")),
#             ("Account Holder", details.get("AccountHolderName")),
#             ("Account Number", details.get("AccountNumber")),
#             ("PAN Number", details.get("PANNumber")),
#             ("Aadhaar Number", details.get("AadhaarNumber")),
#             ("Total Compensation", details.get("totalCompensationAmount")),
#             ("Comments", details.get("comments"))
#         ]
        
#         for field in compensation_fields:
#             if len(field) == 3:  # Has URL flag
#                 draw_boxed_field(field[0], field[1], field[2])
#             else:
#                 draw_boxed_field(field[0], field[1])

#     # --- 5) Footer ---
#     p.setFont("Helvetica-Oblique", 9)
#     p.drawString(left_margin, 30, f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

#     p.showPage()
#     p.save()
#     buffer.seek(0)
#     return buffer



@pdf_bp.route("/pdf", methods=["POST"])
@limiter.limit("5 per minute")
def get_or_create_pdf():
    data = request.json
    mobile   = data.get('mobile').strip()
    username = data.get('username').strip()
    fg_id    = data.get('forestguardId')
    form_id_raw = data.get('form_id')
    is_comp_s   = str(data.get("is_compensation")).lower().strip()
    if form_id_raw is None:
        return jsonify({"error": "Missing form_id field"}), 400
    if not (mobile and username and form_id_raw is not None and is_comp_s in ("true", "false")):
        return jsonify({"error": "Required fields: mobile, username, form_id, is_compensation=true/false. If is_compensation=true, also provide forestguardId."}), 400
    form_id = form_id_raw
    print("FormID",form_id)

    # try:
    #     form_id = int(form_id_raw)
    # except (ValueError, TypeError):
    #     return jsonify({"error": "form_id must be an integer"}), 400

    is_comp = (is_comp_s == "true")
    if is_comp and not fg_id:
        return jsonify({"error": "When is_compensation=true, forestguardId is required"}), 400

    # ── 2) Determine table & storage folder ─────────────────────────────────────
    if is_comp:
        table_name     = "compensationform"
        storage_folder = f"forms/{fg_id}_{mobile}"
        form_type      = "compensation"
        pk_field       = "FormID"
    else:
        table_name     = "complaints"
        storage_folder = f"complaints/{username}_{mobile}"
        form_type      = "complaint"
        pk_field       = "complaint_id"

    # ── 3) Check if PDF already exists in Firebase Storage ───────────────────────
    blob_path = f"{storage_folder}/{form_id}.pdf"
    try:
        blob = bucket.blob(blob_path)
        if blob.exists():
            return jsonify({"download_url": blob.public_url}), 200
    except Exception as e:
        return jsonify({"error": f"Error checking storage: {e}"}), 500

    # ── 4) Fetch record from SQL DB ─────────────────────────────────────────────
    try:
        connection = create_connection()
        if not connection:
            return jsonify({"error": "Database connection failed"}), 500

        cursor = connection.cursor(dictionary=True)

        if is_comp:
            query = """
                SELECT * FROM compensationform
                WHERE FormID = %s AND ForestGuardID = %s AND Mobile = %s
            """
            cursor.execute(query, (form_id, fg_id, mobile))
        else:
            
            query = """
                SELECT * FROM complaints
                WHERE complaint_id = %s
                  AND mobile = %s
            """
            cursor.execute(query, (form_id, mobile))

        row = cursor.fetchone()
        cursor.close()
        connection.close()
    except mysql.connector.Error as db_err:
        return jsonify({"error": f"SQL error: {db_err}"}), 500
    except Exception as e:
        return jsonify({"error": f"Unexpected DB error: {e}"}), 500

    if not row:
        return jsonify({"error": f"No record found in `{table_name}` for form_id={form_id} and provided credentials"}), 404

    # ── 5) Split row into common_fields & details ─────────────────────────────────
    try:
        common_fields = {
            "name":               row.get("name")              or row.get("ApplicantName", ""),
            "age":                row.get("age")               or str(row.get("Age", "")),
            "fatherOrSpouseName": row.get("fatherOrSpouseName") or row.get("FatherSpouseName", ""),
            "mobile":             row.get("mobile")            or row.get("Mobile", ""),
            "email":              row.get("email")             or row.get("email", ""),
            "adhaar":             row.get("adhaar")            or row.get("AadhaarNumber", ""),
        }

        details = {}
        for k, v in row.items():
            if k in {
                pk_field,
                "SubmissionDateTime",
                "name", "age", "fatherOrSpouseName", "mobile", "email", "adhaar",
                "Status", "status", "statusHistory"
            }:
                continue
            details[k] = v if v is not None else ""
    except Exception as e:
        return jsonify({"error": f"Error processing DB row: {e}"}), 500

    # ── 6) Generate PDF ───────────────────────────────────────────────────────────
    try:
        pdf_buffer = generate_pdf_bytes(form_type, common_fields, details)
    except Exception as e:
        return jsonify({"error": f"PDF generation failed: {e}"}), 500

    # ── 7) Upload PDF to Firebase Storage ────────────────────────────────────────
    try:
        blob.upload_from_file(pdf_buffer, content_type="application/pdf")
        blob.make_public()  # Skip if you want restricted access
        public_url = blob.public_url
    except Exception as e:
        return jsonify({"error": f"Failed to upload PDF to storage: {e}"}), 500

    # ── 8) Return success with URL ───────────────────────────────────────────────
    return jsonify({"download_url": public_url}), 200