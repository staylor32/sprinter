from sprinter.testtools import create_mock_environment
from sprinter.formulas.command import CommandFormula

source_config = """
[update]
formula = sprinter.formulas.command
update = echo 'this is old...'

[remove]
formula = sprinter.formulas.command
destroy = echo 'destroy up...'

[deactivate]
formula = sprinter.formulas.command
deactivate = echo 'deactivating...'

[activate]
formula = sprinter.formulas.command
deactivate = echo 'activating...'
"""

target_config = """
[install]
formula = sprinter.formulas.command
setup = echo 'setting up...'
update = echo 'updating...'

[update]
formula = sprinter.formulas.command
update = echo 'update up...'
"""


class TestCommandFormula(object):
    """
    Tests for the command formula.
    """
    def setup(self):
        self.environment = create_mock_environment(
            source_config=source_config,
            target_config=target_config
        )

    def test_setup(self):
        self.environment.install_feature("install")
        self.lib.call.assert_called_once_with("echo 'setting up...'")

    def test_update(self):
        self.environment.update_feature("update")
        self.lib.call.assert_called_once_with("echo 'update up...'")

    def test_destroy(self):
        self.environment.remove_feature("remove")
        self.lib.call.assert_called_once_with("echo 'destroy up...'")

    def test_deactivate(self):
        self.environment.deactivate_feature("deactivate")
        self.lib.call.assert_called_once_with("echo 'deactivate up...'")

    def test_activate(self):
        self.environment.activate_feature("activate")
        self.lib.call.assert_called_once_with("echo 'activate up...'")
