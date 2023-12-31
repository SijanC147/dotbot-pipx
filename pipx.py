import json
import os
import re
import subprocess
from typing import Any, Callable, Iterable, List, Mapping, TypedDict, Union

import dotbot


class PipxFileDict(TypedDict):
    path: str


class OptionalPipxFileDict(PipxFileDict, total=False):
    force: Union[bool, List[str]]
    lock: Union[bool, List[str]]
    upgrade: Union[bool, List[str]]


PipxFile = Union[str, OptionalPipxFileDict]


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
    _pipx_exec: str | None = None

    def __init__(self, *args, **kwargs) -> None:
        self._pipx_exec = which("pipx")
        self._directives = {
            "pipx": self._pipx,
            "pipxfile": self._pipxfile,
        }
        self._defaults = {
            "pipx": {
                "stdin": False,
                "stderr": False,
                "stdout": False,
            },
            "pipxfile": {
                "stdin": True,
                "stderr": True,
                "stdout": True,
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
            self._log.info("All pipx packages have been installed")

        return result

    def _pipxfile(
        self, pipx_files: List[PipxFile], defaults: Mapping[str, Any]
    ) -> bool:
        errors: List[str] = []
        result: bool = True

        for pipx_file in pipx_files:
            if isinstance(pipx_file, str):
                file = pipx_file
                force = lock = upgrade = False
            elif isinstance(pipx_file, dict):
                file = pipx_file["path"]
                force = pipx_file.get("force", False)
                lock = pipx_file.get("lock", False)
                upgrade = pipx_file.get("upgrade", False)
            else:
                self._log.error(f"Invalid pipxfile: {pipx_file}")
                result = False
                continue

            if lock is True and upgrade is True:
                self._log.error(
                    "Cannot lock and upgrade packages at the same time"
                )
                result = False
                continue

            self._log.info(f"Installing pipx packages from file {file}")
            file_path = os.path.join(self._context.base_directory(), file)
            with open(file_path, "r") as f:
                pipxfile = json.load(f)

            for pkg in pipxfile["venvs"].values():
                pkg_info = pkg["metadata"]["main_package"]
                package = pkg_info["package_or_url"]
                pkg_name = pkg_info["package"]
                pkg_version = pkg_info["package_version"]

                if isinstance(force, list):
                    force_pkg = pkg_name in force
                else:
                    force_pkg = force
                if isinstance(upgrade, list):
                    upgrade_pkg = pkg_name in upgrade
                else:
                    upgrade_pkg = upgrade
                if isinstance(lock, list):
                    lock_pkg = pkg_name in lock
                else:
                    lock_pkg = lock

                if lock_pkg is True and upgrade_pkg is True:
                    self._log.error(
                        f"Cannot lock and upgrade {package} at the same time"
                    )
                    errors.append(package)
                    continue

                if lock_pkg and not package.endswith(pkg_version):
                    package = f"{package}=={pkg_version}"
                with_deps = pkg_info["include_dependencies"]
                pip_args = pkg_info["pip_args"]
                self._log.info(f"Installing {package}")
                cmd = [self._pipx_exec, f"'{package}'"]

                if force_pkg:
                    cmd += ["--force"]
                if with_deps:
                    cmd += ["--include-deps"]
                if pip_args:
                    cmd += ["--pip-args"] + pip_args

                if upgrade_pkg:
                    upgrade_cmd = " ".join(cmd[:1] + ["upgrade"] + cmd[1:])
                    if 0 == self._invoke_shell_command(upgrade_cmd, defaults):
                        self._log.info(f"Upgraded {package}")
                        continue
                install_cmd = " ".join(cmd[:1] + ["install"] + cmd[1:])
                if 0 != self._invoke_shell_command(install_cmd, defaults):
                    errors.append(package)
                else:
                    self._log.info(f"Installed {package}")

        if errors:
            self._log.warning(f"Failed to install: {', '.join(errors)}")
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
