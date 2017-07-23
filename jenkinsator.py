#!/usr/bin/python
from __future__ import absolute_import

import argparse


def get_job_list(job_file):
    jobs = set()
    for line in open(job_file):
        if line:
            jobs.add(line)
    return jobs


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Jenkinsator helps to orchestrate Jenkins master')
    parser.add_argument('--login', help="login to access Jenkins master")
    parser.add_argument('--password', help="password to access Jenkins master")
    parser.add_argument('--jobs-file',
                        help="file to retrive the list of jobs to be processed [one url per line]")
    parser.add_argument('--job', help="job be processed [full path]")

    args = parser.parse_args()

    if args.job and args.jobs_file:
        print("Using '--job' and '--jobs-file' at the same time is not supported")
        exit(1)

    jobs = None
    if args.job:
        jobs = list(args.job)

    if args.jobs_file:
        jobs = get_job_list(args.jobs_file)

    if not jobs:
        print("Please, provide job name ('--job') or file with job names ('--jobs-file')")
        exit(1)

    for job in jobs:
        print(job)

    exit(0)
