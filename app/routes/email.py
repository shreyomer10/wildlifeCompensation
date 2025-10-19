from flask import Blueprint, request, jsonify
import resend
import os

email_bp = Blueprint('email', __name__)
resend.api_key = os.getenv("RESEND_API_KEY")

@email_bp.route('/send_email', methods=['POST'])
def send_email():
    try:
        data = request.json
        email = data.get("email")
        message = data.get("message")
        if not email or not message:
            return jsonify({"error": "Email and message are required"}), 400
        response = resend.Emails.send({
            "from": "onboarding@resend.dev",
            "to": email,
            "subject": "Regarding Compensation form",
            "html": f"<p>{message}</p>"
        })
        return jsonify({"success": True, "response": response}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
