# 🏠 Blissful Home Service (BHS)

> A Python/Flask web application implementing a three-tier role system **(Customer · Professional · Admin)** for end-to-end home service management, including service discovery, a complete booking lifecycle, and an analytical summary dashboard.

**Academic Context:** Developed as part of the **Modern Application Development 1 (MAD 1)** course for the **IIT Madras BS Degree Program**.

---

## 📋 Features

### 🛡️ Admin Control Panel
- Oversee the entire platform from a central dashboard
- Approve or block Service Professionals and Customers
- Create, edit, and manage service categories
- View platform-wide analytical summaries and activity charts

### 👷 Professional Portal
- Receive, accept, or reject incoming service requests
- Manage profile and documents (e.g., experience, service type)
- Track ongoing and completed jobs via a personal dashboard

### 👤 Customer Experience
- Browse and search for available home services
- Book verified professionals based on service category
- Track the full lifecycle of service requests (pending → accepted → closed)
- Rate and review completed services

---

## 🛠️ Tech Stack

| Layer       | Technology                                      |
|-------------|------------------------------------------------|
| Backend     | Python 3, Flask 3.0                            |
| Auth        | Flask-Login 0.6                                |
| Database    | SQLite via Flask-SQLAlchemy                    |
| Frontend    | HTML5, CSS3, Jinja2 Templating                 |
| Charts      | Matplotlib (server-side plot generation)       |

---

## 🚀 Local Setup & Installation

### 1. Clone the repository
```bash
git clone https://github.com/AbhiharRathore/BlissFullHomeService.git
cd BlissFullHomeService
```

### 2. Create and activate a virtual environment
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Run the application
```bash
python app.py
```

The app will start at: **http://127.0.0.1:5010**

---

## 🔑 Default Admin Credentials

On first run, an admin account is automatically seeded:

| Field    | Value      |
|----------|------------|
| Username | `admin`    |
| Password | `admin123` |

> ⚠️ Change this password immediately in a production environment.

---

## 📁 Project Structure

```
BHS/
├── app.py                  # Application entry point
├── requirements.txt        # Python dependencies
├── .gitignore
└── PROJECT/
    ├── __init__.py         # App factory & configuration
    ├── models.py           # Database models (User, Admin, Professional, Service, Booking)
    ├── auth.py             # Authentication blueprint (login, signup, logout)
    ├── main.py             # Main blueprint (dashboards, bookings, admin routes)
    ├── plot.py             # Chart/plot generation
    ├── Static/
    │   ├── images/         # Static images & logo
    │   ├── plots/          # Generated chart images
    │   └── style/          # CSS stylesheets
    └── Templates/          # Jinja2 HTML templates
        ├── base.html
        ├── home.html
        ├── admin_dashboard.html
        ├── professional_dashboard.html
        ├── user_dashboard.html
        └── ...             # Other templates
```

---

## 📄 License

This project was created for academic purposes under the IIT Madras BS Degree Program.
