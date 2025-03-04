# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'umling'
copyright = '2025, Steven Abney'
author = 'Steven Abney'

version = '0.1'
release = '0.1.8'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.doctest',
]

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

language = 'en'

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']

# -- Doctest -------------------------------------------------------------------

from doctest import ELLIPSIS, IGNORE_EXCEPTION_DETAIL, DONT_ACCEPT_TRUE_FOR_1, NORMALIZE_WHITESPACE
doctest_default_flags = ELLIPSIS | IGNORE_EXCEPTION_DETAIL | DONT_ACCEPT_TRUE_FOR_1 | NORMALIZE_WHITESPACE
