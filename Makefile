.PHONY: install scrape brains analyze heatmaps site deploy all clean

VENV := venv
PY := $(VENV)/bin/python
PIP := $(VENV)/bin/pip

install:
	$(PIP) install playwright
	$(VENV)/bin/playwright install chromium

# --- Pipeline stages (run in order) ---

scrape:
	$(PY) scripts/scrape_collectr.py

# LIMIT=3 for a quick smoke test: make brains LIMIT=3
brains:
	$(PY) scripts/run_brain_inference.py $(if $(LIMIT),--limit $(LIMIT))

analyze:
	$(PY) scripts/analyze.py

heatmaps:
	$(PY) scripts/render_heatmaps.py

site:
	$(PY) scripts/build_site.py

all: scrape brains analyze heatmaps site

# --- Deploy ---

deploy:
	npx wrangler pages deploy site --project-name pokemon-brain-predictor

# --- Maintenance ---

clean:
	rm -rf data/cards/* data/image_videos/* data/brain/* site/index.html site/assets/heatmaps/* site/assets/cards/*

clean-site:
	rm -rf site/index.html site/assets/heatmaps/* site/assets/cards/*
