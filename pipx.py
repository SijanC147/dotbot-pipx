import os
import subprocess
import dotbot


def which(program):
    def is_exe(fpath):
        return os.path.isfile(fpath) and os.access(fpath, os.X_OK)

    fpath, _ = os.path.split(program)
    if fpath:
        if is_exe(program):
            return program
    else:
        for path in os.environ["PATH"].split(os.pathsep):
            exe_file = os.path.join(path, program)
            if is_exe(exe_file):
                return exe_file
    return None


class Pipx(dotbot.Plugin):
    """
    Installs pipx packages using the `pipx install` command
    """

    _directive = "pipx"

    _default_values = {
        "package": "",
        "flags": [],
        "stdin": False,
        "stdout": False,
        "stderr": False,
    }

    _pipx_exec = which("pipx")

    def can_handle(self, directive):
        return directive == self._directive and self._pipx_exec

    def handle(self, directive, data):
        if not self.can_handle(directive):
            raise ValueError(
                f"Can not handle directive {directive} or pipx is not installed."
            )
        success = True
        for pkg_info in data:
            data = self._apply_defaults(pkg_info)

            success &= self._handle_single_package(data) == 0
        if not success:
            self._log.warning("Not all packages installed.")
        else:
            self._log.info("Finished installing pipx packages")
        return success

    def _handle_single_package(self, data):
        package = data.get("package", "")
        if not package:
            return 0
        with open(os.devnull, "w") as devnull:
            stdin = None if data.get("stdin", False) else devnull
            stdout = None if data.get("stdout", False) else devnull
            stderr = None if data.get("stderr", False) else devnull

            flags = data.get("flags", [])

            cmd = [self._pipx_exec, "install"] + flags + [package]
            self._log.warning(f'Running command: {" ".join(cmd)}')
            ret = subprocess.call(
                cmd,
                shell=False,
                stdout=stdout,
                stderr=stderr,
                stdin=stdin,
                cwd=self._context.base_directory(),
            )
            return ret

    def _apply_defaults(self, data):
        defaults = self._context.defaults().get("pipx", {})
        base = {
            key: defaults.get(key, value)
            for key, value in self._default_values.items()
        }

        if isinstance(data, dict):
            base.update(data)
        else:
            base.update({"package": data})

        return base
