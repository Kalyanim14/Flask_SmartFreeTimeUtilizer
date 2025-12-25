# To setup the project do the following:

 ## Run requirements.txt
 ```pip install -r requirements.txt```

## .env should look like  this: 

- OPENROUTER_API_KEY=sk-or-v1-xyzxxxxxxxxxxxxxxxxxxxx
-
- MYSQL_HOST=127.0.0.1
- MYSQL_USER=root
- MYSQL_PASSWORD=sharvan8
- MYSQL_DATABASE=smartfreetime
- MYSQL_PORT=3306

## The database should contain the following tables in smartfreetime database:

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
*** Note: *** Don't forget to add your own Openrouter API Key
