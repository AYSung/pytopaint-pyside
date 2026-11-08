from pathlib import Path

from pytopaint.io import (
    _is_not_blank_or_viability,
    _is_valid_filetype,
    _read_fcs_3_0,
    _read_fcs_3_1,
    filter_valid_files,
    get_child_files,
    get_fcs_version,
)


def test_is_valid_filetype():
    assert _is_valid_filetype(Path('test.fcs'))
    assert _is_valid_filetype(Path('test.FCS'))
    assert _is_valid_filetype(Path('test.h5ad'))
    assert _is_valid_filetype(Path('test.H5AD'))
    assert not _is_valid_filetype(Path('test'))
    assert not _is_valid_filetype(Path('test.docx'))
    assert not _is_valid_filetype(Path('test/'))


def test_is_not_blank_or_viability():
    assert _is_not_blank_or_viability(Path('test.fcs'))
    assert _is_not_blank_or_viability(Path('test.h5ad'))
    assert not _is_not_blank_or_viability(Path('test_BLANK.fcs'))
    assert not _is_not_blank_or_viability(Path('test_viability.fcs'))
    assert not _is_not_blank_or_viability(Path('test_CELL COUNT.fcs'))


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
