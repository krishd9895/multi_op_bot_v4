from flask import Flask
from threading import Thread
import logging

app = Flask(__name__)

@app.route('/')
def home():
    return "running."

# Start Flask web server
def run_flask():
    app.run(host='0.0.0.0', port=5018)
