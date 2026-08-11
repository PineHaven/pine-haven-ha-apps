"""Enter the restricted runtime account after Supervisor options are loaded."""

import os
import pwd


class PrivilegeDropError(RuntimeError):
    """Raised when the process cannot enter its restricted runtime account."""


def drop_process_privileges(user: str = "deco-lab") -> None:
    """Drop root permanently; leave an already unprivileged process unchanged."""

    if os.geteuid() != 0:
        return

    try:
        account = pwd.getpwnam(user)
        os.setgroups([])
        os.setgid(account.pw_gid)
        os.setuid(account.pw_uid)
    except (KeyError, OSError) as err:
        raise PrivilegeDropError("privilege_drop_failed") from err

    if os.geteuid() == 0:
        raise PrivilegeDropError("privilege_drop_failed")

    os.umask(0o077)
