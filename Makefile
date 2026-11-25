.PHONY: install build deploy lint test

install :
	@ python -m pip install -e ".[dev]"

build :
	@ rm -rf dist && python -m build

deploy :
	@ twine upload dist/*

lint :
	@ black .

test :
	@ coverage run --branch --source edgeable -m pytest tests -v && coverage report && coverage html
