from flask import Flask
import mysql.connector

app = Flask(__name__)

app.secret_key = 'HELLO YOUR GAMBAYOUTAR HAS VIRUS'

app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'sari'
app.config['MYSQL_PASSWORD'] = 'Sari@Itani101'
app.config['MYSQL_DATABASE'] = 'VET'

def get_db_connection():
    return mysql.connector.connect(
        host=app.config['MYSQL_HOST'],
        user=app.config['MYSQL_USER'],
        password=app.config['MYSQL_PASSWORD'],
        database=app.config['MYSQL_DATABASE']
    )

from vet_app import views
