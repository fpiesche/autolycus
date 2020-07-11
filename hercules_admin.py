#!/usr/bin/env python3

import argparse
from configparser import ConfigParser
import dataset
import dateparser
import logging
import psutil

# Going to leave this for now because I'll have to write my own
# parser for Hercules' config files and that's a whole can of
# worms that I don't want to touch just yet...
# from hercules_config import HerculesConfig


class HerculesAdmin(object):
    def __init__(self):
        self._parse_args()

        self.logger = logging.getLogger('hercules')
        self.version_info_file = os.path.join(self.hercules_path, 'version_info.ini')

        self.servers = ['map-server', 'char-server', 'login-server']

        self.version_info = self._read_version_info()
        self.pids = self._read_pids()

    def _parse_args(self):
        parser = argparse.ArgumentParser(
            formatter_class=argparse.ArgumentDefaultsHelpFormatter)
        parser.add_argument('operation',
                            choices=['info', 'start', 'stop', 'restart',
                                     'setup_all', 'setup_database', 'setup_interserver'],
                            help=('The action to perform on the servers.\n',
                                    '\tinfo: Output version information and exit.\n',
                                    '\tstart: Start the game servers.\n',
                                    '\tstop: Stop the game servers.\n',
                                    '\trestart: Stop and restart the servers as needed.\n',
                                    '\tsetup_all: Set up the server configuration.\n',
                                    '\tsetup_database: Set up the database server configuration.\n',
                                    '\tsetup_interserver: Set up the inter-server configuration.\n',
                                    '\tsql_upgrades: Run any SQL upgrades required.\n',
                                    '\tfirst_run: Setup database and interserver settings, run SQL upgades, and start server.\n',
                            ))

        parser.add_argument('-p', '--hercules_path',
                            default=os.path.abspath(os.path.dirname(__file__)),
                            help='The path containing the Hercules installation to control.')
        parser.add_argument('-r', '--autorestart', action='store_true',
                            help='Automatically restart servers when making configuration changes.')

        args = parser.parse_args()
        self.operation = args.operation
        self.hercules_path = args.hercules_path
        self.foreground = args.foreground
        self.autorestart = args.autorestart

    def _parse_version_info(self):
        version_info = {'git_version': 'unknown',
                        'packet_version': 'unknown',
                        'build_date': 'unknown',
                        'server_mode': 'unknown'}

        if not os.path.exists(self.version_info_file):
            self.logger.warning('Failed to find version info file %s! Version info will be empty.'
                                % self.version_info_file)
            return version_info

        config = configparser.ConfigParser()
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
            pid (int): The stored process ID for the server. None if no ID is stored.
        """
        pid_file_path = os.path.join(self.hercules_path, '%s.pid' % server)
        if os.path.exists(pid_file_path):
            with open(pid_file_path, 'r') as pidfile:
                    return int(pidfile.read())
        else:
            return None

    def _read_config(self):
        """Read the current database and inter-server configuration.
        
        This will use the information in the server .conf files by default, but can be
        overridden using environment variables."""
        raise NotImplementedError

    def _set_config(self, config_file, key, value):
        """Set the given value in the given configuration file."""
        raise NotImplementedError

    def _get_status(self, server):
        """Get the status for the given server.

        Args:
            server (str): The server to check status for [map, login, char]
        Returns:
            status (str): The server status [running, stopped, orphaned, missing].
                "orphaned" means there is a process for the server but no pid file (or one
                    with a pid that doesn't match the process)
                "missing" means there is a pid file but no process for the server.
        """
        status = {}
        processes = {}
        expected_pid = self._server_pid(server)

        # We're expecting a server to be running
        if expected_pid is not None and psutil.pid_exists(expected_pid):
            proc = psutil.Process(expected_pid)
            if proc.name().startswith(server):
                # We've found a process of the right name with the pid we're expecting
                return ('running', expected_pid)
            else:
                # The stored pid exists but belongs to another process
                return ('missing', expected_pid)

        # We aren't aware of a running server
        elif expected_pid is None:
            matching_processes = []
            for proc in psutil.process_iter():
                with proc.oneshot():
                    if proc.name().startswith(server):
                        matching_processes.append(proc.pid())

            if len(matching_processes) > 1:
                self.logger.warn('Found multiple processes matching %s!',
                                 'Status info may be unreliable.'
                                 % server)
                return ('orphaned', matching_processes)
            elif len(mathing_processes) == 1:
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
            os.path.remove(os.path.join(self.hercules_path, '%s.pid' % server))
        if current_status == 'orphaned' or (current_status == 'running' and force):
            self._kill_server(server)

        psutil.Popen([os.path.join(self.hercules_path, server)])

    def _kill_server(self, server):
        """Kill the specified server.

        Args:
            server (str): Which of the servers to kill.
        """        
        pid = self._server_pid(server)
        if psutil.pid_exists(pid):
            proc = psutil.Process(pid)
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except psutil.TimeoutExpired:
                self.logger.warn('%s failed to exit within 10 seconds, killing process!' % server)
                proc.kill()

    def info(self):
        self.logger.info('Hercules %s git version %s' %
                         (self.config['version_info']['arch'],
                          self.config['version_info']['git_version']))
        self.logger.info('Packet version %s' %
                         self.config['version_info']['packet_version'])
        self.logger.info('%s mode' %
                         self.config['version_info']['server_mode'])
        self.logger.info('Build date %s' %
                         self.config['version_info']['build_date'])

    def execute(self):
        """Perform the operation specified by the command line."""
        getattr(self, self.operation)()

    def setup_all(self):
        """Read configuration information and set up the server configuration files to match."""
        self.setup_database()
        self.setup_interserver()

    def setup_database(self, hostname=None, username=None, password=None, database=None):
        """Set up the database configuration file."""
        raise NotImplementedError

    def setup_interserver(self, username=None, password=None):
        """Set up the inter-server configuration file and user."""
        raise NotImplementedError

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
        self.setup_database()
        self.setup_interserver()
        self.sql_upgrades()
        self.start()


if __name__ == '__main__':
    launcher = HerculesAdmin()
    launcher.execute()
