#!/usr/bin/env python3

from __future__ import print_function, division, unicode_literals

import argparse
from configparser import ConfigParser
import dataset
import dateparser
import logging
import os
import psutil
from random import choice
import re
import sys

from hercules_config import HerculesConfig

class HerculesAdmin(object):

    def __init__(self):
        self._parse_args()

        self.logger = logging.getLogger('hercules')
        self.logger.setLevel(logging.DEBUG)

        stdout_log = logging.StreamHandler(sys.stdout)
        stdout_log.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        stdout_log.setFormatter(formatter)
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

        firstrun = subparsers.add_parser(
            'first_run', help='Set up database and inter-server config, run SQL upgrades, and start the game servers.')
        firstrun.add_argument('-dh', '--db_hostname', default='db',
                              help='The host name or IP address for the database server.')
        firstrun.add_argument('-du', '--db_username', default=os.environ.get('MYSQL_USER', ''),
                              help='The user name used to connect to the database server.')
        firstrun.add_argument('-dp', '--db_password',  default=os.environ.get('MYSQL_PASSWORD', ''),
                              help='The password for the database user.')
        firstrun.add_argument('-iu', '--is_username', default=os.environ.get('INTERSERVER_USER', ''),
                              help='The user name used for servers to communicate.')
        firstrun.add_argument('-ip', '--is_password', help='The password for inter-server user.',
                              default=os.environ.get('INTERSERVER_PASSWORD', ''))
        firstrun.set_defaults(func=self.first_run)

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
        dbsetup.add_argument('--db_port',  default=os.environ.get('MYSQL_PORT', ''),
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
            self.logger.warning('Failed to find version info file %s! Version info will be empty.'
                                % self.version_info_file)
            return version_info

        config = ConfigParser()
        config.read(self.version_info_file)

        if 'version_info' not in config.sections():
            self.logger.warning('version_info section not found in %s! Version info will be empty.'
                                % self.version_info_file)
            return version_info

        for info in version_info.keys():
            try:
                version_info[info] = config['version_info'][info]
            except KeyError:
                self.logger.warning('Failed to find entry %s in %s! Data will be empty.'
                                    % (info, self.version_info_file))
                continue

        return version_info

    def _server_pid(self, server):
        """Read the pid files in the Hercules directory.

        Args:
            server (str): The server to get the pid for [map, login, char]
        Returns:
            int: The stored process ID for the server. None if no ID is stored.
        """
        pid_file_path = os.path.join(self.hercules_path, '%s.pid' % server)
        if os.path.exists(pid_file_path):
            with open(pid_file_path, 'r') as pidfile:
                return int(pidfile.read())
        else:
            return None

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
                self.logger.warn('Found multiple processes matching %s!',
                                 'Status info may be unreliable.'
                                 % server)
                return ('orphaned', matching_processes)
            elif len(matching_processes) == 1:
                return ('orphaned', matching_processes[0])
            else:
                return ('stopped', None)

        raise AssertionError('Failed to find status for %s!' % server)

    def _run_executable(self, server, force=False):
        """Run the specified server executable.

        This will clean up orphaned server processes and stray pid files, but not stop running
        ones by default. Pass in the force parameter to kill and restart a running server.

        Args:
            server (str): The server executable to run.
            force (boolean): Whether to restart the server if it is already running.
        """

        current_status, pid = self._get_status(server)
        if current_status == 'missing' or (current_status == 'running' and force):
            os.remove(os.path.join(self.hercules_path, '%s.pid' % server))
        if current_status == 'orphaned' or (current_status == 'running' and force):
            self._kill_server(server)

        proc = psutil.Popen([os.path.join(self.hercules_path, server)])
        if psutil.pid_exists(proc.pid):
            with open(os.path.join(self.hercules_path, '%s.pid' % server), 'w') as pidfile:
                print(proc.pid, file=pidfile)

    def _kill_server(self, server):
        """Kill the specified server.

        Args:
            server (str): Which of the servers to kill.
        """
        pid = self._server_pid(server)
        if psutil.pid_exists(pid):
            self.logger.info('Asking %s (pid %s) to shut down.' % (server, pid))
            proc = psutil.Process(pid)
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except psutil.TimeoutExpired:
                self.logger.warn(
                    '%s failed to exit within 10 seconds, killing process!' % server)
                proc.kill()

        os.remove(os.path.join(self.hercules_path, '%s.pid' % server))

    @property
    def _database_config(self):
        db_config = {}
        for key in ['db_username', 'db_password', 'db_hostname', 'db_port', 'db_database']:
            db_config[key] = self.config.get('sql_connection.conf', key).replace('"', '')
        return db_config

    def _database(self):
        """Get a database connection object as a context handler."""
        db_config = self._database_config
        db = dataset.connect('mysql://%s:%s@%s:%s/%s' %
                             (db_config['db_username'], db_config['db_password'],
                              db_config['db_hostname'], db_config['db_port'],
                              db_config['db_database']))
        return db

    def _database_status(self):
        """Check connection to the database and output the connection status."""
        db = self._database()
        try:
            self._database().tables
            return {'ok': True, 'url': db.url, 'reason': None}
        except Exception as exc:
            return {'ok': False, 'url': db.url, 'reason': str(exc)}

    def _wait_for_database(self, timeout=60):
        while timeout > 0:
            status = self._database_status()
            if status['ok']:
                return True
            else:
                timeout -= 1
                sleep(1)
        raise IOError('Database %s did not become available in time! Reason: %s' %
                      (status['url'], status['reason']))

    def execute(self):
        self.args.func()

    def info(self):
        """Print info on the Hercules server."""
        self.logger.info('Hercules %s git version %s' %
                         (self.version_info['arch'],
                          self.version_info['git_version']))
        self.logger.info('Packet version %s' %
                         self.version_info['packet_version'])
        self.logger.info('%s mode' %
                         self.version_info['server_mode'])
        self.logger.info('Build date %s' %
                         self.version_info['build_date'])
        for server in self.servers:
            self.logger.info('%s status: %s (pid: %s)' % (server,
                                                          self._get_status(
                                                              server),
                                                          self._server_pid(server)))
        self.logger.info('Database status: %s' % self._database_status())

    def setup_all(self):
        """Read configuration information and set up the server configuration files to match."""
        self.setup_database_connection()
        self.setup_interserver()

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
            'db_hostname': hostname or self.args.get('db_hostname'),
            'db_username': username or self.args.get('db_username'),
            'db_pass': password or self.args.get('db_pass'),
            'db_port': port or self.args.get('db_port'),
            'db_database': database or self.args.get('db_database')
        }
        for setting, value in field_mappings.items():
            if value is not None:
                self.config.set('sql_connection.conf', setting, value)

    def setup_interserver(self, username=None, password=None):
        """Set up the inter-server configuration file and user.

        Args:
            username (str, optional): The user name for the inter-server user.
            password (str, optional): The password for the inter-server user.
        """
        self.account(id=1, name=username, password=password, sex='S')
        for config_file in ['char-server.conf', 'map-server.conf']:
            self.config.set(config_file, 'userid', username)
            self.config.set(config_file, 'passwd', password)


    def start(self):
        """Start the servers."""
        self.info()
        for server in self.servers:
            self._run_executable(server)

    def stop(self):
        """Stop the servers."""
        for server in self.servers:
            self._kill_server(server)

    def restart(self):
        """Restart the servers."""
        self.stop()
        self.start()

    def sql_upgrades(self):
        """Determine whether any SQL upgrades need to be run and do so if appropriate."""
        raise NotImplementedError

    def first_run(self):
        """Set up database and interserver settings, run SQL upgrades, and start the server."""
        self.setup_database_connection()
        self._wait_for_database()
        self.setup_interserver()
        self.sql_upgrades()
        self.start()

    def account(self, name, id=None, password=None, sex=None, admin=False):
        """Create or modify accounts on the server."""
        account_spec = {
            'userid': name
        }

        if sex or hasattr(self.args, 'sex'):
            account_spec['sex'] = sex or self.args.sex
        
        if admin or hasattr(self.args, 'admin'):
            account_spec['group_id'] = 99

        if id:
            account_spec['account_id'] = id

        with self._database() as db:
            login_table = db['login']
            if not login_table.find(userid=name):
                if 'user_pass' not in account_spec:
                    raise KeyError('Account %s does not exist so a password is required!' % name)
                else:
                    login_table.insert(account_spec)
                    self.logger.log('Account %s created with%s admin rights.' %
                                    (name, 'out' if not admin else ''))
            else:
                if 'id' in account_spec:
                    key = 'id'
                else:
                    key = 'userid'
                login_table.update(account_spec, [key])
                self.logger.log('Account %s updated to %s' %
                                (name, account_spec))


if __name__ == '__main__':
    launcher = HerculesAdmin()
    launcher.execute()