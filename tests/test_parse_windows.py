import json
from pathlib import Path

import pytest

from aqt import xmlparser


@pytest.mark.parametrize(
    "in_file,expect_out_file",
    [
        ("windows-5140-update.xml", "windows-5140-expect.json"),
    ],
)
def test_parse_updates(in_file: str, expect_out_file: str):
    xml = (Path(__file__).parent / "data" / in_file).read_text("utf-8")
    expect_all = json.loads((Path(__file__).parent / "data" / expect_out_file).read_text("utf-8"))
    architectures = expect_all["architectures"]
    update_xml = xmlparser.Updates.fromstring(xml)
    expect_metadata = expect_all["modules_metadata_by_arch"]
    for arch in architectures:
        expect_update = expect_metadata[arch]
        updates = update_xml.get_from_arch(arch)
        for entry in updates:
            for expect in expect_update:
                if expect["Name"] == entry.name:
                    assert entry.version == expect["Version"]
                    assert entry.release_date == expect["ReleaseDate"]
                    assert entry.description == expect["Description"]
                    count = 0
                    for item in entry.downloadable_archives:
                        count += 1
                        assert item in expect["DownloadableArchives"]
                    assert count == len(expect["DownloadableArchives"])
                    count = 0
                    for item in entry.auto_dependon:
                        count += 1
                        assert item in expect["AutoDependOn"]
                    assert count == len(expect["AutoDependOn"])
                    for item in entry.dependencies:
                        assert item in [ expect["Dependencies"] ]


@pytest.mark.parametrize(
    ("target,in_file,expect"),
    [
        ("qt.qt6.622.qt5compat.android_armv7", "windows-622-android-update.xml", "qt.tools.qtcreator"),
    ],
)
def test_parse_and_get_packages(target: str, in_file: str, expect: str):
    xml = (Path(__file__).parent / "data" / in_file).read_text("utf-8")
    update_xml = xmlparser.Updates.fromstring(xml)
    packages = update_xml.dfs(target)
    assert expect in packages
    assert len(packages) == 5


@pytest.mark.parametrize(
    ("target,in_file,expect_depend"),
    [
        ("qt.qt5.5140.qtcharts.win32_mingw73", "windows-5140-update.xml", "qt.tools.win32_mingw730"),
    ],
)
def test_get_module_to_package(target: str, in_file: str, expect_depend: str):
    xml = (Path(__file__).parent / "data" / in_file).read_text("utf-8")
    update_xml = xmlparser.Updates.fromstring(xml)
    module = target.split(".")[-2]
    #
    packages = update_xml.dfs(target)
    module_to_package = xmlparser.ModuleToPackage({module: packages})
    assert module_to_package.has_package(target)
    assert module_to_package.has_package(expect_depend)
