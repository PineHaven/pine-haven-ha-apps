import unittest
from types import SimpleNamespace
from unittest.mock import Mock, call, patch

from deco_research.privileges import PrivilegeDropError, drop_process_privileges


class PrivilegeDropTests(unittest.TestCase):
    @patch("deco_research.privileges.os.setuid")
    @patch("deco_research.privileges.os.setgid")
    @patch("deco_research.privileges.os.setgroups")
    @patch("deco_research.privileges.pwd.getpwnam")
    @patch("deco_research.privileges.os.geteuid", return_value=1000)
    def test_already_unprivileged_process_is_unchanged(
        self, _geteuid, getpwnam, setgroups, setgid, setuid
    ):
        drop_process_privileges()

        getpwnam.assert_not_called()
        setgroups.assert_not_called()
        setgid.assert_not_called()
        setuid.assert_not_called()

    @patch("deco_research.privileges.os.umask")
    @patch("deco_research.privileges.os.geteuid", side_effect=[0, 1000])
    @patch("deco_research.privileges.pwd.getpwnam")
    @patch("deco_research.privileges.os.setgroups")
    @patch("deco_research.privileges.os.setgid")
    @patch("deco_research.privileges.os.setuid")
    def test_root_drops_groups_gid_and_uid_before_runtime(
        self, setuid, setgid, setgroups, getpwnam, _geteuid, umask
    ):
        getpwnam.return_value = SimpleNamespace(pw_uid=991, pw_gid=992)
        operations = Mock()
        operations.attach_mock(setgroups, "setgroups")
        operations.attach_mock(setgid, "setgid")
        operations.attach_mock(setuid, "setuid")

        drop_process_privileges()

        self.assertEqual(
            operations.mock_calls,
            [call.setgroups([]), call.setgid(992), call.setuid(991)],
        )
        umask.assert_called_once_with(0o077)

    @patch("deco_research.privileges.os.geteuid", return_value=0)
    @patch("deco_research.privileges.pwd.getpwnam", side_effect=KeyError)
    def test_missing_runtime_account_fails_closed(self, _getpwnam, _geteuid):
        with self.assertRaises(PrivilegeDropError):
            drop_process_privileges()


if __name__ == "__main__":
    unittest.main()
