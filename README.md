<h1 align="center">
  ❤️🩺 Heart Disease Prediction Web App 🩺❤️
</h1>

<p align="center">
  <img src="https://media.giphy.com/media/hV5mt9FmG4Z5S/giphy.gif" alt="Heartbeat Animation" width="300"/>
</p>

<p align="center">
  A Flask-based web application that predicts the likelihood of heart disease using a machine learning model. Users can create accounts, input their health data, and receive a risk assessment.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/Flask-000000?style=for-the-badge&logo=flask&logoColor=white" alt="Flask">
  <img src="https://img.shields.io/badge/Scikit--learn-F7931E?style=for-the-badge&logo=scikit-learn&logoColor=white" alt="Scikit-learn">
  <img src="https://img.shields.io/badge/SQLAlchemy-D71F00?style=for-the-badge&logo=sqlalchemy&logoColor=white" alt="SQLAlchemy">
   <img src="https://img.shields.io/badge/SQLite-003B57?style=for-the-badge&logo=sqlite&logoColor=white" alt="SQLite">
  <img src="https://img.shields.io/badge/Bootstrap-563D7C?style=for-the-badge&logo=bootstrap&logoColor=white" alt="Bootstrap">
  <img src="https://img.shields.io/badge/HTML5-E34F26?style=for-the-badge&logo=html5&logoColor=white" alt="HTML5">
  <img src="https://img.shields.io/badge/CSS3-1572B6?style=for-the-badge&logo=css3&logoColor=white" alt="CSS3">
</p>

---

## 📖 Table of Contents

- [🌟 About The Project](#-about-the-project)
- [✨ Key Features](#-key-features)
- [🛠️ Technology Stack](#️-technology-stack)
- [🚀 Getting Started](#-getting-started)
  - [Prerequisites](#prerequisites)
  - [Installation & Setup](#installation--setup)
- [📂 Project Structure](#-project-structure)
- [🖼️ Screenshots](#️-screenshots)

---

## 🌟 About The Project

This web application provides users with a tool to assess their potential risk of heart disease based on various health metrics. It utilizes a pre-trained machine learning model (`heart_model.joblib`) integrated into a user-friendly Flask web interface.

Users can register, log in, manage their profile, submit their health data through an assessment form, and view the prediction result along with their submission history on a personal dashboard.

---

## ✨ Key Features

* 👤 **User Authentication:** Secure signup and login functionality.
* 🔒 **Password Hashing:** User passwords are securely hashed before storing.
* 👤 **Profile Management:** Users can view and update their profile information (including profile pictures).
* 📝 **Risk Assessment Form:** Collects relevant health data (age, sex, cholesterol, blood pressure, etc.) needed for prediction.
* 🤖 **ML Prediction:** Uses a `joblib`-saved scikit-learn model and scaler to predict heart disease likelihood based on input data.
* 📊 **Results Display:** Clearly presents the prediction outcome to the user.
* 📈 **Dashboard:** Allows users to view their past assessment results.
* 🎨 **Responsive UI:** Built with Bootstrap for usability across different screen sizes.

---

## 🛠️ Technology Stack

* **Backend:**
    * [Python 3](https://www.python.org/)
    * [Flask](https://flask.palletsprojects.com/) (Web Framework)
    * [Flask-SQLAlchemy](https://flask-sqlalchemy.palletsprojects.com/) (Database ORM)
    * [Flask-Login](https://flask-login.readthedocs.io/) (Session Management)
    * [Flask-Bcrypt](https://flask-bcrypt.readthedocs.io/) (Password Hashing)
    * [Flask-WTF](https://flask-wtf.readthedocs.io/) (Forms Handling)
    * [scikit-learn](https://scikit-learn.org/) (Machine Learning)
    * [Joblib](https://joblib.readthedocs.io/) (Model Loading)
    * [Pandas](https://pandas.pydata.org/) (Data Handling for ML model)
* **Frontend:**
    * HTML5 (via Jinja2 Templates)
    * CSS3
    * JavaScript
    * [Bootstrap](https://getbootstrap.com/)
* **Database:**
    * [SQLite](https://www.sqlite.org/)

---

## 🚀 Getting Started

Follow these instructions to set up and run the project locally.

### Prerequisites

* **Python:** Ensure you have Python 3.x installed. ([Download](https://www.python.org/downloads/))
* **pip:** Python's package installer should be included with your Python installation.
* **(Optional) Virtual Environment:** It's highly recommended to use a virtual environment:
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    ```

### Installation & Setup

1.  **Clone the repository:**
    ```bash
    git clone [https://github.com/vakrahul/heart.git](https://github.com/vakrahul/heart.git)
    cd heart
    ```

2.  **Install Python dependencies:**
    ```bash
    pip install Flask Flask-SQLAlchemy Flask-Login Flask-Bcrypt Flask-WTF scikit-learn joblib pandas Pillow email_validator
    ```
    *(Note: `Pillow` is needed for image handling, `email_validator` for WTForms)*

3.  **Set up Flask Secret Key:**
    * Open `app.py`.
    * Find the line `app.config['SECRET_KEY'] = '...'`.
    * **Replace** the existing placeholder key with your own strong, secret key. You can generate one easily (e.g., using Python's `secrets` module: `python -c 'import secrets; print(secrets.token_hex(16))'`).
        ```python
        # Example: Replace this line in app.py
        app.config['SECRET_KEY'] = 'YOUR_SUPER_SECRET_RANDOM_KEY_HERE'
        ```

4.  **Initialize the Database:**
    * The `database.db` file is included, but if you need to create it from scratch or reset it:
        * Open a Python interpreter in your project directory (with the virtual environment activated).
        * Run the following commands:
            ```python
            from app import app, db, User # Make sure User model is imported in app.py if needed here
            with app.app_context():
                db.create_all()
            exit()
            ```

5.  **Run the Flask Application:**
    ```bash
    flask run
    # Or: python app.py
    ```
    * The application should now be running, typically at `http://127.0.0.1:5000/`.

---

## 📂 Project Structure
