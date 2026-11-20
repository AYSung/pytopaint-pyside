from pathlib import Path

from pytopaint.io import (
    IOPaths,
    _contains_filter_string,
    _is_valid_filetype,
    _read_fcs_3_0,
    _read_fcs_3_1,
    filter_valid_files,
    get_child_files,
    get_fcs_version,
)


def test_io_paths():
    io_paths = IOPaths()
    home_dir = str(Path.home())
    assert io_paths.home == Path.home()

    assert io_paths.last_case_dir == home_dir
    assert io_paths.last_case_parent_dir == home_dir
    assert io_paths.last_file_dir == home_dir
    assert io_paths.last_file_parent_dir == home_dir
    assert io_paths.last_save_dir == home_dir

    io_paths.set_file_dir(Path('test/path/to/first/file/'))
    io_paths.set_file_parent_dir(Path('test/path/to/first/'))
    assert io_paths.last_case_dir == home_dir
    assert io_paths.last_case_parent_dir == 'test/path/to/first'
    assert io_paths.last_file_dir == 'test/path/to/first/file'
    assert io_paths.last_file_parent_dir == 'test/path/to/first'

    io_paths = IOPaths()
    io_paths.set_case_dir(Path('test/path/to/case/'))
    io_paths.set_case_parent_dir(Path('test/path/to/'))
    assert io_paths.last_case_dir == 'test/path/to/case'
    assert io_paths.last_case_parent_dir == 'test/path/to'
    assert io_paths.last_file_dir == 'test/path/to/case'
    assert io_paths.last_file_parent_dir == 'test/path/to'

    io_paths.set_file_dir(Path('test/path/to/different/file/'))
    io_paths.set_file_parent_dir(Path('test/path/to/different/'))
    assert io_paths.last_case_dir == 'test/path/to/case'
    assert io_paths.last_case_parent_dir == 'test/path/to'
    assert io_paths.last_file_dir == 'test/path/to/different/file'
    assert io_paths.last_file_parent_dir == 'test/path/to/different'

    io_paths.reset_case_dir()
    assert io_paths.last_case_dir == home_dir
    assert io_paths.last_case_parent_dir == 'test/path/to'
    assert io_paths.last_file_dir == 'test/path/to/different/file'
    assert io_paths.last_file_parent_dir == 'test/path/to/different'

    io_paths.set_save_dir('test/path/to/save/file/')
    assert io_paths.last_case_dir == home_dir
    assert io_paths.last_case_parent_dir == 'test/path/to'
    assert io_paths.last_file_dir == 'test/path/to/different/file'
    assert io_paths.last_file_parent_dir == 'test/path/to/different'
    assert io_paths.last_save_dir == 'test/path/to/save/file/'


def test_is_valid_filetype():
    assert _is_valid_filetype(Path('test.fcs'))
    assert _is_valid_filetype(Path('test.FCS'))
    assert _is_valid_filetype(Path('test.h5ad'))
    assert _is_valid_filetype(Path('test.H5AD'))
    assert not _is_valid_filetype(Path('test'))
    assert not _is_valid_filetype(Path('test.docx'))
    assert not _is_valid_filetype(Path('test/'))


def test_contains_filter_string():
    assert _contains_filter_string(Path('test.fcs'))
    assert _contains_filter_string(Path('test.h5ad'))
    assert not _contains_filter_string(Path('test_BLANK.fcs'))
    assert not _contains_filter_string(Path('test_viability.fcs'))
    assert not _contains_filter_string(Path('test_CELL COUNT.fcs'))


def test_get_child_files():
    assert get_child_files(Path('tests/resources/')) == [
        Path('tests/resources/cytek_22_bit.fcs'),
        Path('tests/resources/normal_01_B.fcs'),
    ]
    assert get_child_files(Path('tests/resources/layouts')) == []


def test_filter_valid_files():
    assert filter_valid_files(
        [
            Path('tests/resources/layouts/test.yml'),
            Path('tests/resources/normal_01_B.fcs'),
        ]
    ) == [Path('tests/resources/normal_01_B.fcs')]
    assert (
        filter_valid_files(
            [
                Path('tests/resources/layouts/test.yml'),
                Path('tests/resources/non-existent-file.fcs'),
            ]
        )
        == []
    )


def test_get_fcs_version():
    assert get_fcs_version(Path('tests/resources/normal_01_B.fcs')) == 'FCS3.0'
    assert get_fcs_version(Path('tests/resources/cytek_22_bit.fcs')) == 'FCS3.2'


def test_read_fcs_3_0():
    assert _read_fcs_3_0(Path('tests/resources/normal_01_B.fcs')).version == 'FCS3.0'


def test_read_fcs_3_1():
    assert _read_fcs_3_1(Path('tests/resources/cytek_22_bit.fcs')).version == 'FCS3.2'
