"""
Generates a ssh key if necessary, and adds a config to ~/.ssh/config
if it doesn't exist already.
[github]
formula = sprinter.formulas.ssh
keyname = github
nopassphrase = true
type = rsa
hostname = github.com
user = toumorokoshi
create = false
"""
import os

from sprinter.formulabase import FormulaBase

ssh_config_template = \
    """
Host %(host)s
  HostName %(hostname)s
  IdentityFile %(ssh_path)s
  User %(user)s
"""

ssh_config_path = os.path.expanduser('~/.ssh/config')


class SSHFormula(FormulaBase):

    def install(self):
        ssh_path = self.__generate_key(self.target)
        self.__install_ssh_config(self.target, ssh_path)
        if self.target.has('command'):
            self.__call_command(self.target.get('command'), ssh_path)

    def update(self):
        ssh_path = self.__generate_key(self.target)
        self.__install_ssh_config(self.target, ssh_path)

    def deactivate(self):
        ssh_path = os.path.join(self.directory.install_directory(self.feature_name),
                                self.source.get('keyname'))
        self.__install_ssh_config(self.source, ssh_path)

    def activate(self):
        ssh_path = os.path.join(self.directory.install_directory(self.feature_name),
                                self.source.get('keyname'))
        self.__install_ssh_config(self.source, ssh_path)

    def __generate_key(self, config):
        """
        Generate the ssh key, and return the ssh config location
        """
        command = "ssh-keygen -t %(type)s -f %(keyname)s -N  " % config
        cwd = self.directory.install_directory(self.feature_name)
        if 'ssh_path' in config:
            cwd = config['ssh_path']
        if 'create' not in config or config['create'].lower().startswith('t'):
            if not os.path.exists(cwd):
                os.makedirs(cwd)
            if not os.path.exists(os.path.join(cwd, config['keyname'])):
                self.logger.info(self.lib.call(command, cwd=cwd))
        return os.path.join(cwd, config['keyname'])

    def __install_ssh_config(self, config, ssh_path):
        """
        Install the ssh configuration
        """
        config['ssh_path'] = ssh_path
        ssh_config_injection = ssh_config_template % config
        if os.path.exists(ssh_config_path):
            if self.injections.in_noninjected_file(ssh_config_path, "Host %s" % config['host']):
                self.logger.info("SSH config for host %s already exists! Override?" % config['host'])
                self.logger.info("Your existing config will not be overwritten, simply inactive.")
                overwrite = self.lib.prompt("Override?", boolean=True, default="no")
                if overwrite:
                    self.injections.inject(ssh_config_path, ssh_config_injection)
            else:
                self.injections.inject(ssh_config_path, ssh_config_injection)
        else:
            self.injections.inject(ssh_config_path, ssh_config_injection)
        self.injections.commit()

    def __call_command(self, command, ssh_path):
        ssh_path += ".pub"  # make this the public key
        ssh_contents = open(ssh_path, 'r').read().rstrip('\n')
        command = command.replace('{{ssh}}', ssh_contents)
        self.logger.info(self.lib.call(command, shell=True))