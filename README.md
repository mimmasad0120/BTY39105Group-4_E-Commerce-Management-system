# 🍔 Mealzy — Food Delivery Website

**Mealzy** is a food-delivery web application designed to make ordering food simple and convenient. The project combines a user-friendly frontend with a Python Flask backend and a MySQL database.

## 🚀 Features

- User registration and login
- Customer account management
- Food product listings
- Product and order management
- MySQL database integration
- Admin dashboard
- Payment transaction management
- Sample database records
- SQL queries for database inspection and analysis

> Features depend on the functionality currently implemented in the project.

## 🛠️ Technologies Used

- **Frontend:** HTML, CSS, JavaScript
- **Backend:** Python and Flask
- **Database:** MySQL
- **Database Tool:** MySQL Workbench
- **Version Control:** Git and GitHub

## 📁 Project Structure

```text
Mealzy/
│
├── app.py
├── schema.sql
├── .gitignore
├── README.md
│
├── database/
│   ├── mealzy_backup.sql
│   ├── sample_data.sql
│   └── mealzy_queries.sql
│
├── tests/
│   └── test_app_routes.py
│
└── .venv/
```

*Note: The structure above shows the main files; additional frontend files and folders may exist in your project.*

## ⚙️ Installation and Setup

### 1. Clone the Repository

Open your terminal and run:

```bash
git clone https://github.com/mimmasad0120/Mealzy.git
```

Navigate into the project folder:

```bash
cd Mealzy
```

### 2. Create a Virtual Environment

```bash
python -m venv .venv
```

Activate it on Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

### 3. Install Dependencies

Install the packages required by the project.

If a `requirements.txt` file exists, run:

```bash
pip install -r requirements.txt
```

Otherwise, install the dependencies listed in your project's imports.

### 4. Configure MySQL

1. Install MySQL Server and MySQL Workbench.
2. Start MySQL Server.
3. Create the database:

```sql
CREATE DATABASE mealzy_main;
```

4. Configure your database connection settings using your local environment variables.
5. Run the appropriate table-creation SQL script for your database structure.

**Important:** The database schema must match the models and queries used by the Flask application.

### 5. Configure Environment Variables

Create a local `.env` file if your application requires it.

Example:

```env
DB_HOST=localhost
DB_PORT=3306
DB_NAME=mealzy_main
DB_USER=your_mysql_username
DB_PASSWORD=your_mysql_password
```

Use the exact variable names expected by your application. Never upload real passwords, API keys, email credentials, or other secrets to GitHub.

### 6. Run the Application

Activate the virtual environment and run:

```bash
python app.py
```

Open your browser and visit:

```text
http://127.0.0.1:5000
```

The actual address and port depend on your Flask configuration.

## 🗄️ Database Files

The `database/` directory contains SQL resources for working with the Mealzy database.

| File | Description |
|---|---|
| `mealzy_backup.sql` | Database backup |
| `sample_data.sql` | SQL script for inserting sample records |
| `mealzy_queries.sql` | SQL queries for inspecting tables, customers, products, orders, payments, and database relationships |

### Running SQL Files

1. Open MySQL Workbench.
2. Connect to your MySQL Server.
3. Open the required `.sql` file.
4. Review its commands and database requirements.
5. Execute the commands when appropriate.

**Warning:** Backups and sample-data scripts may contain database-specific statements or duplicate existing records. Review them before execution, and back up important data before making changes.

## 🧪 Testing

If the project dependencies are installed and the tests are configured, run:

```bash
python -m pytest
```

## 🔒 Security

- Keep credentials in environment variables.
- Do not publish real customer data.
- Never commit private API keys or passwords.
- Use sanitized sample data when sharing the project.
- Protect database backups containing personal information.
- Configure production security settings before deployment.

## 🌐 GitHub Repository

**Repository:**  
https://github.com/mimmasad0120/Mealzy

## 🎯 Project Goal

The goal of Mealzy is to provide a convenient food-ordering platform with customer management, product listings, order handling, and database-backed functionality.

## 👨‍💻 Author

**Mealzy Project Developer**

GitHub: https://github.com/mimmasad0120

---

*Mealzy — Good Food, Better You.*