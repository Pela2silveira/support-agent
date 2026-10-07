SHELL := /bin/bash

.PHONY: help venv install activate clean

VENV_DIR ?= .venv
PYTHON ?= python3

help:
	@echo "Makefile targets:"
	@echo "  venv     - create virtualenv in $(VENV_DIR)"
	@echo "  install  - install pip packages from requirements.txt into $(VENV_DIR)"
	@echo "  activate - print activation command for the venv"
	@echo "  clean    - remove $(VENV_DIR)"

venv:
	@echo "Creating virtual environment in $(VENV_DIR) using $(PYTHON)..."
	@if [ -d "$(VENV_DIR)" ]; then \
		echo "$(VENV_DIR) already exists - skipping creation"; \
	else \
		$(PYTHON) -m venv $(VENV_DIR); \
		echo "Virtual environment created."; \
	fi

install: venv
	@echo "Installing requirements into $(VENV_DIR)..."
	@$(VENV_DIR)/bin/pip install --upgrade pip
	@if [ -f requirements.txt ]; then \
		$(VENV_DIR)/bin/pip install -r requirements.txt; \
		echo "Requirements installed."; \
	else \
		echo "requirements.txt not found, skipping."; \
	fi

activate:
	@echo "To activate the virtualenv, run:"
	@echo "  source $(VENV_DIR)/bin/activate"

clean:
	@echo "Removing $(VENV_DIR)..."
	@rm -rf $(VENV_DIR)
	@echo "Clean complete."
