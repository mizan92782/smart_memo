#!/bin/bash
# Unset system DEBUG variable that conflicts with .env
unset DEBUG
# Activate virtual environment and run server
source venv/bin/activate
python manage.py runserver
