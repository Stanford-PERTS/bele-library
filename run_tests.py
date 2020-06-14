import unittest
import ruamel.yaml
import sys
import os

# PERTS code expects this to be set so we can detect localhost
# or production. See util.is_localhost().
# http://stackoverflow.com/questions/1916579/in-python-how-can-i-test-if-im-in-google-app-engine-sdk
os.environ['SERVER_SOFTWARE'] = 'Development/X.Y'

# Read through app.yaml and set an environment variables that are present.
with open('app.yaml', 'r') as file_handle:
    # Read as a dictionary.
    app_yaml = ruamel.yaml.load(file_handle.read())
    for key, value in app_yaml['env_variables'].items():
        os.environ[key] = value

# Don't actually know what this does. Got it from here:
# https://cloud.google.com/appengine/docs/python/tools/localunittesting?hl=en#Python_Setting_up_a_testing_framework
sys.path.insert(0, '/home/rof/appengine/python_appengine')
# sys.path.insert(0, '/usr/local/google_appengine')  # local testing
import dev_appserver
dev_appserver.fix_sys_path()

# Check the unit_testing folder for test definitions.
suite = unittest.loader.TestLoader().discover('unit_testing')
test_result = unittest.TextTestRunner(verbosity=2).run(suite)

# The wasSuccessful function doesn't do exactly what you expect. It
# returns True even if there are unexpected successes. Fix it.
# https://docs.python.org/2/library/unittest.html#unittest.TestResult
success = (test_result.wasSuccessful() and
           len(test_result.unexpectedSuccesses) is 0)

# This part is essential for communicating to codeship's build process. It will
# stop the build--and stop short of deployment!--if any of the commands run
# during the build return an exit code of 1, which indicates an error.
# Although the TextTestRunner does stream to stderr when there are failures, it
# does NOT exit with code 1 on its own. Do that here.
sys.exit(0 if success else 1)
