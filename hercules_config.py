import dataset
import json


class HerculesConfig(object):
    """[summary]

    Args:
        object ([type]): [description]
    """

    def __init__(self, hercules_path):
        """Read configuration from files.

        Args:
            hercules_path (str): The path to the Hercules installation to configure.
        """



    def show_rate_messages(self, enabled):
        """Toggle XP/drop etc rate messages on login."""
        self.client_conf['show_rate_messages'] = 0x1 if enabled else 0x0


class ConfigurationFile(object):
    """[summary]

    Args:
        object ([type]): [description]
    """

    def __init__(self, path):
        """[summary]

        Args:
            path (str): The path to the configuration file.
        """

        # Navigate up the directory tree until we find the root configuration directory
        self.config_root = os.path.dirname(path)
        while not self.config_root.endswith('conf'):
            self.config_root(os.path.dirname(self.config_root))

        self.defaults_file = path
        self.base_filename = os.path.basename(self.defaults_file)
        self.override_file = os.path.join(self.config_root, 'import', self.base_filename)

        self._settings = {}

        with open(self.defaults_file, 'r') as defaults:
            self._settings.update(json.loads(defaults.read()))

        if os.path.exists(self.override_file):
            with open(self.override_file, 'r') as overrides:
                self._settings.update(json.loads(overrides.read()))

