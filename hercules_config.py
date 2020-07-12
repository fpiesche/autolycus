import glob
import logging
import os
import re

class HerculesConfig(object):
    """Manipulate Hercules configuration files.

    Args:
        hercules_path (str): The path to the Hercules installation to configure.
    """

    def __init__(self, hercules_path):
        """Read configuration from files.

        Args:
            hercules_path (str): The path to the Hercules installation to configure.
        """
        self.hercules_path = hercules_path
        self.logger = logging.getLogger('hercules')

    def _find_config_files(self, file_name):
        """Find any configuration files matching the file name.

        Args:
            file_name (str): The configuration file  to look for.

        Raises:
            IOError: No files matching the name were found.
        
        Returns:
            list: A list of configuration files, in order of priority (highest first).
                This will sort files in the conf/import directory to the front of the list.
        """        
        # First check for any files matching the given file name in the conf/import directory.
        override_glob = os.path.join(self.hercules_path, 'conf', 'import',
                                     '**', os.path.basename(file_name))
        matching_files = glob.glob(override_glob, recursive = True)

        # Then check for any files elsewhere in the conf directory.
        defaults_glob = os.path.join(self.hercules_path, 'conf', '**', os.path.basename(file_name))
        matching_files += [file_name for file_name in
                           glob.glob(defaults_glob, recursive=True)
                           if file_name not in matching_files]

        if not matching_files:
            raise IOError('Failed to find any configuration files matching %s!' % file_name)

        return matching_files


    def get(self, config_file, setting):
        """Read the current value for setting from config_file.

        This will respect override files in conf/import/ and otherwise fall back to the file name
        given.

        NOTE that at this point this will not work with complex values.

        Args:
            config_file (str): The file name of the configuration file to read from.
            setting (str): The setting to read from the configuration file.

        Returns:
            str: The value for the setting as it will be used by the server.
        """
        for file_name in self._find_config_files(config_file):
            with open(file_name, 'r') as conffile:
                configuration = conffile.read()
            matches = re.search(r'\s*%s\s*:\s*(.*)' % setting, configuration)
            if len(matches.groups()) > 1:
                self.logger.warning('Found multiple matches for %s: %s' % (setting, matches.groups()))
                self.logger.warning('Will use first matching group %s.' % matches.groups[0])
            if matches.groups():
                return matches.groups()[0]

    def set(self, file_name, setting, value):
        """Set the given value in the given configuration file.

        Args:
            config_file ([type]): [description]
            setting ([type]): [description]
            value ([type]): [description]

        Raises:
            NotImplementedError: [description]
        """
        full_path = self._find_config_files(file_name)[0]
        self.logger.debug('Setting %s in %s to %s.' % (setting, full_path, value))
        lines = []
        with open(full_path) as config_file:
            config = config_file.read()

        config_lines = config.splitlines()

        matches = re.search(r'\s*%s\s*:.*' % setting, config)
        if not matches:
            # setting isn't currently in the file. Simply append it.
            out_lines = config_lines
            out_lines.append('%s: %s' % (setting, value))
        else:
            out_lines = []
            for line in config_lines:
                matches = re.search(r'\s*%s\s*:\s*(.*)' % setting, line)
                if matches:
                    if matches.groups()[0].startswith('"'):
                        value = '"%s"' % value
                    new_line = re.sub(matches.groups()[0], value, line)
                    self.logger.debug('Replacing %s with %s.' % (line, new_line))
                    out_lines.append(new_line)
                else:
                    out_lines.append(line)

        with open(full_path, 'w') as outfile:
            outfile.write(os.linesep.join(out_lines))


    def show_rate_messages(self, enabled):
        """Toggle XP/drop etc rate messages on login."""
        self.set_config('client.conf', 'show_rate_messages', '0x1')
