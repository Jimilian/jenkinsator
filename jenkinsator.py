#!/usr/bin/python
from __future__ import absolute_import, print_function

import sys
import argparse

try:
    import jenkins as jenkins_api
except ImportError as e:
    no_module_error = "No module named "
    if(e.message.startswith(no_module_error)):
        module_name = e.message[len(no_module_error):]
        if module_name == "jenkins":
            module_name = "python-jenkins"
        print(e)
        print("Please, install it via: sudo python -m pip install", module_name)
        sys.exit(1)
    else:
        raise e


REPLACE_SPLITTER = "#"


def get_job_list(job_file):
    jobs = set()
    for line in open(job_file):
        l = line.strip().replace("\n", "")
        if l:
            jobs.add(l)
    return jobs


def replace(options, input_string):
    orig, target = options.split(REPLACE_SPLITTER)
    return input_string.replace(orig, target)


def connect(url, login, password):
    return jenkins_api.Jenkins(url, login, password)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Jenkinsator helps to orchestrate Jenkins master')
    parser.add_argument(dest="jenkins", action="store", help="Jenkins master [full url]")
    parser.add_argument('--login', help="login to access Jenkins master")
    parser.add_argument('--password', help="password to access Jenkins master")
    parser.add_argument('--jobs-file',
                        help="file to retrive the list of jobs to be processed [one url per line]")
    parser.add_argument('--job', help="job to be processed [full path]")
    parser.add_argument('--replace', help="use {0} to split original value and desired one, i.e. "
                                          "`aaa{0}bbb` replaces all occurances of `aaa` by `bbb`".
                                          format(REPLACE_SPLITTER))
    parser.add_argument('--dry-run', action="store_true", help="do not perform any action")
    args = parser.parse_args()

    if args.job and args.jobs_file:
        print("Using '--job' and '--jobs-file' at the same time is not supported")
        sys.exit(1)

    jobs = None
    if args.job:
        jobs = [args.job]

    if args.jobs_file:
        jobs = get_job_list(args.jobs_file)

    if not jobs:
        print("Please, provide job name ('--job') or file with job names ('--jobs-file')")
        sys.exit(1)

    jenkins = connect(args.jenkins, args.login, args.password)
    if not jenkins:
        sys.exit(1)

    print("Succesfully connected to %s." % args.jenkins, "version is", jenkins.get_version())

    for job in jobs:
        config = jenkins.get_job_config(job)
        if args.replace:
            new_config = replace(args.replace, config)
            if config == new_config:
                print("Config was not changed for the job:", job)
            else:
                if not args.dry_run:
                    jenkins.reconfig_job(job, new_config)
                print("Config was updated for the job:", job)

    exit(0)
