from flask import Flask
import mysql.connector
from flask_mail import Mail
import os

app = Flask(__name__)

app.secret_key = 'HELLO YOUR GAMBAYOUTAR HAS VIRUS'

app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'sari'
app.config['MYSQL_PASSWORD'] = 'Sari@Itani101'
app.config['MYSQL_DATABASE'] = 'VET'

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'sariitani101@gmail.com'
app.config['MAIL_PASSWORD'] = 'iozdolwpaiushskt'
app.config['MAIL_DEFAULT_SENDER'] = 'sariitani101@gmail.com'

mail = Mail(app)

def get_db_connection():
    return mysql.connector.connect(
        host=app.config['MYSQL_HOST'],
        user=app.config['MYSQL_USER'],
        password=app.config['MYSQL_PASSWORD'],
        database=app.config['MYSQL_DATABASE']
    )

from vet_app import views
