#!/bin/bash

if [ -d "venv" ]; then
    echo "Directory 'env' already exists."
else 
    python3 -m venv venv
fi
source venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt
python -m streamlit run portal.py