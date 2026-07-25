from pytopaint.channels import clean_marker_name, sort_channels


def test_clean_marker_name():
    assert clean_marker_name('KAPPA') == 'Kappa'
    assert clean_marker_name('m Kappa') == 'Kappa'
    assert clean_marker_name('mKAPPA') == 'Kappa'
    assert clean_marker_name('LAMBDA') == 'Lambda'
    assert clean_marker_name('m Lambda') == 'Lambda'
    assert clean_marker_name('mLAMBDA') == 'Lambda'
    assert clean_marker_name('TDT') == 'TdT'
    assert clean_marker_name('TdT') == 'TdT'
    assert clean_marker_name('mpo') == 'MPO'

    assert clean_marker_name('CD45 AF700') == 'CD45'
    assert clean_marker_name('CD45') == 'CD45'
    assert clean_marker_name('CD45 RA') == 'CD45 RA'
    assert clean_marker_name('CD45 BV480') == 'CD45'
    assert clean_marker_name('CD5 BV480') == 'CD5'
    assert clean_marker_name('CD11b') == 'CD11b'
    assert clean_marker_name('CD41/CD61') == 'CD41/CD61'


def test_sort_channels():
    test_channels = [
        'CD12',
        'CD45',
        'CD32',
        'CD123',
        'FSC-A',
        'FSC-H',
        'Time',
        'Lambda',
        'Kappa',
        'HLA-DR',
        'SSC-H',
        'SSC-A',
    ]

    assert sort_channels(test_channels) == [
        'FSC-A',
        'FSC-H',
        'SSC-A',
        'SSC-H',
        'CD12',
        'CD32',
        'CD45',
        'CD123',
        'HLA-DR',
        'Kappa',
        'Lambda',
        'Time',
    ]
