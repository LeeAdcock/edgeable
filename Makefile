.PHONY: build deploy

build :
	@ python setup.py build_py sdist

deploy :
	@ twine upload dist/*

lint :
	@ black **/*.py 

test :
	@ coverage run --branch --source edgeable -m pytest ./tests/test_*.py -s -v && coverage report && coverage html