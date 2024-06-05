-- Database creation
CREATE DATABASE IF NOT EXISTS VET;

USE VET;

-- Create Users table
CREATE TABLE IF NOT EXISTS Users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    email_verified_at TIMESTAMP NULL
);

-- Create Pets table
CREATE TABLE IF NOT EXISTS Pets (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    name VARCHAR(255) NOT NULL,
    type VARCHAR(255) NOT NULL,
    age INT,
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
    vaccine_id INT NOT NULL,
    vaccination_date DATE,
    FOREIGN KEY (pet_id) REFERENCES Pets(id) ON DELETE CASCADE,
    FOREIGN KEY (vaccine_id) REFERENCES Vaccines(id) ON DELETE CASCADE
);
