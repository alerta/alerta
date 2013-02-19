from flask import Flask
from flask.ext.pymongo import PyMongo

# Default configuration
MONGO_HOST = 'localhost'
MONGO_PORT = 27017
MONGO_DBNAME = 'monitoring'

app = Flask(__name__)
app.config.from_object(__name__)
mongo = PyMongo(app)


import views
import management.views

