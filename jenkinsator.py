#!/usr/bin/python
from __future__ import absolute_import, print_function

import sys
import netrc
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


def url_to_host(url):
    return url.replace("http://", "").replace("https://", "")


def connect(url, login, password):
    if not login and not password:
        host = url_to_host(url)
        try:
            secrets = netrc.netrc()
            secret = secrets.authenticators(host)
        except IOError:
            print("Please, provide login and password as parameters "
                  "or put them to .netrc file as default values for the host:", host)
            secret = None

        if secret is None:
            return None

        login, _, password = secret

    return jenkins_api.Jenkins(url, login, password)


def validate_params(params):
    if args.replace and not params.name and not params.from_file:
        print("Please, provide job name ('--job') or file with job names ('--jobs-file')")
        return False

    if params.name and params.from_file:
        print("Using '--job' and '--jobs-file' at the same time is not supported")
        return False

    if args.dump_to_file and (not params.name or params.from_file):
        print("`--dump-to-file` can be used only with `--name`")
        return False

    if args.create_from_file and (not params.name or params.from_file):
        print("`--create-from-file` can be used only with `--name`")
        return False

    return True


def main(args):
    jenkins = connect(args.jenkins, args.login, args.password)
    if not jenkins:
        return 1

    print("Succesfully connected to %s." % args.jenkins, "Version is", jenkins.get_version())

    if args.action == "job":
        process_jobs(jenkins, args)

    return 0


def process_jobs(jenkins, args):
    jobs = None
    if args.name:
        jobs = [args.name]

    if args.from_file:
        jobs = get_job_list(args.from_file)

    if args.replace:
        for job in jobs:
            try:
                config = jenkins.get_job_config(job)
            except jenkins_api.NotFoundException:
                print("Can't find the job:", job)
                continue

            if args.replace:
                new_config = replace(args.replace, config)
                if config == new_config:
                    print("Config was not changed for the job:", job)
                else:
                    if not args.dry_run:
                        jenkins.reconfig_job(job, new_config)
                    print("Config was updated for the job:", job)
    elif args.dump_to_file:
        if not args.dry_run:
            with open(args.dump_to_file, "w") as f:
                f.write(config)
            print("Job `%s` was dumped to the file: %s" % (args.name, args.dump_to_file))
    elif args.create_from_file:
        with open(args.create_from_file) as f:
            if not args.dry_run:
                jenkins.create_job(args.name, f.read())
            print("Job `%s` was created from the file: %s" % (args.name, args.create_from_file))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Jenkinsator helps to orchestrate Jenkins master')
    parser.add_argument(dest="jenkins", action="store", help="Jenkins master [full url]")
    parser.add_argument('--login', help="login to access Jenkins [INSECURE - use .netrc]")
    parser.add_argument('--password', help="password to access Jenkins [INSECURE - use .netrc]")
    parser.add_argument('--dry-run', action="store_true", help="do not perform any action")

    subparsers = parser.add_subparsers(title='Actions', dest="action")
    job_parser = subparsers.add_parser("job")
    job_parser.add_argument('--from-file',
                            help="file to retrive the list of jobs to be processed [one per line]")
    job_parser.add_argument('--name', help="job to be processed [full name]")
    job_parser.add_argument('--replace',
                            help="use {0} to split original value and desired one, i.e."
                            "`aaa{0}bbb` replaces all occurances of `aaa` by `bbb`".
                            format(REPLACE_SPLITTER))
    job_parser.add_argument('--dump-to-file', help="dump job configuration to the file")
    job_parser.add_argument('--create-from-file', help="create the job from configuration file")
    args = parser.parse_args()

    if not validate_params(args):
        sys.exit(1)

    sys.exit(main(args))
