


### Home
- **GET** `/`
  - Returns a welcome message.

### Email Routes (Prefix: `/email`)
- **POST** `/email/send_email`
  - Sends an email with provided address and message.

### Guards Routes (Prefix: `/guards`)
- **GET** `/guards/`
  - Retrieves all guard records.
- **POST** `/guards/add`
  - Adds a new guard.
- **GET** `/guards/<mobile_number>`
  - Retrieves guard information based on mobile number.

### Users Routes (Prefix: `/users`)
- **POST** `/users/add_user`
  - Adds a new user.
- **POST** `/users/check_user`
  - Checks user credentials for login.

### Verification Routes (Prefix: `/verify`)
- **POST** `/verify/verify_guard`
  - Verifies a guard using emp_id, mobile number, and role.

### Compensation Routes (Prefix: `/compensationform`)
- **POST** `/compensationform`
  - Inserts a new compensation form record.
- **GET** `/compensationform/<string:forest_guard_id>`
  - Retrieves compensation forms for the given ForestGuardID.
- **GET** `/compensationform/<string:role>/<string:emp_id>`
  - Retrieves compensation forms filtered by role and emp_id.

### Complaints Routes (Prefix: `/complaints`)
- **POST** `/complaints/submit_complaint`
  - Submits a new complaint.
- **POST** `/complaints/get_complaint`
  - Retrieves a complaint by complaint_id or mobile number.
- **POST** `/complaints/get_guard_complaints`
  - Retrieves complaints assigned to a guard using guardId.
- **POST** `/complaints/reject_complaint`
  - Allows a guard to reject a complaint (updates status and history).

### Update Form Status Routes (Prefix: `/update_form_status`)
- **POST** `/update_form_status/<int:form_id>`
  - Updates the status of a compensation form (and its associated complaint, if linked) along with its status history.
"""

with open("README.md", "w", encoding="utf-8") as f:
    f.write(readme_content)

print("README.md file has been created/updated.")
