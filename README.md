# Smart Free Time Utilizer - Backend

A Flask-based backend service that leverages Large Language Models (LLMs) to generate personalized productivity and learning recommendations. The system analyzes user preferences, available time, and historical activities to provide relevant and non-repetitive suggestions.

## Features

* User Authentication
* Personalized Activity Generation
* AI-Powered Recommendation Engine
* Activity History Management
* RESTful API Architecture
* MySQL Database Integration
* User Preference Tracking

## Tech Stack

### Backend

* Python
* Flask
* MySQL
* REST APIs

### AI Integration

* OpenRouter API
* Large Language Models (LLMs)

## System Workflow

1. User submits interests and available time.
2. Backend retrieves recent activity history.
3. Context is sent to the LLM.
4. AI generates personalized recommendations.
5. Results are returned and stored for future personalization.

## API Endpoints

### Authentication

```http
POST /signup
POST /signin
```

### Recommendation Engine

```http
POST /api/process-data
```

### Activity History

```http
GET    /api/history/<username>
DELETE /api/history/<username>
```

### Health Check

```http
GET /api/health
```

## Database Schema

### Users

* id
* username
* name
* password

### History

* id
* username
* title
* timestamp

## Project Structure

```text
backend/
├── app.py
├── requirements.txt
├── database/
└── config/
```

## Installation

Create a virtual environment:

```bash
python -m venv venv
```

Activate the environment:

```bash
venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the application:

```bash
python app.py
```

Backend runs at:

```text
http://localhost:5000
```

# To setup the project do the following (In detail):

 ## Run requirements.txt
 ```pip install -r requirements.txt```

## .env should look like  this: 

- OPENROUTER_API_KEY=sk-or-v1-xyzxxxxxxxxxxxxxxxxxxxx
-
- MYSQL_HOST=127.0.0.1
- MYSQL_USER=root
- MYSQL_PASSWORD=password
- MYSQL_DATABASE=smartfreetime
- MYSQL_PORT=3306

## The database should contain the following tables in smartfreetime database:
### DB Commands
```
CREATE DATABASE smartfreetime;

USE smartfreetime;

CREATE TABLE users (
    id INT NOT NULL AUTO_INCREMENT,
    username VARCHAR(80) NOT NULL UNIQUE,
    name VARCHAR(120),
    password VARCHAR(120) NOT NULL,
    PRIMARY KEY (id)
);

CREATE TABLE history (
    id INT NOT NULL AUTO_INCREMENT,
    username VARCHAR(80) NOT NULL,
    title VARCHAR(255) NOT NULL,
    timestamp INT NOT NULL,
    PRIMARY KEY (id),
    INDEX (username)
);

CREATE TABLE ai_history (
id INT AUTO_INCREMENT PRIMARY KEY,
username VARCHAR(100),
user_prompt TEXT,
ai_response LONGTEXT,
created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```
```
mysql> desc history;
+-----------+--------------+------+-----+---------+----------------+
| Field     | Type         | Null | Key | Default | Extra          |
+-----------+--------------+------+-----+---------+----------------+
| id        | int          | NO   | PRI | NULL    | auto_increment |
| username  | varchar(80)  | NO   | MUL | NULL    |                |
| title     | varchar(255) | NO   |     | NULL    |                |
| timestamp | int          | NO   |     | NULL    |                |
+-----------+--------------+------+-----+---------+----------------+
4 rows in set (0.02 sec)
```

```
mysql> desc users;
+----------+--------------+------+-----+---------+----------------+
| Field    | Type         | Null | Key | Default | Extra          |
+----------+--------------+------+-----+---------+----------------+
| id       | int          | NO   | PRI | NULL    | auto_increment |
| username | varchar(80)  | NO   | UNI | NULL    |                |
| name     | varchar(120) | YES  |     | NULL    |                |
| password | varchar(120) | NO   |     | NULL    |                |
+----------+--------------+------+-----+---------+----------------+
4 rows in set (0.01 sec)
```
## Use follwing commands to run the code
use this command to run backend:
```python app.py```

use this command to run frontend:
```npm run dev```


***Note:*** Don't forget to add your own Openrouter API Key

## Future Enhancements

* User Goal Management
* Calendar Integration
* Multi-Model AI Support
* Analytics Dashboard
* Personalized Learning Paths

