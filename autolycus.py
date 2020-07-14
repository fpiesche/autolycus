#!/usr/bin/env python3

from __future__ import print_function, division, unicode_literals

import argparse
from configparser import ConfigParser
import dataset
import dateparser
import datetime
import glob
from hashlib import md5
import logging
import os
import platform
import psutil
from random import choice
import re
import sys
from time import sleep

from hercules_config import HerculesConfig
from autolycus_logger import AutolycusFormatter

class Autolycus(object):

    def __init__(self):
        self._parse_args()

        self.logger = logging.getLogger('autolycus')
        self.logger.setLevel(logging.DEBUG)

        stdout_log = logging.StreamHandler(sys.stdout)
        stdout_log.setLevel(logging.DEBUG)
        stdout_log.setFormatter(AutolycusFormatter())
        self.logger.addHandler(stdout_log)

        self.servers = ['map-server', 'char-server', 'login-server']

        self.config = HerculesConfig(self.hercules_path)

        self.version_info_file = os.path.join(
            self.hercules_path, 'version_info.ini')
        self.version_info = self._read_version_info()

    def _parse_args(self):
        parser = argparse.ArgumentParser(
            formatter_class=argparse.ArgumentDefaultsHelpFormatter)

        parser.add_argument('-p', '--hercules_path',
                            default=os.path.abspath(os.path.dirname(__file__)),
                            help='The path containing the Hercules installation to control.')
        parser.add_argument('-r', '--autorestart', action='store_true',
                            help='Automatically restart servers when making configuration changes.')

        subparsers = parser.add_subparsers(title='Available commands')

        info = subparsers.add_parser('info',
                                     help='Output server status and version information and exit.')
        info.set_defaults(func=self.info)

        start = subparsers.add_parser('start', help='Start the game servers.')
        start.set_defaults(func=self.start)

        stop = subparsers.add_parser('stop', help='Stop the game servers.')
        stop.set_defaults(func=self.stop)

        restart = subparsers.add_parser(
            'restart', help='Stop and restart the game servers.')
        restart.set_defaults(func=self.restart)

        sql_upgrades = subparsers.add_parser(
            'sql_upgrades', help='Run any SQL upgrades needed.')
        sql_upgrades.set_defaults(func=self.sql_upgrades)

        setupall = subparsers.add_parser(
            'setup_all', help='Set up database and inter-server config and run SQL upgrades.')
        setupall.add_argument('-dh', '--db_hostname', default='db',
                              help='The host name or IP address for the database server.')
        setupall.add_argument('-du', '--db_username', default=os.environ.get('MYSQL_USER', ''),
                              help='The user name used to connect to the database server.')
        setupall.add_argument('-dp', '--db_password',  default=os.environ.get('MYSQL_PASSWORD', ''),
                              help='The password for the database user.')
        setupall.add_argument('-dd', '--db_database',  default=os.environ.get('MYSQL_DATABASE', ''),
                              help='The database on the MySQL server to use.')
        setupall.add_argument('--db_port',  default=os.environ.get('MYSQL_PORT', '3306'),
                              help='The port used to reach the database server.')
        setupall.add_argument('-iu', '--is_username', default=os.environ.get('INTERSERVER_USER', ''),
                              help='The user name used for servers to communicate.')
        setupall.add_argument('-ip', '--is_password', help='The password for inter-server user.',
                              default=os.environ.get('INTERSERVER_PASSWORD', ''))
        setupall.set_defaults(func=self.setup_all)

        dbsetup = subparsers.add_parser(
            'setup_db', help='Set up the database server configuration.')
        dbsetup.add_argument('-dh', '--db_hostname', default='db',
                             help='The host name or IP address for the database server.')
        dbsetup.add_argument('-du', '--db_username', default=os.environ.get('MYSQL_USER', ''),
                             help='The user name used to connect to the database server.')
        dbsetup.add_argument('-dp', '--db_password',  default=os.environ.get('MYSQL_PASSWORD', ''),
                             help='The password for the database user.')
        dbsetup.add_argument('-dd', '--db_database',  default=os.environ.get('MYSQL_DATABASE', ''),
                             help='The database on the MySQL server to use.')
        dbsetup.add_argument('--db_port',  default=os.environ.get('MYSQL_PORT', '3306'),
                             help='The port used to reach the database server.')
        dbsetup.set_defaults(func=self.setup_database_connection)

        issetup = subparsers.add_parser(
            'setup_interserver', help='Set up the inter-server communications configuration.')
        issetup.add_argument('-iu', '--is_username', default=os.environ.get('INTERSERVER_USER', ''),
                             help='The user name used for servers to communicate.')
        issetup.add_argument('-ip', '--is_password', help='The password for inter-server user.',
                             default=os.environ.get('INTERSERVER_PASSWORD', ''))
        issetup.set_defaults(func=self.setup_interserver)

        account = subparsers.add_parser(
            'account', help='Edit or create an account on the server.')
        account.add_argument(
            'name', help='The user name for the account. Will be created if it does not exist.')
        account.add_argument('-p', '--password', help='The password for the account.')
        account.add_argument('-s', '--sex', help='The sex for the account (default: random).',
                             default=choice(['M', 'F']))
        account.add_argument('--admin', help='Whether the account should be admin.',
                             action='store_true')
        account.set_defaults(func=self.account)

        import_sql = subparsers.add_parser(
            'import_sql', help='Import an SQL file into the database.')
        import_sql.add_argument(
            'file_name', help='The path to the .sql file to import.')
        import_sql.set_defaults(func=self.import_sql)

        self.args = parser.parse_args()
        self.hercules_path = os.path.abspath(self.args.hercules_path)
        self.autorestart = self.args.autorestart

    def _read_version_info(self):
        """Parse the version_info.ini file.

        Returns:
            dict: A dictionary of the keys and values in the version info file.
        """
        version_info = {'git_version': 'unknown',
                        'packet_version': 'unknown',
                        'build_date': 'unknown',
                        'server_mode': 'unknown',
                        'arch': 'unknown'}

        if not os.path.exists(self.version_info_file):
            self.logger.warning(f'Failed to find {self.version_info_file}!')
            return version_info

        config = ConfigParser()
        config.read(self.version_info_file)

        if 'version_info' not in config.sections():
            self.logger.warning(f'version_info section not found in {self.version_info_file}')
            return version_info

        for info in version_info.keys():
            try:
                version_info[info] = config['version_info'][info]
            except KeyError:
                self.logger.warning(f'Failed to find entry {info} in {self.version_info_file}!')
                continue

        return version_info

    def _server_pid(self, server):
        """Read the pid files in the Hercules directory.

        Args:
            server (str): The server to get the pid for [map, login, char]
        Returns:
            int: The stored process ID for the server. None if no ID is stored.
        """
        pid_file_path = os.path.join(self.hercules_path, f'{server}.pid')
        if os.path.exists(pid_file_path):
            with open(pid_file_path, 'r') as pidfile:
                return int(pidfile.read())
        else:
            return None

    def _server_executable(self, server_name):
        """Return the full path for the executable for the given server, with extension as needed.

        Args:
            server_name (str): The server name to get the executable path for.
        """
        ext = '.exe' if platform.system() == 'Windows' else ''
        return os.path.join(self.hercules_path, f'{server_name}{ext}')

    def _get_status(self, server):
        """Get the status for the given server.

        Args:
            server (str): The server to check status for [map, login, char]
        Returns:
            str: The server status [running, stopped, orphaned, missing].
                "orphaned" means there is a process for the server but no pid file (or one
                    with a pid that doesn't match the process)
                "missing" means there is a pid file but no process for the server.
        Raises:
            AssertionError: No server status could be determined for the given server.
        """
        expected_pid = self._server_pid(server)

        # We're expecting a server to be running
        if expected_pid is not None:
            if psutil.pid_exists(expected_pid):
                proc = psutil.Process(expected_pid)
                if proc.name().startswith(server):
                    # We've found a process of the right name with the pid we're expecting
                    return ('running', expected_pid)
                else:
                    # The stored pid exists but belongs to another process
                    return ('missing', expected_pid)
            else:
                # The stored pid does not exist
                return ('missing', expected_pid)

        # We aren't aware of a running server
        elif expected_pid is None:
            matching_processes = []
            for proc in psutil.process_iter():
                with proc.oneshot():
                    if proc.name().startswith(server):
                        matching_processes.append(proc.pid)

            if len(matching_processes) > 1:
                self.logger.warn(f'Found multiple processes matching {server}!')
                return ('orphaned', matching_processes)
            elif len(matching_processes) == 1:
                return ('orphaned', matching_processes[0])
            else:
                return ('stopped', None)

        raise AssertionError(f'Failed to find status for {server}!')

    def _run_executable(self, server, force=False):
        """Run the specified server executable.

        This will clean up orphaned server processes and stray pid files, but not stop running
        ones by default. Pass in the force parameter to kill and restart a running server.

        Args:
            server (str): The server executable to run.
            force (boolean): Whether to restart the server if it is already running.
        """
        current_status, pid = self._get_status(server)

        if current_status == 'running' and not force:
            self.logger.info(f'{server} already running on pid {pid}, not starting another.')
            return
        elif current_status == 'orphaned' or (current_status == 'running' and force):
            self.logger.info(f'{server} {current_status} on pid {pid}, killing...')
            self._kill_server(server)
        elif current_status == 'missing':
            self.logger.info(f'{server} missing on pid {pid}, removing pidfile.')
            os.remove(os.path.join(self.hercules_path, f'{server}.pid'))

        proc = psutil.Popen([self._server_executable(server)])
        if psutil.pid_exists(proc.pid):
            with open(os.path.join(self.hercules_path, f'{server}.pid'), 'w') as pidfile:
                print(proc.pid, file=pidfile)
            self.logger.info(f'Started {server} with pid {proc.pid}.')
        else:
            exe = self._server_executable(server)
            raise OSError(f'Ran {exe} but failed to find process!')

    def _kill_server(self, server):
        """Kill the specified server.

        Args:
            server (str): Which of the servers to kill.
        """
        server_status, server_pid = self._get_status(server)
        pidfile = os.path.join(self.hercules_path, f'{server}.pid')
        if server_status in ['orphaned', 'running']:
            self.logger.info(f'Asking {server} (pid {server_pid}) to shut down.')
            proc = psutil.Process(server_pid)
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except psutil.TimeoutExpired:
                self.logger.warn(f'{server} failed to exit within 10 seconds, killing process!')
                proc.kill()
        else:
            self.logger.info(f'{server} is {server_status}, no need to stop.')

        if os.path.exists(pidfile):
            self.logger.info(f'Removing pidfile for {server}.')
            os.remove(pidfile)

    @property
    def _database_config(self):
        db_config = {}
        for key in ['db_username', 'db_password', 'db_hostname', 'db_port', 'db_database']:
            db_config[key] = self.config.get('sql_connection.conf', key).replace('"', '')
        return db_config

    def _database(self):
        """Get a database connection object as a context handler."""
        db_config = self._database_config
        db = dataset.connect(
            'mysql://{db_username}:{db_password}@{db_hostname}:{db_port}/{db_database}'.format(
                **db_config))
        return db

    def _database_status(self):
        """Check connection to the database and output the connection status."""
        db = self._database()
        try:
            db.tables
            return {'ok': True, 'url': db.url, 'reason': None}
        except Exception as exc:
            return {'ok': False, 'url': db.url, 'reason': str(exc).replace('\n', ' ')}

    def _wait_for_database(self, timeout=60):
        self.logger.info(f'Waiting for database for up to {timeout} seconds...')
        while timeout > 0:
            status = self._database_status()
            if status['ok']:
                return True
            else:
                timeout -= 1
                sleep(1)
        raise IOError(
            'Database {url} did not become available in time! Reason: {reason}'.format(**status))

    def execute(self):
        # try:
        self.args.func()
        # except Exception as exc:
        #     self.logger.error(f'Failed to execute {self.args.func}! Reason: {exc}')

    def info(self):
        """Print info on the Hercules server."""
        self.logger.info(f'Hercules {arch} git version {git_version}'.format(**self.version_info))
        self.logger.info(f'Packet version {self.version_info["packet_version"]}')
        self.logger.info(f'{self.version_info["server_mode"]} mode')
        self.logger.info(f'Build date {self.version_info["build_date"]}')
        for server in self.servers:
            status, pid = self._get_status(server)
            self.logger.info(f'{server} status: {status} (pid: {pid})')
        db_status = self._database_status()
        status = 'OK' if db_status['ok'] else 'Unavailable'
        self.logger.info(f'Database status: {status}')
        self.logger.info(f'Database URL: {db_status["url"]}')
        if db_status['reason']:
            self.logger.info(f'Database status reason: {db_status["reason"]}')

    def setup_database_connection(self, hostname=None, username=None, password=None,
                                  database=None, port=None):
        """Set up the database configuration file.

        Args:
            hostname (str, optional): The host name for the database server.
            username (str, optional): The user name used to log into the database.
            password (str, optional): The password for the database user.
            database (str, optional): The database to use on the server.
            port (str, optional): The network port used to reach the database server.
        """
        field_mappings = {
            'db_hostname': hostname or self.args.db_hostname,
            'db_username': username or self.args.db_username,
            'db_password': password or self.args.db_password,
            'db_port': port or self.args.db_port,
            'db_database': database or self.args.db_database
        }
        self.logger.info(f'Setting up database connection as {field_mappings}.')
        for setting, value in field_mappings.items():
            if value and self.config.get('sql_connection.conf', setting) not in [value, f'"{value}"']:
                self.config.set('sql_connection.conf', setting, value)

    def setup_interserver(self, username=None, password=None):
        """Set up the inter-server configuration file and user.

        Args:
            username (str, optional): The user name for the inter-server user.
            password (str, optional): The password for the inter-server user.
        """
        field_mappings = {
            'userid': username or self.args.is_username,
            'passwd': password or self.args.is_password
        }

        if field_mappings['userid'] or field_mappings['passwd']:
            self.logger.info(f'Setting up interserver user {field_mappings["userid"]}.')
            self.account(id=1, name=field_mappings['userid'],
                        password=field_mappings['passwd'], sex='S')
            for config_file in ['char-server.conf', 'map-server.conf']:
                for setting, value in field_mappings.items():
                    if value and self.config.get(config_file, setting) not in [value, f'"{value}"']:
                        self.config.set(config_file, setting, value)
        else:
            self.logger.info('No interserver user specified to set up, leaving defaults.')


    def start(self):
        """Start the servers."""
        self.info()
        for server in self.servers:
            try:
                self._run_executable(server)
            except Exception as exc:
                raise OSError(f'Failed to run {server}! Reason: {exc}')

    def stop(self):
        """Stop the servers."""
        for server in self.servers:
            self._kill_server(server)

    def restart(self):
        """Restart the servers."""
        self.stop()
        self.start()

    def sql_upgrades(self, force=False):
        """Determine whether any SQL upgrades need to be run and do so if appropriate.
        
        Args:
            force (boolean): Whether or not to apply SQL updates even if build date cannot be
                confidently determined.
        """
        if self.version_info['build_date'] == 'unknown':
            if not force:
                raise KeyError(f'Could not get build date from {self.version_info_file}! ' +
                               'SQL upgrades are unsafe. To run them anyway, use the "force" flag.')
            else:
                build_date = datetime.datetime.fromtimestamp(
                    os.path.getctime(self._server_executable('char-server')))
                char_server = self._server_executable('char-server')
                test.logger.warn(f'Failed to get build date from {self.version_info_file}! ' +
                                 'SQL upgrades are unsafe.')
                test.logger.warn('sql_upgrades called with force argument, proceeding anyway.')
                test.logger.warn('------- THIS MAY BREAK YOUR DATABASE! -------')
                test.logger.warn(f'Assuming {char_server} creation date {build_date} as build date.')
        else:
            build_date = dateparser.parse(self.version_info['build_date'],
                                          date_formats=['%Y-%m-%d_%H-%M-%S'])

        upgrade_files = sorted(glob.glob(os.path.join(self.hercules_path, 'sql-files',
                                                      'upgrades', '*.sql')))

        for file_name in upgrade_files:
            upgrade_date = dateparser.parse(os.path.splitext(os.path.basename(file_name))[0],
                                            date_formats=['%Y-%m-%d--%H-%M'])
            if upgrade_date is None:
                self.logger.info(f'Failed to parse upgrade date for {file_name} - ignoring file.')
                continue
            elif upgrade_date > build_date:
                self.import_sql(file_name)
            else:
                self.logger.debug(f'{file_name} is older than build, no need to import.')

    def import_sql(self, file_name):
        """Import an .sql file to the database

        Args:
            file_name (str): The full path to the .sql file to import.
        
        Raises:
            IOError: The database is unavailable.
        """
        self.logger.info(f'Importing {file_name} to database...')

        if not self._database_status()['ok']:
            raise IOError('Database is unavailable; cannot import SQL file!')

        with open(file_name) as sql_file, self._database() as db:
            query = ''

            for line in sql_file.readlines():
                if line.startswith('--') or line.startswith('#') or not line.strip():
                    # Ignore any comments, SQL update timestamp lines and empty lines
                    continue

                # just add any non-comment lines to the query
                query += line.strip() + ' '

                # If the current line ends a command, run it
                if line.strip().endswith(';'):
                    self.logger.debug(query)
                    try:
                        db.query(query)
                    except Exception as exc:
                        self.logger.error(f'SQL statement error: {exc}')

                    # empty out current query after running the statement.
                    query = ''

    def setup_all(self):
        """Stop the servers if needed, set up database+interserver settings and run SQL upgrades."""
        self.stop()
        self.setup_database_connection()
        self._wait_for_database()
        self.setup_interserver()
        self.sql_upgrades()

    def account(self, name, id=None, password=None, sex=None, gm=False):
        """Create or modify accounts on the server."""
        account_spec = {
            'userid': name
        }

        if sex or hasattr(self.args, 'sex'):
            account_spec['sex'] = sex or self.args.sex
        
        if gm or hasattr(self.args, 'gm'):
            account_spec['group_id'] = 99

        if id:
            account_spec['account_id'] = id
        
        if password:
            if self.config.get('login-server.conf', 'use_MD5_passwords') == 'true':
                account_spec['password'] = md5(password)
            else:
                account_spec['password'] = password

        with self._database() as db:
            login_table = db['login']
            if not login_table.find(userid=name):
                if 'user_pass' not in account_spec:
                    raise KeyError(f'Account {name} does not exist so a password is required!')
                else:
                    login_table.insert(account_spec)
                    self.logger.log(f'Account {name} created; GM rights: {gm}.')
            else:
                if 'id' in account_spec:
                    key = 'id'
                else:
                    key = 'userid'
                login_table.update(account_spec, [key])
                self.logger.info(f'Account {name} updated to {account_spec}')


if __name__ == '__main__':
    launcher = Autolycus()
    launcher.execute()