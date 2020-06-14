"""Process the branch_environment.json file to create other config files
(e.g. app.yaml) from templates as appropriate for the current branch."""


import json
import os
import re
# preferred over pyyaml b/c it preserves comments,
# see http://stackoverflow.com/questions/7255885/save-dump-a-yaml-file-with-comments-in-pyyaml
import ruamel.yaml


def main():
    with open('branch_environment.json', 'r') as file_handle:
        branch_environments = json.loads(file_handle.read())
        # The CI_BRANCH environment variable should be set if we are in a
        # codeship build environment.
        branch = os.environ.get('CI_BRANCH', None)
        if not branch:
            # Otherwise, try to get it from local git.
            stream = os.popen("git rev-parse --abbrev-ref HEAD")
            branch = stream.read().strip()
            stream.close()
        if not branch:
            # If it's still not defined, stop to debug.
            raise Exception("Branch could not be determined.")

        # Look up the part of the configuration for this branch. If this
        # branch isn't in the conf, default to dev.
        branch = branch if branch in branch_environments else 'dev'
        conf = branch_environments[branch]

    # Process the app.yaml part of the environment config.
    file_conf = conf['app.yaml']

    with open('app.yaml.template', 'r') as file_handle:
        # Read as a string since we don't care about semantics.
        app_yaml_str = file_handle.read()

    # Loop through values to interpolate
    for k, v in file_conf.items():
        regex = re.compile(r'\$\{' + k + r'\}')
        app_yaml_str = regex.sub(v, app_yaml_str)

    # Write an app.yaml file that App Engine can use.
    with open('app.yaml', 'w') as file_handle:
        file_handle.write(app_yaml_str)

    # Also write environment information to disk so we can customize the
    # deploy script. See codeship_deploy.sh in your project.
    is_codeship = os.environ.get('CI', None) == 'true'
    if is_codeship:
        with open('project_id.txt', 'w') as file_handle:
            file_handle.write(file_conf['PROJECT_ID'])
        with open('app_engine_version.txt', 'w') as file_handle:
            file_handle.write(file_conf['APP_ENGINE_VERSION'])

    # Process the cron.yaml part of the environment config.
    file_conf = conf['cron.yaml']

    with open('cron.yaml.template', 'r') as file_handle:
        # Read as a dictionary since we DO care about semantics.
        cron_yaml = ruamel.yaml.load(file_handle.read(),
                                     ruamel.yaml.RoundTripLoader)

        # Determine which of the available cron jobs to use.
        if '_all' in file_conf:
            if file_conf['_all']:
                enabled_jobs = cron_yaml['cron']  # use all jobs
            else:
                enabled_jobs = []  # use no jobs
        else:
            enabled = lambda cron_job: True if cron_job['url'] in file_conf.keys() else False
            enabled_jobs = [job for job in cron_yaml['cron'] if enabled(job)]

        # Overwrite existing jobs with those we've chosen.
        cron_yaml['cron'] = enabled_jobs

    # Write an cron.yaml file that App Engine can use.
    with open('cron.yaml', 'w') as file_handle:
        file_handle.write(ruamel.yaml.dump(
            cron_yaml, Dumper=ruamel.yaml.RoundTripDumper))


if __name__ == "__main__":
    print "branch_environment.py building various config files..."
    main()
    print "...success"
