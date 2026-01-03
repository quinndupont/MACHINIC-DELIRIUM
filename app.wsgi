#!/usr/bin/env python3
"""
WSGI entry point for Apache/mod_wsgi deployment on NearlyFreeSpeech
"""
import sys
import os

# Add the project directory to the Python path
project_dir = os.path.dirname(os.path.abspath(__file__))
if project_dir not in sys.path:
    sys.path.insert(0, project_dir)

# Change to the project directory
os.chdir(project_dir)

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

# Import the Flask application
from app import app as application

if __name__ == "__main__":
    application.run()

