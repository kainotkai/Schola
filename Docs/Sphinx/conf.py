# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'Schola'
copyright = '2023-2024, Advanced Micro Devices Inc.'
author = 'Advanced Micro Devices'

import sys
import os
sys.path.insert(0, os.path.abspath("../../Resources/python"))
sys.path.append(os.path.abspath("./_ext"))


# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.viewcode',
    'sphinx.ext.autosummary',
    'sphinx.ext.napoleon',
    'sphinx_tabs.tabs',
    'sphinx.ext.intersphinx',
    'sphinx_copybutton',
    'sphinx.ext.autosectionlabel', 
    'argparseautodoc.ext',
    'breathe',
    "blueprint",
    "localref"
]

autosectionlabel_prefix_document = True

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

language = 'en'

#code highlighting
pygments_style = 'sphinx'

# Generate the API documentation when building
autosummary_generate=True

# -- Options for autodoc extension -------------------------------------------
autodoc_typehints = "description"

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "sphinx_rtd_theme"
html_static_path = ['_static']
html_logo = './_static/AMD_Schola_Lockup_RGB_Blk.png'
html_css_files = ['schola_theme.css']
html_favicon = "./_static/icon.png"

# disable index page
html_domain_indices = False

html_theme_options = {
    # Toc options
    'collapse_navigation': False,
    'sticky_navigation': True,
    'navigation_depth': 5,
    'includehidden': True,
    'titles_only': False,
    'logo_only': True,
}


# -- Options for todo extension ----------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/extensions/todo.html#configuration

todo_include_todos = True

# -- Options for breathe extension -------------------------------------------
# https://breathe.readthedocs.io/en/latest/directives.html#config-values

# most of these are set to the defaults but exposed here to make it easier to track
#breathe_build_directory= ...
breathe_implementation_filename_extensions = ['.c', '.cc', '.cpp']
breathe_show_define_initializer = True
breathe_show_enumvalue_initializer = True
breathe_show_include = True
breathe_projects = {
    "Schola" : "../Doxygen/xml"
}
breathe_default_project="Schola"
#Make the doxygen classes actually display things
breathe_default_members = ('members', 'undoc-members')

# -- Options for sphinx_tabs extension ---------------------------------------
sphinx_tabs_disable_tab_closing = True

# -- Options for intersphinx extension ---------------------------------------
intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None), 
    'ray': ('https://docs.ray.io/en/master/', None),
    'gym': ('https://gymnasium.farama.org/', None),
    'stable_baselines3': ('https://stable-baselines3.readthedocs.io/en/master/', None)
    }

# -- Options for blueprints extension -----------------------------------------
blueprint_dir = './blueprints'