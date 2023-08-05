import json
import os
import re
import subprocess
from typing import Any, Callable, Iterable, Mapping

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
    _directives: Mapping[str, Callable] = {}
    _defaults: Mapping[str, Any] = {}
    _pipx_exec = which("pipx")

    def __init__(self, *args, **kwargs) -> None:
        self._directives = {
            "pipx": self._pipx,
            "pipxfile": self._pipxfile,
        }
        self._defaults = {
            "pipx": {
                "stdin": False,
                "stderr": False,
                "stdout": False,
                "force_intel": False,
            },
            "pipxfile": {
                "stdin": True,
                "stderr": True,
                "stdout": True,
                "force_intel": False,
            },
        }
        super().__init__(*args, **kwargs)

    def can_handle(self, directive: str) -> bool:
        return self._pipx_exec is not None and directive in self._directives

    def handle(self, directive: str, data: Iterable) -> bool:
        user_defaults = self._context.defaults().get(directive, {})
        local_defaults = self._defaults.get(directive, {})
        defaults = {**local_defaults, **user_defaults}
        return self._directives[directive](data, defaults)

    # def handle(self, directive, data):
    #     if not self.can_handle(directive):
    #         raise ValueError(
    #             f"Can not handle directive {directive} or pipx is not installed."
    #         )
    #     success = True
    #     for pkg_info in data:
    #         data = self._apply_defaults(pkg_info)

    #         success &= self._handle_single_package(data) == 0
    #     if not success:
    #         self._log.warning("Not all packages installed.")
    #     else:
    #         self._log.info("Finished installing pipx packages")
    #     return success

    def _pipx(self, packages: list, defaults: Mapping[str, Any]) -> bool:
        result: bool = True

        for pkg in packages:
            run = self._install(
                f"{self._pipx_exec} install {pkg}",
                f"{self._pipx_exec} list --short | grep {pkg}",
                pkg,
                defaults,
            )
            if not run:
                self._log.error("Some packages were not installed")
                result = False

        if result:
            self._log.info("All brew packages have been installed")

        return result

    def _pipxfile(self, pipx_files: list, defaults: Mapping[str, Any]) -> bool:
        result: bool = True

        for file in pipx_files:
            self._log.info(f"Installing from file {file}")
            with open(file, "r") as f:
                pipxfile = json.load(f)

            for package, package_info in pipxfile["venvs"].items():
                version = package_info["metadata"]["main_package"][
                    "package_version"
                ]
                pip_args = package_info["metadata"]["main_package"]["pip_args"]
                cmd = f"pipx install '{package}=={version}' {pip_args}"

            if 0 != self._invoke_shell_command(cmd, defaults):
                self._log.warning(f"Failed to install file [{file}]")
                result = False

        return result

    def _invoke_shell_command(
        self, cmd: str, defaults: Mapping[str, Any]
    ) -> int:
        with open(os.devnull, "w") as devnull:
            return subprocess.call(
                cmd,
                shell=True,
                cwd=self._context.base_directory(),
                stdin=devnull if defaults["stdin"] else None,
                stdout=devnull if defaults["stdout"] else None,
                stderr=devnull if defaults["stderr"] else None,
            )

    def _install(self, install_format, check_installed_format, pkg, defaults):
        cwd = self._context.base_directory()

        if not pkg:
            self._log.error("Cannot process blank package name")
            return False

        pkg_parse = re.search(r"^(?:.+/)?(.+?)(?: .+)?$", pkg)
        if not pkg_parse:
            self._log.error(f"Package name {pkg} doesn't work for some reason")
            return False

        pkg_name = pkg_parse[1]

        with open(os.devnull, "w") as devnull:
            isInstalled = subprocess.call(
                check_installed_format.format(pkg_name=pkg_name),
                shell=True,
                stdin=devnull,
                stdout=devnull,
                stderr=devnull,
                cwd=cwd,
            )

            if isInstalled == 0:
                self._log.debug(f"{pkg} already installed")
                return True

            self._log.info(f"Installing {pkg}")
            result = self._invoke_shell_command(
                install_format.format(pkg=pkg), defaults
            )
            if 0 != result:
                self._log.warning(f"Failed to install [{pkg}]")

            return 0 == result

    # def _handle_single_package(self, data):
    #     package = data.get("package", "")
    #     if not package:
    #         return 0
    #     with open(os.devnull, "w") as devnull:
    #         stdin = None if data.get("stdin", False) else devnull
    #         stdout = None if data.get("stdout", False) else devnull
    #         stderr = None if data.get("stderr", False) else devnull

    #         flags = data.get("flags", [])

    #         cmd = [self._pipx_exec, "install"] + flags + [package]
    #         self._log.warning(f'Running command: {" ".join(cmd)}')
    #         ret = subprocess.call(
    #             cmd,
    #             shell=False,
    #             stdout=stdout,
    #             stderr=stderr,
    #             stdin=stdin,
    #             cwd=self._context.base_directory(),
    #         )
    #         return ret

    # def _apply_defaults(self, data):
    #     defaults = self._context.defaults().get("pipx", {})
    #     base = {
    #         key: defaults.get(key, value)
    #         for key, value in self._default_values.items()
    #     }

    #     if isinstance(data, dict):
    #         base.update(data)
    #     else:
    #         base.update({"package": data})

    #     return base
