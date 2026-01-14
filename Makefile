.PHONY: requirements run

VENV := venv
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip

# Create virtual environment if it doesn't exist
$(VENV):
	python3 -m venv $(VENV)
	$(PIP) install --upgrade pip

# Generate updated requirements.txt from requirements.in
requirements: $(VENV)
	$(PIP) install pip-tools
	$(VENV)/bin/pip-compile --upgrade requirements.in -o requirements.txt
	$(PIP) install -r requirements.txt

# Start the streamlit portal
run: $(VENV)
	$(PIP) install -r requirements.txt
	$(PYTHON) -m streamlit run portal.py
