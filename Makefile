.PHONY: build deploy

build :
	@ python setup.py build_py sdist

deploy :
	@ twine upload dist/*