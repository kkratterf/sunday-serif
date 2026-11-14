# Sunday Serif. `make` builds everything into fonts/; `make test` runs fontbakery.
# Needs uv (https://docs.astral.sh/uv/), which also fetches Python 3.12.
PY := .venv/bin/python
QA := .venv-qa/bin/fontbakery

.PHONY: all venv build variable test npm clean

all: build

venv: .venv/.ok .venv-qa/.ok

.venv/.ok: requirements.txt
	uv venv -q --allow-existing --python 3.12 .venv
	uv pip install -q --python .venv -r requirements.txt
	touch $@

.venv-qa/.ok: requirements-qa.txt
	uv venv -q --allow-existing --python 3.12 .venv-qa
	uv pip install -q --python .venv-qa -r requirements-qa.txt
	touch $@

build: .venv/.ok
	$(PY) scripts/build.py

# Only the two variable fonts and their WOFF2: quick check while editing sources.
variable: .venv/.ok
	$(PY) scripts/build.py --only-variable

test: .venv-qa/.ok
	mkdir -p build/fontbakery
	$(QA) check-universal fonts/variable/*.ttf -l FAIL --succinct --html build/fontbakery/variable.html
	$(QA) check-universal fonts/ttf/*.ttf -l FAIL --succinct --html build/fontbakery/static.html

# The `sunday-serif` npm package in build/npm (after `make build`).
npm: .venv/.ok
	$(PY) scripts/npm_package.py

clean:
	rm -rf build fonts
