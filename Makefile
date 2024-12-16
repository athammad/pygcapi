# Variables
PACKAGE_NAME = pygcapi
PYPI_REPOSITORY = pypi
TEST_PYPI_REPOSITORY = testpypi

# Commands
.PHONY: help install-dev test clean build publish publish-test

help:
	@echo "Usage:"
	@echo "  make install_poetry  Install Poetry."
	@echo "  make activate_env    Install the package and development dependencies using Poetry."
	@echo "  make test            Run all tests using Poetry and pytest."
	@echo "  make clean           Remove build artifacts and temporary files."
	@echo "  make install_package Installs the library for local use."
	@echo "  make build           Build the package for distribution."
	@echo "  make publish         Publish the package to PyPI."
	@echo "  make publish-test    Publish the package to Test PyPI."


install_poetry:
	curl -sSL https://install.python-poetry.org | python3 -
	poetry --version

activate_env:
	@echo "Installing dependencies in Poetry's environment..."
	poetry shell
	poetry install

install_package:
	@echo "Installing the library for local use..."
	@pip install -e .


test:
	@echo "Running tests..."
	poetry run pytest

clean:
	@echo "Cleaning build artifacts..."
	rm -rf dist/ build/ *.egg-info
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -exec rm -f {} +

build: clean
	@echo "Building the package..."
	poetry build

publish: build
	@echo "Publishing the package to PyPI..."
	poetry publish --build

publish-test: build
	@echo "Publishing the package to Test PyPI..."
	poetry publish --build --repository $(TEST_PYPI_REPOSITORY)
