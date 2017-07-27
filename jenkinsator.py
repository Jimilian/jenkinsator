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


def validate_params(params):  # noqa: C901
    if args.replace and not params.name and not params.jobs_file:
        print("Please, provide job name ('--job') or file with job names ('--jobs-file')")
        return False

    if params.name and params.jobs_file:
        print("Using '--job' and '--jobs-file' at the same time is not supported")
        return False

    if args.dump_to_file and (not params.name or params.jobs_file):
        print("`--dump-to-file` can be used only with `--name`")
        return False

    if args.create_from_file and (not params.name or params.jobs_file):
        print("`--create-from-file` can be used only with `--name`")
        return False

    if args.enable and args.disable:
        print("--enable and --disable can not be used together")
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


def get_config(jenkins, job_name):
    try:
        return jenkins.get_job_config(job_name)
    except jenkins_api.NotFoundException:
        print("Can't find the job:", job_name)

    return None


def get_jobs(args):
    jobs = None
    if args.name:
        jobs = [args.name]

    if args.jobs_file:
        jobs = get_job_list(args.jobs_file)

    return jobs


def replace(jenkins, args):
    jobs = get_jobs(args)

    for job in jobs:
        original_config = get_config(jenkins, job)
        if not original_config:
            continue

        orig, target = args.replace.split(REPLACE_SPLITTER)
        new_config = original_config.replace(orig, target)

        if original_config == new_config:
            print("Config was not changed for the job:", job)
        else:
            if not args.dry_run:
                jenkins.reconfig_job(job, new_config)
            print("Config was updated for the job:", job)

    return


def create_from_file(jenkins, args):
    with open(args.create_from_file) as f:
        if not args.dry_run:
            jenkins.create_job(args.name, f.read())
        print("Job `%s` was created from the file: %s" % (args.name, args.create_from_file))


def dump_to_file(jenkins, args):
    config = get_config(jenkins, args.name)
    if not config:
        return

    if not args.dry_run:
        with open(args.dump_to_file, "w") as f:
            f.write(config)
    print("Job `%s` was dumped to the file: %s" % (args.name, args.dump_to_file))


def enable(jenkins, args):
    for job in get_jobs(args):
        if not args.dry_run:
            jenkins.enable_job(job)
        print("Enable the job:", job)


def disable(jenkins, args):
    for job in get_jobs(args):
        if not args.dry_run:
            jenkins.disable_job(job)
        print("Disable the job:", job)


def process_jobs(jenkins, args):  # noqa: C901
    if args.replace:
        replace(jenkins, args)
    elif args.dump_to_file:
        dump_to_file(jenkins, args)
    elif args.create_from_file:
        create_from_file(jenkins, args)

    if args.enable:
        enable(jenkins, args)
    elif args.disable:
        disable(jenkins, args)

    return


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Jenkinsator helps to orchestrate Jenkins master')
    parser.add_argument(dest="jenkins", action="store", help="Jenkins master [full url]")
    parser.add_argument('--login', help="login to access Jenkins [INSECURE - use .netrc]")
    parser.add_argument('--password', help="password to access Jenkins [INSECURE - use .netrc]")
    parser.add_argument('--dry-run', action="store_true", help="do not perform any action")

    subparsers = parser.add_subparsers(title='Actions', dest="action")
    job_parser = subparsers.add_parser("job")
    job_parser.add_argument('--jobs-file',
                            help="file to retrive the list of jobs to be processed [one per line]")
    job_parser.add_argument('--name', help="job to be processed [full name]")
    job_parser.add_argument('--replace',
                            help="use {0} to split original value and desired one, i.e."
                            "`aaa{0}bbb` replaces all occurances of `aaa` by `bbb`".
                            format(REPLACE_SPLITTER))
    job_parser.add_argument('--dump-to-file', help="dump job configuration to the file")
    job_parser.add_argument('--create-from-file', help="create the job from configuration file")
    job_parser.add_argument('--enable', action="store_true", help="enable the job")
    job_parser.add_argument('--disable', action="store_true", help="disable the job")
    args = parser.parse_args()

    if not validate_params(args):
        sys.exit(1)

    sys.exit(main(args))
