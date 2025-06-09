# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
import os
import sys
sys.path.insert(0, os.path.abspath('../src'))

# -- Project information -----------------------------------------------------

project = 'LLM Agent Framework'
copyright = '2024, Your Name'
author = 'Your Name'

# The full version, including alpha/beta/rc tags
release = '1.0.0'

# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    'sphinx.ext.autodoc',       # Auto-generate docs from docstrings
    'sphinx.ext.viewcode',      # Add source code links
    'sphinx.ext.napoleon',      # Support Google/NumPy style docstrings
    'sphinx.ext.intersphinx',   # Link to other documentation
    'sphinx.ext.autosummary',   # Generate summary tables
    'sphinx.ext.githubpages',   # Publish to GitHub Pages
]

# Napoleon settings for Google-style docstrings
napoleon_google_docstring = True
napoleon_numpy_docstring = True
napoleon_include_init_with_doc = False
napoleon_include_private_with_doc = False
napoleon_include_special_with_doc = True
napoleon_use_admonition_for_examples = False
napoleon_use_admonition_for_notes = False
napoleon_use_admonition_for_references = False
napoleon_use_ivar = False
napoleon_use_param = True
napoleon_use_rtype = True
napoleon_preprocess_types = False
napoleon_type_aliases = None
napoleon_attr_annotations = True

# Autodoc settings
autodoc_default_options = {
    'members': True,
    'undoc-members': False,
    'show-inheritance': True,
    'special-members': '__init__',
    'exclude-members': '__weakref__'
}

# Don't show full module paths
add_module_names = False

# Autosummary settings
autosummary_generate = True
autosummary_imported_members = False

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store', 'modules.rst']

# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.
html_theme = 'sphinx_rtd_theme'

# Theme options are theme-specific and customize the look and feel of a theme
# further.
html_theme_options = {
    'collapse_navigation': False,
    'sticky_navigation': True,
    'navigation_depth': 4,
    'includehidden': True,
    'titles_only': False
}

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

# Create _static directory if it doesn't exist
os.makedirs('_static', exist_ok=True)

# -- Cross-reference configuration -------------------------------------------

# Configure cross-reference resolution to avoid duplicate warnings
nitpicky = False
nitpick_ignore = [
    ('py:class', 'EmbeddingsManager'),
    ('py:class', 'Optional'),
    ('py:class', 'List'),
    ('py:class', 'Dict'),
    ('py:class', 'Tuple'),
    ('py:class', 'Any'),
]

# Suppress duplicate object description warnings
suppress_warnings = [
    'autosummary.import_cycle',
    'autodoc.import_object'
]

# Intersphinx mapping to external documentation
intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
    'numpy': ('https://numpy.org/doc/stable/', None),
}

# -- Custom configuration ----------------------------------------------------

# Source code encoding
source_suffix = '.rst'

# Master document
master_doc = 'index'

# Language
language = 'en'

# Pygments style for syntax highlighting
pygments_style = 'sphinx'

# Output file base name for HTML help builder
htmlhelp_basename = 'LLMAgentFrameworkdoc'
