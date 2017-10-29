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


class DryJenkins(object):
    def get_nodes(self):
        return [{"name": "dry node", "offline": True}]

    def get_plugins(self, depth):
        return {("DryRun Plugin", "dry run plugin"): {"version": 1}}

    def __getattribute__(self, name):
        if name == "get_nodes":
            return lambda: DryJenkins.get_nodes(self)
        if name == "get_plugins":
            return lambda depth: DryJenkins.get_plugins(self, depth)

        return (lambda *args: "DRY_RUN")


def get_items_from_file(list_file):
    jobs = set()
    for line in open(list_file):
        job_name = line.strip().replace("\n", "")
        if job_name:
            jobs.add(job_name)
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
    if args.action == "job":
        if args.dump_to_file and (not params.name or params.list_from_file):
            print("`--dump-to-file` can be used only with `--name`")
            return False

        if args.create_from_file and (not params.name or params.list_from_file):
            print("`--create-from-file` can be used only with `--name`")
            return False
    elif args.action == "node":
        if params.get_nodes:
            return True
    elif args.action == "script":
        if params.execute_from_file:
            return True
        else:
            print("Please, specify `--execute-from-file` option")
            return False
    else:
        return True

    if not params.name and not params.list_from_file:
        print("Please, provide job name ('--name') or file with job names ('--list-from-file')")
        return False

    if params.name and params.list_from_file:
        print("Using '--name' and '--list-from-file' at the same time is not supported")
        return False

    if args.enable and args.disable:
        print("--enable and --disable can not be used together")
        return False

    return True


def main(args):
    if not args.dry_run:
        jenkins = connect(args.jenkins, args.login, args.password)
    else:
        jenkins = DryJenkins()

    print("Succesfully connected to %s." % args.jenkins, "Version is", jenkins.get_version())

    do_action(args, jenkins)


def do_action(args, jenkins):
    actions = {"job": lambda x, y: process_jobs(x, y),
               "node": lambda x, y: process_nodes(x, y),
               "plugin": lambda x, y: process_plugins(x, y),
               "script": lambda x, y: process_script(x, y)}

    action = actions[args.action]
    action(jenkins, args)


def process_script(jenkins, args):
    with open(args.execute_from_file) as f:
        script = f.read()

        res = jenkins.run_script(script)

        if res:
            print(res)


def process_plugins(jenkins, args):
    for plugin, desc in sorted(jenkins.get_plugins(depth=1).items(),
                               key=lambda x: x[0][1]):
        print("{0}: {1}".format(plugin[1], desc["version"]))


def process_nodes(jenkins, args):
    what_to_do = get_what_to_do(args, "node")
    if what_to_do:
        generic_action(jenkins, args, what_to_do)
    elif args.get_nodes:
        get_all_nodes(jenkins, args)
    elif args.replace:
        replace(jenkins, args, "node")

    return


def get_all_nodes(jenkins, args):
    show_all = args.get_nodes == "all"

    for node in jenkins.get_nodes():
        if show_all or node['offline'] == (args.get_nodes == "offline"):
            print(node['name'])


def get_config(jenkins, name, key):
    try:
        if key == "job":
            return jenkins.get_job_config(name)
        if key == "node":
            return jenkins.get_node_config(name)
        print("Invalid key for get_config:", key)
    except jenkins_api.NotFoundException:
        print("Can't find the {0}: {1}".format(key, name))

    return None


def get_items(args):
    items = None
    if args.name:
        items = [args.name]

    if args.list_from_file:
        items = get_items_from_file(args.list_from_file)

    return items


def update_config(jenkins, item, new_config, key):
    if key == "job":
        jenkins.reconfig_job(item, new_config)
    if key == "node":
        jenkins.reconfig_node(item, new_config)
    return


def replace(jenkins, args, key):
    splitter = args.replace[0]
    statement = args.replace[1:]
    if statement.count(splitter) != 1:
        print()
        print("You selected bad splitter '{0}', "
              "because it occurs in your replacement as well. "
              "Please, choose another one.".format(splitter))
        return

    items = get_items(args)

    for item in items:
        original_config = get_config(jenkins, item, key)
        if not original_config:
            continue

        orig, target = args.replace[1:].split(splitter)
        new_config = original_config.replace(orig, target)

        if original_config == new_config:
            print("Config was not changed for the {0}: {1}".format(key, item))
        else:
            update_config(jenkins, item, new_config, key)
            print("Config was updated for the {0}: {1}".format(key, item))

    return


def start_jobs(jenkins, args):
    items = get_items(args)

    for item in items:
        print("Run:", item)
        jenkins.build_job(item, {"fake_parameter": "x"})

    return


def create_from_file(jenkins, args):
    with open(args.create_from_file) as f:
        jenkins.create_job(args.name, f.read())
        print("Job `%s` was created from the file: %s" % (args.name, args.create_from_file))


def dump_to_file(jenkins, args, key):
    config = get_config(jenkins, args.name, key)
    if not config:
        return

    if not args.dry_run:
        with open(args.dump_to_file, "w") as f:
            f.write(config)
    print("Configuration for the {0} `{1}` was dumped to the file: {2}".
          format(key, args.name, args.dump_to_file))

    return


def generic_action(jenkins, args, key):
    actions = {"Delete job": lambda x: jenkins.delete_job(x),
               "Delete node": lambda x: jenkins.delete_node(x),
               "Disable node": lambda x: jenkins.disable_node(x),
               "Disable job": lambda x: jenkins.disable_job(x),
               "Enable job": lambda x: jenkins.enable_job(x),
               "Enable node": lambda x: jenkins.enable_node(x),
               "Dump job": lambda _: dump_to_file(jenkins, args, "job"),
               "Dump node": lambda _: dump_to_file(jenkins, args, "node")}

    for item in get_items(args):
        action = actions[key]
        action(item)
        print("{0}: {1}".format(key, item))


def process_jobs(jenkins, args):
    what_to_do = get_what_to_do(args, "job")
    if what_to_do:
        generic_action(jenkins, args, what_to_do)
    elif args.replace:
        replace(jenkins, args, "job")
    elif args.create_from_file:
        create_from_file(jenkins, args)
    elif args.start:
        start_jobs(jenkins, args)

    return


def get_what_to_do(args, key):
    if args.enable:
        return "Enable " + key
    elif args.disable:
        return "Disable " + key
    elif args.delete:
        return "Delete " + key
    elif args.dump_to_file:
        return "Dump " + key

    return None


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Jenkinsator helps to orchestrate Jenkins master')
    parser.add_argument(dest="jenkins", action="store", help="Jenkins master [full url]")
    parser.add_argument('--login', help="login to access Jenkins [INSECURE - use .netrc]")
    parser.add_argument('--password', help="password to access Jenkins [INSECURE - use .netrc]")
    parser.add_argument('--dry-run', action="store_true", help="do not perform any action")

    subparsers = parser.add_subparsers(title='Actions', dest="action",
                                       help="Choose action type you want to perform")
    job_parser = subparsers.add_parser("job")
    job_parser.add_argument('--create-from-file', help="create the job from configuration file")
    job_parser.add_argument('--start', action="store_true", help="starts the job")
    node_parser = subparsers.add_parser("node")

    for sub_parser, key in [(job_parser, "job"), (node_parser, "node")]:
        sub_parser.add_argument('--list-from-file',
                                help="file to retrive the list of " +
                                key + "s to be processed [one per line]")
        sub_parser.add_argument('--name', help=key + " to be processed [full name]")
        sub_parser.add_argument('--dump-to-file', help="dump" + key + " configuration to the file")
        sub_parser.add_argument('--enable', action="store_true", help="enable the " + key)
        sub_parser.add_argument('--disable', action="store_true", help="disable the " + key)
        sub_parser.add_argument('--delete', action="store_true", help="delete the " + key)
        sub_parser.add_argument('--replace',
                                help="Replace some pattern in the configuration. "
                                "Use first symbol to configure the splitter "
                                "and the rest of parameter to define the "
                                "original value and desired one, i.e."
                                "`?aaa?bbb` specifies `?` as a splitter and "
                                "replaces all occurances of `aaa` by `bbb`")

    node_parser.add_argument('--get-nodes', choices=["offline", "online", "all"],
                             help="dump list of all connected nodes")

    plugin_parser = subparsers.add_parser("plugin")
    plugin_parser.add_argument("--list-all", action="store_true",
                               help="list all available plugins")

    script_parser = subparsers.add_parser("script")
    script_parser.add_argument("--execute-from-file", action="store",
                               help="execute custom Groovy scipt from specified file")

    args = parser.parse_args()

    if not validate_params(args):
        sys.exit(1)

    sys.exit(main(args))
