from flask import Flask, request

app = Flask(__name__)
from app import api

if __name__ == '__main__':
    app.run(debug=True)