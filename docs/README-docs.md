# docs

The HTML pages are in _build/html.
Documentation setup complete!
To view documentation:
  cd docs
  python -m http.server 8000 --directory _build/html
  Then open http://localhost:8000 in your browser
To rebuild documentation after changes:
  cd docs && make html