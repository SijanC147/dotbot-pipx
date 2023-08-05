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


class Ruby(dotbot.Plugin):
    """
    Installs ruby gems using the `gem install` command
    """

    _directive = "ruby"

    _default_values = {
        "gem": "",
        "flags": [],
        "stdin": False,
        "stdout": False,
        "stderr": False,
    }

    _gem_exec = which("gem")

    def can_handle(self, directive):
        return directive == self._directive and self._gem_exec

    def handle(self, directive, data):
        if not self.can_handle(directive):
            raise ValueError(
                f"Can not handle directive {directive} or ruby/gem is not installed."
            )
        success = True
        for pkg_info in data:
            data = self._apply_defaults(pkg_info)

            success &= self._handle_single_gem(data) == 0
        if not success:
            self._log.warning("Not all gems installed.")
        else:
            self._log.info("Finished installing ruby gems")
        return success

    def _handle_single_gem(self, data):
        gem = data.get("gem", "")
        if not gem:
            return 0
        with open(os.devnull, "w") as devnull:
            stdin = None if data.get("stdin", False) else devnull
            stdout = None if data.get("stdout", False) else devnull
            stderr = None if data.get("stderr", False) else devnull

            flags = data.get("flags", [])

            cmd = [self._gem_exec, "install"] + flags + [gem]
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
        defaults = self._context.defaults().get("ruby", {})
        base = {
            key: defaults.get(key, value)
            for key, value in self._default_values.items()
        }

        if isinstance(data, dict):
            base.update(data)
        else:
            base.update({"gem": data})

        return base
