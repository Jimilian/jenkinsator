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


def get_items_from_file(list_file):
    jobs = set()
    for line in open(list_file):
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
    if not params.name and not params.list_from_file:
        print("Please, provide job name ('--name') or file with job names ('--list-from-file')")
        return False

    if params.name and params.list_from_file:
        print("Using '--name' and '--list-from-file' at the same time is not supported")
        return False

    if args.action == "job":
        if args.dump_to_file and (not params.name or params.list_from_file):
            print("`--dump-to-file` can be used only with `--name`")
            return False

        if args.create_from_file and (not params.name or params.list_from_file):
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
    elif args.action == "node":
        process_nodes(jenkins, args)

    return 0


def process_nodes(jenkins, args):
    if args.enable:
        enable(jenkins, args, "node")
    elif args.disable:
        disable(jenkins, args, "node")

    return


def get_config(jenkins, job_name):
    try:
        return jenkins.get_job_config(job_name)
    except jenkins_api.NotFoundException:
        print("Can't find the job:", job_name)

    return None


def get_items(args):
    items = None
    if args.name:
        items = [args.name]

    if args.list_from_file:
        items = get_items_from_file(args.list_from_file)

    return items


def replace(jenkins, args):
    jobs = get_items(args)

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


def enable(jenkins, args, key):
    for item in get_items(args):
        if not args.dry_run:
            if key == "job":
                jenkins.enable_job(item)
            else:
                jenkins.enable_node(item)
        print("Enable {0}: {1}".format(key, item))


def disable(jenkins, args, key):
    for item in get_items(args):
        if not args.dry_run:
            if key == "job":
                jenkins.disable_job(item)
            else:
                jenkins.disable_node(item)
        print("Disable {0}: {1}".format(key, item))


def process_jobs(jenkins, args):  # noqa: C901
    if args.replace:
        replace(jenkins, args)
    elif args.dump_to_file:
        dump_to_file(jenkins, args)
    elif args.create_from_file:
        create_from_file(jenkins, args)

    if args.enable:
        enable(jenkins, args, "job")
    elif args.disable:
        disable(jenkins, args, "job")

    return


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Jenkinsator helps to orchestrate Jenkins master')
    parser.add_argument(dest="jenkins", action="store", help="Jenkins master [full url]")
    parser.add_argument('--login', help="login to access Jenkins [INSECURE - use .netrc]")
    parser.add_argument('--password', help="password to access Jenkins [INSECURE - use .netrc]")
    parser.add_argument('--dry-run', action="store_true", help="do not perform any action")

    subparsers = parser.add_subparsers(title='Actions', dest="action")
    job_parser = subparsers.add_parser("job")
    job_parser.add_argument('--replace',
                            help="use {0} to split original value and desired one, i.e."
                            "`aaa{0}bbb` replaces all occurances of `aaa` by `bbb`".
                            format(REPLACE_SPLITTER))
    job_parser.add_argument('--dump-to-file', help="dump job configuration to the file")
    job_parser.add_argument('--create-from-file', help="create the job from configuration file")
    node_parser = subparsers.add_parser("node")

    for sub_parser, key in [(job_parser, "job"), (node_parser, "node")]:
        sub_parser.add_argument('--list-from-file',
                                help="file to retrive the list of " +
                                key + "s to be processed [one per line]")
        sub_parser.add_argument('--name', help=key + " to be processed [full name]")
        sub_parser.add_argument('--enable', action="store_true", help="enable the " + key)
        sub_parser.add_argument('--disable', action="store_true", help="disable the " + key)

    args = parser.parse_args()

    if not validate_params(args):
        sys.exit(1)

    sys.exit(main(args))
