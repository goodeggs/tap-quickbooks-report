isort:
	isort --recursive

flake8:
	flake8 . --ignore=E501,E722 --count --statistics
