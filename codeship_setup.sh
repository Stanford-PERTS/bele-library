#!/bin/bash

# Commands to be run during a codeship build of the Mindset Kit.
# In a codeship project, in the Setup Commands window, enter this:

# chmod +x codeship_setup.sh && ./codeship_setup.sh

# Run a custom python script to compile branch-specific config files.
pip install --user 'ruamel.yaml<0.15'
python branch_environment.py

# Compass is a Ruby program that handles compilation of CSS languages,
# e.g. SASS
gem install compass

# Bower is a node package that organizes javascript libraries, e.g. jQuery
npm install bower

# Grunt runs a variety of tasks on our static resources
npm install grunt-cli

# This installs the grunt packages listed in packages.json
npm install

# This installs the javascript libraries listed in bower.json
bower install

# This executes all the grunt tasks, e.g. minification
grunt build
