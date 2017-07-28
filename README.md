# jenkinsator
[![Build Status](https://travis-ci.org/Jimilian/jenkinsator.svg?branch=master)](https://travis-ci.org/Jimilian/jenkinsator)

## How to install it
Just download jenkinsator.py file and follow the instructions.

## How to use it

I.e. replace all occurances of SOURCE by DEST for the list of jobs provided in file jobs.txt:

    python jenkinsator.py JENKINS_URL --login=LOGIN --password=PASSWORD job --replace "SOURCE#DEST" --jobs-file=jobs.txt

For more details check:

    python jenkinsator.py --help

## How to provide credentials in secure way

The tool supports two ways: secure and in-secure (as it was shown in example above). The secure way is a little bit more complex and it uses the magic of [.netrc](https://www.gnu.org/software/inetutils/manual/html_node/The-_002enetrc-file.html) in case of Linux/Mac or [_netrc](https://superuser.com/a/1076070/483606) on Windows. So, all you need is to create a *~/.netrc* file this follow content:

    default
            login <your_login>
            password <your_password>

or

    machine <jenkins_host_name>
            login <your_login>
            password <your_password>

If you just created the *.netrc* file, you must change the permission to 600 using the follow command:

    chmod 600 ~/.netrc

Done! Now *jenkinsator* will be able to get the credentials from this file.

## Supported features

- [x] Replace pattern in job config
- [x] Create new job from config.xml file
- [x] Dump job configuration to thie
- [x] Enable/disable the job
- [x] Enable/disable the node
- [x] List all plugins

## Road map

- [ ] Replace pattern in node config

---

Work in Progress! So far *jenkinsator* was tested with python3.4+ only.
