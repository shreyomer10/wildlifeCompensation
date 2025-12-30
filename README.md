<p align="center">
  <img src="./logo.png" alt="Anugrah Backend Logo" width="140"/>
</p>

<h2 align="center">🌲 Anugrah – Forest Compensation Backend API</h2>

<p align="center">
<b>Secure • Scalable • AI-Assisted</b>
</p>

The **Anugrah Backend** is a **Flask-based REST API** that powers the **mobile application and web dashboard** for managing forest compensation cases arising from human–wildlife conflicts.

It handles **authentication, form processing, verification workflows, analytics, AI-based similarity detection, and document generation**, serving as the core system of the Anugrah platform.

---

## 🧩 System Role

This backend acts as the **single source of truth** for:
- Compensation forms lifecycle
- Role-based access & verification
- AI-assisted fraud detection
- Analytics & reporting
- PDF generation and notifications

It integrates with:
- 📱 Android Mobile App
- 🌐 Web Dashboard
- 🤖 AI similarity detection pipeline
---

## 🚀 Key Features

- 🔐 **Authentication & Authorization**
  - Role-based access (fg,d.ranger,ranger,sdo,dfo ccf,PCCF)
  - Token-based authentication
  - Secure password hashing (bcrypt)

- 🧾 **Compensation Form Management**
  - Create, update, verify compensation forms
  - Maintain complete status timeline
  - Prevent duplicate submissions

- 🧠 **AI-Based Similarity Detection**
  - ONNX-based embedding model
  - Detects similar historical compensation forms
  - Flags suspicious or repeated claims

- 📊 **Analytics APIs**
  - Day-wise / month-wise claim peaks
  - Region-wise analytics
  - Admin dashboards support

- 📄 **PDF Generation**
  - Auto-generated compensation PDFs
  - Backend-controlled formatting & data consistency

- ⚡ **Rate Limiting & Security**
  - Flask-Limiter integration
  - Redis-backed rate limiting
  - CORS-controlled access

---

## 🛠 Tech Stack

### Backend
- **Framework:** Flask
- **Language:** Python 3.x
- **API Style:** REST
- **ORM / DB Connector:** MySQL Connector
- **Caching / Rate Limit:** Redis + Flask-Limiter
- **Auth & Security:** bcrypt, token validation

### AI / ML
- **Model Format:** ONNX
- **Embedding Pipeline:** Custom similarity scoring
- **Vector Store:** Pinecone (via utils)

### Infrastructure
- **Containerization:** Docker
- **Deployment Ready:** Gunicorn-compatible
- **CORS:** Flask-CORS

---

## ⚙️ Installation & Setup

### 1️⃣ Clone the repository
```bash
git clone https://github.com/shreyomer10/wildlifeCompensation.git
cd wildlifeCompensation
```

### 2️⃣ Create virtual environment
```bash
python -m venv venv
source venv/bin/activate      # Linux / Mac
venv\Scripts\activate         # Windows
```

### 3️⃣ Install dependencies
```bash
pip install -r requirements.txt
```

### 4️⃣ Environment Configuration
```bash
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=yourpassword
DB_NAME=compensation_db

REDIS_URL=redis://localhost:6379

JWT_SECRET=your_secret_key
```

### 5️⃣ Start Redis (required)
```bash
redis-server
```

### 6️⃣ Run the backend
```bash
python backend.py
```

---

## 🔗 Related Repositories
- **APP:** [Github](https://github.com/shreyomer10/COMPENSATION_APP)
- **Web Dashboard:** [Anugrah](https://anugraha-nine.vercel.app/)

---


## 👥 Team Members
- **Shrey Omer**  
- **Sujal Goel**  
- **Chetankumar S. Majjagi**

