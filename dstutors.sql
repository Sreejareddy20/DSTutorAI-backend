-- Create the database
CREATE DATABASE IF NOT EXISTS dstutorial;

-- Use the database
USE dstutorial;

-- Create the users table
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert a test user for verification
-- Email: test@example.com, Password: password123
INSERT IGNORE INTO users (email, password) VALUES ('test@example.com', 'password123');
