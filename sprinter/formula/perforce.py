"""
Creates a perforce repository and places it at the install
location.

[perforce]
formula = sprinter.formulas.perforce
inputs = p4username
         p4password?
version = r10.1
root_path = ~/p4/
username = %(config:p4username)s
password = %(config:p4password)s
port = perforce.local:1666 
client = %(config:node)s
write_password_p4settings = true
overwrite_p4settings = false
overwrite_client = false

"""

valid_options = ['version', 'root_path', 'username', 'password', 'port', 
                 'client', 'write_p4settings', 'write_password_p4settings', 'overwrite_p4settings',
                 'overwrite_client']

url_template = "http://filehost.perforce.com/perforce/%s/%s/p4"
exec_dict = {"r10.1": {"mac": "bin.macosx104u",
                       "linux": "bin.linux26x86_64"}}

from sprinter import lib

class PerforceFormula(FormulaBase):

    def prompt(self, feature_name, config, reconfigure=False):
        if reconfigure:
            config.prompt('write_p4settings', 'Write a p4settings file?', default='yes')
        config.set_if_empty('write_p4settings', True)

        phase == "install" or reconfigure:
            if config.is_affirmative('write_p4settings'):
                p4settings_path = os.path.join(config.get('root_path'), '.p4settings')

                if os.path.exists(p4settings_path):
                    config.prompt_if_empty(
                        "overwrite_p4settings",
                        "p4settings already exists at %s. Overwrite?" % config.get('root_path'),
                        default="no", only_if_empty=(not reconfigure))

                if lib.is_affirmative(config.get('overwrite_p4settings')):
                    config.prompt_if_empty(
                        "write_password_p4settings",
                        "Insert the perforce password to your p4settings?" +
                        "(password will be stored in plaintext in a file in your perforce root)",
                        default="no", only_if_empty=(not reconfigure))

            config.prompt_if_empty(
                "overwrite_client",
                "Would you like to overwrite the client workspace in perforce?",
                default="yes", only_if_empty=(not reconfigure))

        elif phase == "remove":
                config.prompt_if_empty(
                    "remove_p4root",
                    "Would you like to completely remove the p4 directory?" +
                    default="no", only_if_empty=True)

    def install(self, feature_name, config):
        super(PerforceFormula, self).install(feature_name, config)
        self.p4environ = dict(os.environ.items() + [('P4USER', config['username']),
                                                    ('P4PASSWD', config['password']),
                                                    ('P4CLIENT', config['client'])])
        self.__install_perforce(feature_name, config)
        if not os.path.exists(os.path.expanduser(config.get('root_path')):
            os.makedirs(os.path.expanduser(config['root_path']))
        if config.is_affirmative('write_p4settings'):
            self.__write_p4settings(config)
        if config.is_affirmative('overwrite_client'):
            self.__configure_client(config)
        self.__add_p4_env(config)

    def update(self, feature_name, source_config, target_config):
        super(PerforceFormula, self).update(feature_name, config)
        if source_config.get('version', 'r10.1') != target_config.get('version', 'r10.1'):
            os.remove(os.path.join(self.directory.install_directory(feature_name), 'p4'))
            self.__install_perforce(self, feature_name, target_config)
        self.__add_p4_env(target_config)

    def remove(self, feature_name, config):
        super(PerforceFormula, self).remove(feature_name, config)
        self.__destroy_perforce(config)

    def validate(self, feature_name, config):
        errors = super(PerforceFormula, self).validate()
        for required in ['root_path', 'port', 'client', 'username', 'password']:
            if not config.has(required):
                errors.append("%s must be set!" % required)
        for k in config.keys():
            if k not in valid_options:
                self.logger.warn("Unused option %s in %s!" % (k, feature_name)

    def reconfigure(self, feature_name, config):
        self.prompt(feature_name, config, reconfigure=True)
        self.__write_p4settings(config)

    def __install_perforce(self, feature_name, config):
        """ install perforce binary """
        version = config.get('version', 'r10.1')
        exec_dir = exec_dict[version]['mac'] if self.system.isOSX() else \
                   exec_dict[version]['linux']
        url = url_template % (version, exec_dir)
        d = self.directory.install_directory(feature_name)
        if not os.path.exists(d):
            os.makedirs(d)
        self.logger.info("Downloading p4 executable...")
        urllib.urlretrieve(url, os.path.join(d, "p4"))
        self.directory.symlink_to_bin("p4", os.path.join(d, "p4"))
        self.p4_command = os.path.join(d, "p4")

    def __write_p4settings(self, config):
        """ write perforce settings """
        self.logger.info("Writing p4settings...")
        root_dir = os.path.expanduser(config.get('root_path'))
        p4settings_path = os.path.join(root_dir, ".p4settings")
        if not os.path.exists(p4settings_path) or self.get('overwrite_p4settings'):
            self.logger.info("Overwriting existing p4settings...")
            os.remove(p4settings_path)
        else:
            return
        with open(p4settings_path, "w+") as p4settings_file:
            p4settings_file.write(p4settings_template % config.to_dict())
            if config.get('write_password_p4settings'):
                p4settings_file.write("\nP4PASSWD=%s" % config['password'])

    def __add_p4_env(self, config):
        self.directory.add_to_rc('export P4PORT=%s' % config['port'])
        if config.get('write_p4settings'):
            self.directory.add_to_rc('export P4CONFIG=.p4settings')

    def __configure_client(self, config):
        """ write the perforce client """
        self.logger.info("Configuring p4 client...")
        client_dict = config.to_dict()
        client_dict['root_path'] = os.path.expanduser(config.get('root_path'))
        os.chdir(client_dict['root_path'])
        client_dict['hostname'] = self.system.node
        client_dict['p4view'] = config['p4view'] % self.environment.target.get_context_dict()
        client = re.sub('//depot', '    //depot', p4client_template % client_dict)
        self.logger.info(lib.call("%s client -i" % self.p4_command,
                                  stdin=client,
                                  env=self.p4environ,
                                  cwd=client_dict['root_path']))

    def __destroy_perforce(self, config):
        """ destroy the perforce root """
        self.logger.info("Removing %s..." % config.get('root_path'))
        shutil.rmtree(os.path.expanduser(config.get('root_path'))

p4settings_template = """
P4USER=%(username)s
P4CLIENT=%(client)s
"""

p4client_template = """
Client:	%(client)s

Update:	2012/12/03 00:16:24

Access:	2012/12/03 00:16:24

Owner:	%(username)s

Host:	%(hostname)s

Description:
        Created by %(username)s

Root:	%(root_path)s

Options:	noallwrite noclobber nocompress unlocked nomodtime normdir

LineEnd:	local

View:
%(p4view)s
"""