from pathlib import Path

from pytopaint.io import (
    _is_valid_filetype,
    _scrub_metadata,
    filter_valid_files,
    get_child_files,
)


def test_is_valid_filetype():
    assert _is_valid_filetype(Path('test.fcs'))
    assert _is_valid_filetype(Path('test.FCS'))
    assert _is_valid_filetype(Path('test.h5ad'))
    assert _is_valid_filetype(Path('test.H5AD'))
    assert not _is_valid_filetype(Path('test'))
    assert not _is_valid_filetype(Path('test.docx'))
    assert not _is_valid_filetype(Path('test/'))


def test_get_child_files():
    assert get_child_files(Path('tests/resources/')) == [
        Path('tests/resources/normal_01_B.fcs')
    ]
    assert get_child_files(Path('tests/resources/layouts')) == []


def test_filter_valid_files():
    assert filter_valid_files([
        Path('tests/resources/layouts/test.yml'),
        Path('tests/resources/normal_01_B.fcs'),
    ]) == [Path('tests/resources/normal_01_B.fcs')]
    assert (
        filter_valid_files([
            Path('tests/resources/layouts/test.yml'),
            Path('tests/resources/non-existent-file.fcs'),
        ])
        == []
    )


def test_scrub_metadata():
    assert _scrub_metadata({
        'beginanalysis': 'test',
        'spill': 'test',
        'mode': 'test',
        'test': 'test',
    }) == {'beginanalysis': 'test', 'spill': 'test', 'mode': 'test'}
