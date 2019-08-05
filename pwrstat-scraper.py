#!/usr/bin/env python
import argparse
from datetime import datetime
import logging
import shutil
import subprocess
import sys
import time

import daemon
from influxdb import InfluxDBClient
import yaml


# Logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)


# Sane defaults
DEFAULT_HEART_BEAT = 15
DEFAULT_INFLUX_DB_NAME = 'config.example.yaml'

# Command used to access pwrstat
STAT_COMMAND = ['pwrstat', '-status']

# Which pwrstat results to use as tags and values.
IMPORTANT_PWRSTAT_TAG_KEYS = [
    'Model Name',
    'Firmware Number',
    'Rating Voltage',
    'Rating Power'
]

IMPORTANT_PWRSTAT_VALUE_KEYS = [
    'State',
    'Utility Voltage',
    'Output Voltage',
    'Battery Capacity',
    'Remaining Runtime',
    'Load',
    # 'Last Power Event'
]

IMPORTANT_PWRSTAT_STAT_KEYS_TRANSFORMS = {
    'State': lambda x: 0.0 if x == 'Normal' else 1.0,
    'Battery Capacity': lambda x: float(x)
}


def setup_logging(logfile_path, verbosity):
    """
    Setup a optional file logger.  Always provides a stdout logger.
    :param logfile_path: Full path to the log file.
    :param verbosity: Logging verbosity.
    :return:
    """
    formatter = logging.Formatter("%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s")
    root_logger = logging.getLogger()

    if logfile_path:
        file_handler = logging.FileHandler(logfile_path)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    logger.setLevel(max(2 - verbosity, 0) * 10)


def verify_setup():
    """
    Perform any verification require so we can bail early.
    :return:
    """
    if not shutil.which('pwrstat'):
        logger.error("'pwrstat' not found.")
        sys.exit(1)


def parse_pwrstat(out):
    """
    Parse pwrstat command output into a dictionary.
    We take every line containing periods and split it by period.
    :param out: stdout from the pwrstat command.
    :return:
    """
    pwrstat_dict = {}
    lines = out.split('\n')[3:]
    for line in lines:
        if not line:
            continue

        # We only care about lines with dots in the output
        if '.' not in line:
            continue

        line_split = line.split('.')
        key = line_split[0].strip()

        if 'Remaining Runtime' in line:
            value = line_split[-2].strip()
        else:
            value = line_split[-1].strip()

        pwrstat_dict[key] = value

    return pwrstat_dict


def write_influxdb(client, series_name, pwrstat_dict, dry_run=False):
    """
    Writes a pwrstat dictionary to the InfluxDB using requests (essentially the CURL approach).
    :param client: InfluxDB Client
    :param series_name: The series name to use when generating the packet to write.
    :param pwrstat_dict: The parsed pwrstat dictionary.
    :param dry_run: Whether we should actually post or not.
    :return:
    """
    json_body = {
        'measurement': series_name,
        'tags': {},
        'fields': {},
        'time': None
    }

    for tag in IMPORTANT_PWRSTAT_TAG_KEYS:
        key = tag.replace(' ', '')
        value = pwrstat_dict[tag].split(' ')[0]
        json_body['tags'][key] = value

    for stat_key in IMPORTANT_PWRSTAT_VALUE_KEYS:
        key = stat_key.replace(' ', '')
        value = pwrstat_dict[stat_key].split(' ')[0]
        if stat_key in IMPORTANT_PWRSTAT_STAT_KEYS_TRANSFORMS:
            value = IMPORTANT_PWRSTAT_STAT_KEYS_TRANSFORMS[stat_key](value)
        else:
            value = float(value)
        json_body['fields'][key] = value

    # Convert into NS because that is apparently what InfluxDB wants
    ts = datetime.utcnow().isoformat()
    json_body['time'] = ts

    logger.debug(json_body)
    if dry_run:
        return

    success = client.write_points([json_body])
    if not success:
        logger.error("Error writing to InfluxDB!")


def run_scrape(args, config):
    """
    Perform the scrape.
    :param args: Argparse parsed arguments.
    :param config: Yaml config parsed into a dictionary.
    :return:
    """
    client = InfluxDBClient(config['influx']['host'],
                            config['influx']['port'],
                            config['influx']['user'],
                            config['influx']['password'],
                            config['influx']['db'])

    influx_ping_repsonse = client.ping()
    if influx_ping_repsonse:
        logger.info("Connected to InfluxDB: {0}".format(influx_ping_repsonse))
    else:
        logger.error("Error connecting to InfluxDB.")
        return

    if config['influx']['admin']:
        client.create_database(config['influx']['db'])

    logger.info("InfluxDB URL: {0}".format(client))
    logger.info("Starting up scraper...")
    while True:
        p = subprocess.Popen(STAT_COMMAND, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = p.communicate()

        if p.returncode != 0:
            logger.error("Error executing {0}: {1}".format(STAT_COMMAND, err.decode().strip()))
            return

        pwrstat_dict = parse_pwrstat(out.decode())

        write_influxdb(client, args.series, pwrstat_dict, dry_run=args.dry_run)

        time.sleep(args.interval)


def main():
    """
    Parse arguments and execute the scrape.
    :return:
    """
    parser = argparse.ArgumentParser(description='Scrape power stat binary.')
    parser.add_argument('--config-file',
                        default=DEFAULT_INFLUX_DB_NAME,
                        type=str,
                        help='Influx DB database name, default: %(default)s')
    parser.add_argument('--series',
                        required=True,
                        type=str,
                        help='Series name to use.')
    parser.add_argument('--daemonize', '-d',
                        default=False,
                        action='store_true',
                        help='Daemonize the process.')
    parser.add_argument('--interval', '-n',
                        default=DEFAULT_HEART_BEAT,
                        type=float,
                        help='Time between readings in seconds, default: %(default)s')
    parser.add_argument('--dry-run',
                        default=False,
                        action='store_true',
                        help='Time between readings in seconds.')
    parser.add_argument('--log-file',
                        default=None,
                        action='store_true',
                        help='Time between readings in seconds.')
    parser.add_argument("-v", "--verbose",
                        dest="verbose",
                        action="count",
                        default=0,
                        help="Increase log verbosity.")
    args = parser.parse_args()

    with open(args.config_file, 'r') as stream:
        try:
            config = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            logger.error("Error loading config file [{0}]: {1}".format(args.config_file, exc))
            sys.exit(1)

    setup_logging(args.log_file, args.verbose)
    verify_setup()

    if args.daemonize:
        logger.info("Starting daemon...")
        with daemon.DaemonContext():
            run_scrape(args, config)
    else:
        run_scrape(args, config)

    logger.info("Shutting down...")


if __name__ == "__main__":
    main()
