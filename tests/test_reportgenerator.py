from pytopaint.widgets.reportgenerator import (
    generate_report_template,
    _add_marker_smartlist,
    _join_list,
)


def test_generate_report_template():
    assert (
        generate_report_template(
            ip_channels=['FSC-A', 'SSC-A', 'CD5', 'CD10', 'CD19', 'CD20'],
            percent=0.213,
        )
        == 'Immunophenotypic analysis reveals a population of {cell lineage selection:40658} cells (21.3% of total events) with {light scatter strength:40657} forward light scatter, {light scatter strength:40657} orthogonal light scatter, and the following immunophenotype: CD5 ({+/-:40630}), CD10 ({+/-:40630}), CD19 ({+/-:40630}), and CD20 ({+/-:40630})'
    )
    assert (
        generate_report_template(
            ip_channels=[
                'FSC-A',
                'SSC-A',
                'CD5',
                'CD10',
                'CD19',
                'CD20',
                'Kappa',
                'Lambda',
            ],
            percent=0.0003,
        )
        == 'Immunophenotypic analysis reveals a population of {cell lineage selection:40658} cells (0.03% of total events) with {light scatter strength:40657} forward light scatter, {light scatter strength:40657} orthogonal light scatter, and the following immunophenotype: CD5 ({+/-:40630}), CD10 ({+/-:40630}), CD19 ({+/-:40630}), CD20 ({+/-:40630}), {surface/IC:46754} kappa light chain ({+/-:40630}), and {surface/IC:46754} lambda light chain ({+/-:40630})'
    )
    assert (
        generate_report_template(
            ip_channels=[
                'FSC-A',
                'SSC-A',
                'CD5',
                'CD10',
                'CD19',
                'CD20',
                'Kappa',
                'Lambda',
            ],
            percent=None,
        )
        == 'Immunophenotypic analysis reveals a population of {cell lineage selection:40658} cells (***% of total events) with {light scatter strength:40657} forward light scatter, {light scatter strength:40657} orthogonal light scatter, and the following immunophenotype: CD5 ({+/-:40630}), CD10 ({+/-:40630}), CD19 ({+/-:40630}), CD20 ({+/-:40630}), {surface/IC:46754} kappa light chain ({+/-:40630}), and {surface/IC:46754} lambda light chain ({+/-:40630})'
    )


def test_add_marker_smartlist():
    assert _add_marker_smartlist('CD5') == 'CD5 ({+/-:40630})'
    assert _add_marker_smartlist('CD10') == 'CD10 ({+/-:40630})'
    assert _add_marker_smartlist('TRBC1') == 'TRBC1 ({+/-:40630})'
    assert (
        _add_marker_smartlist('Kappa')
        == '{surface/IC:46754} kappa light chain ({+/-:40630})'
    )


def test_join_list():
    assert _join_list(['CD5', 'CD10', 'CD20']) == 'CD5, CD10, and CD20'
    assert _join_list(['CD5', 'CD10']) == 'CD5 and CD10'
    assert _join_list(['CD5']) == 'CD5'
    assert _join_list([]) == ''
