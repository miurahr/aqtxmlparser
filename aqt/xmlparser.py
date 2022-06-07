#!/usr/bin/env python
#
# Copyright (C) 2022 Hiroshi Miura
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of
# this software and associated documentation files (the "Software"), to deal in
# the Software without restriction, including without limitation the rights to
# use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
# the Software, and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
# FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
# COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
# IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional

from defusedxml import ElementTree


class ModuleToPackage:
    """
    Holds a mapping of module names to a list of Updates.xml PackageUpdate names.
    For example, we could have the following:
    {"qtcharts": ["qt.qt6.620.addons.qtcharts.arch", qt.qt6.620.qtcharts.arch", qt.620.addons.qtcharts.arch",])
    It also contains a reverse mapping of PackageUpdate names to module names, so that
    lookup of a package name and removal of a module name can be done in constant time.
    Without this reverse mapping, QtArchives._parse_update_xml would run at least one
    linear search on the forward mapping for each module installed.

    The list of PackageUpdate names consists of all the possible names for the PackageUpdate.
    The naming conventions for each PackageUpdate are not predictable, so we need to maintain
    a list of possibilities. While reading Updates.xml, if we encounter any one of the package
    names on this list, we can use it to install the package "qtcharts".

    Once we have installed the package, we need to remove the package "qtcharts" from this
    mapping, so we can keep track of what still needs to be installed.
    """

    def __init__(self, initial_map: Dict[str, List[str]]):
        self._modules_to_packages: Dict[str, List[str]] = initial_map
        self._packages_to_modules: Dict[str, str] = {
            value: key for key, list_of_values in initial_map.items() for value in list_of_values
        }

    def add(self, module_name: str, package_names: List[str]):
        self._modules_to_packages[module_name] = self._modules_to_packages.get(module_name, []) + package_names
        for package_name in package_names:
            assert package_name not in self._packages_to_modules, "Detected a package name collision"
            self._packages_to_modules[package_name] = module_name

    def remove_module_for_package(self, package_name: str):
        module_name = self._packages_to_modules[package_name]
        for package_name in self._modules_to_packages[module_name]:
            self._packages_to_modules.pop(package_name)
        self._modules_to_packages.pop(module_name)

    def has_package(self, package_name: str):
        return package_name in self._packages_to_modules

    def get_modules(self) -> Iterable[str]:
        return self._modules_to_packages.keys()

    def __len__(self) -> int:
        return len(self._modules_to_packages)

    def __format__(self, format_spec) -> str:
        return str(sorted(set(self._modules_to_packages.keys())))


@dataclass
class PackageUpdate:
    name: str
    display_name: str
    description: str
    release_date: str
    version: str
    dependencies: List[str]
    auto_dependon: Optional[List[str]]
    downloadable_archives: Optional[List[str]]
    default: bool
    virtual: bool


@dataclass(init=False)
class Updates:
    application_name: str
    application_version: str
    package_updates: List[PackageUpdate]

    def __init__(self):
        self.package_updates = []

    def extend(self, other):
        self.package_updates.extend(other.package_updates)

    @classmethod
    def fromstring(cls, update_xml_text: str):
        self = cls()
        update_xml = ElementTree.fromstring(update_xml_text)
        self.application_name = update_xml.find("ApplicationName").text
        self.application_version = update_xml.find("ApplicationVersion").text
        for packageupdate in update_xml.iter("PackageUpdate"):
            pkg_name = self._get_text(packageupdate.find("Name"))
            display_name = self._get_text(packageupdate.find("DisplayName"))
            full_version = self._get_text(packageupdate.find("Version"))
            package_desc = self._get_text(packageupdate.find("Description"))
            release_date = self._get_text(packageupdate.find("ReleaseDate"))
            dependencies = self._get_list(packageupdate.find("Dependencies"))
            auto_dependon = self._get_list(packageupdate.find("AutoDependOn"))
            archives = self._get_list(packageupdate.find("DownloadableArchives"))
            default = self._get_boolean(packageupdate.find("Default"))
            virtual = self._get_boolean(packageupdate.find("Virtual"))
            self.package_updates.append(
                PackageUpdate(
                    pkg_name,
                    display_name,
                    package_desc,
                    release_date,
                    full_version,
                    dependencies,
                    auto_dependon,
                    archives,
                    default,
                    virtual,
                )
            )
        return self

    def get(self):
        return self.package_updates

    def get_from_arch(self, arch: str):
        result = []
        for update in self.package_updates:
            if update.name.endswith(arch):
                result.append(update)
        return result

    def dfs(self, target:str):
        # initialize
        filo = [target]
        packages = []
        visited = []
        # dfs look-up
        while len(filo) > 0:
            next = filo.pop()
            packages.append(next)
            for entry in self.package_updates:
                if entry.name == next:
                    visited.append(next)
                    for depend in entry.dependencies:
                        if depend not in visited:
                            filo.append(depend)
        return packages

    def _get_text(self, item):
        if item is not None and item.text is not None:
            return item.text
        else:
            return ""

    def _get_list(self, item):
        if item is not None and item.text is not None:
            return ssplit(item.text)
        else:
            return None

    def _get_boolean(self, item):
        if "true" == item:
            return True
        else:
            return False


def ssplit(data: str):
    for element in data.split(","):
        yield element.strip()
