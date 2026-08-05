CREATE TABLE IF NOT EXISTS tasks (
  id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  username VARCHAR(80) NOT NULL,
  title VARCHAR(255) NOT NULL,
  description TEXT,
  skill VARCHAR(100) NOT NULL DEFAULT 'General',
  status ENUM('pending','progressing','done','rejected') NOT NULL DEFAULT 'pending',
  due_at DATETIME NULL,
  reminder_at DATETIME NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  completed_at DATETIME NULL,
  INDEX tasks_username_status (username, status),
  INDEX tasks_reminder (username, reminder_at)
);
