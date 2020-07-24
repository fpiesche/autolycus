import json
import logging


class AutolycusConfig(object):
    """Read and store Autolycus configuration options."""

    def __init__(self, hercules_path):
        """Read configuration from files.

        Args:
            hercules_path (str): The path to the Hercules installation to configure.
        """
        self.hercules_path = hercules_path
        self.global_config_file = os.path.join(os.path.abspath(os.path.dirname(__file__)),
                                               'autolycus_config.json')
        self.installation_config_file = os.path.join(os.path.abspath(hercules_path),
                                                     'conf', 'autolycus_config.json')
        self._global_config = None
        self._installation_config = None
        self.logger = logging.getLogger('autolycus')

        self._read_config()

    def _write_config(self, config_file, config_dict):
        with open('w', config_file) as config:
            config.write(json.dumps(config_dict))

    def _read_config(self):
        """Read global and installation config from files."""        
        try:
            with open(self.global_config_file) as global_file:
                self._global_config.update(json.loads(global_file.read()))
        except IOError:
            self.logger.info(f'Global config file {self.global_config_file} does not exist.')
        try:
            with open(self.installation_config_file) as install_file:
                self._installation_config.update(
                    json.loads(install_file.read()))
        except IOError:
            self.logger.info(f'Install config file {self.installation_config_file} does not exist.')

    def global_config(self, key, value=None):
        """Read or write a value from the global Autolycus configuration.
        
        Will automatically update the configuration file on disk when setting a value.

        Args:
            key (str): The key of the configuration option to get or set.
            value (str, optional): The value to set the key to. Key will be read if this is None.

        Returns:
            str: The value of the configuration option given.
        """        
        if self._global_config is None:
            self._read_config()
        if value is not None:
            self._global_config[key] = value
            self.write_config(self.global_config_file, self._global_config)
        return self._global_config[key]

    def installation_config(self, key, value=None):
        """Read or write a value from the installation configuration.
        
        Will automatically update the configuration file on disk when setting a value.

        Args:
            key (str): The key of the configuration option to get or set.
            value (str, optional): The value to set the key to. Key will be read if this is None.

        Returns:
            str: The value of the configuration option given.
        """        
        if self._installation_config is None:
            self._read_config()
        if value is not None:
            self._installation_config[key] = value
            self.write_config(self.installation_config_file, self._installation_config)
        return self._installation_config[key]
