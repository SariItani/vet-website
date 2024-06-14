-- Database creation
CREATE DATABASE IF NOT EXISTS VET;

USE VET;

-- Create Users table
CREATE TABLE IF NOT EXISTS Users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    email_verified_at TIMESTAMP NULL,
    verified BOOLEAN DEFAULT FALSE,
    verification_token VARCHAR(255) DEFAULT NULL,
    reset_token VARCHAR(255),
    profile_picture VARCHAR(255)
);

-- Create Pets table
CREATE TABLE IF NOT EXISTS Pets (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    name VARCHAR(255) NOT NULL,
    type VARCHAR(255) NOT NULL,
    FOREIGN KEY (user_id) REFERENCES Users(id) ON DELETE CASCADE
);

-- Create Vaccines table
CREATE TABLE IF NOT EXISTS Vaccines (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT
);

-- Create pet_vaccines table
CREATE TABLE IF NOT EXISTS pet_vaccines (
    id INT AUTO_INCREMENT PRIMARY KEY,
    pet_id INT NOT NULL,
    vaccine_name VARCHAR(255) NOT NULL,
    vaccination_date DATE,
    FOREIGN KEY (pet_id) REFERENCES Pets(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS Employees (
    id INT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL
);

-- Insert root user
INSERT IGNORE INTO Employees (email, password, role) VALUES ('sariitani101@gmail.com', 'pbkdf2:sha256:600000$SnxWh1jlhzN8hqge$4ff5768ff9805cfb1a246b46baeb01ad8ac567e762ec39275e1b998747ec87e1', 'admin');

-- Insert popular vaccines
INSERT INTO Vaccines (name, description) VALUES
('Rabies', 'Rabies vaccine for pets'),
('Canine Distemper', 'Canine Distemper vaccine'),
('Parvovirus', 'Parvovirus vaccine for dogs'),
('Adenovirus', 'Adenovirus vaccine for dogs'),
('Parainfluenza', 'Parainfluenza vaccine for dogs'),
('Leptospirosis', 'Leptospirosis vaccine for pets'),
('Feline Herpesvirus', 'Feline Herpesvirus vaccine'),
('Calicivirus', 'Calicivirus vaccine for cats'),
('Feline Panleukopenia', 'Feline Panleukopenia vaccine'),
('Feline Leukemia', 'Feline Leukemia vaccine');
