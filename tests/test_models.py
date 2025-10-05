"""JobSpec モデル関連のテスト。"""

from __future__ import annotations

from pptx_generator.models import ChartOptions, ChartSeries, JobAuth, JobMeta, JobSpec, Slide, SlideChart, SlideTable, TableStyle


def test_job_spec_accepts_tables_and_charts() -> None:
    spec = JobSpec(
        meta=JobMeta(schema_version="1.0", title="提案書"),
        auth=JobAuth(created_by="tester"),
        slides=[
            Slide(
                id="slide-1",
                layout="Title and Content",
                tables=[
                    SlideTable(
                        id="table-1",
                        columns=["項目", "値"],
                        rows=[["A", 1], ["B", 2]],
                        style=TableStyle(header_fill="#112233", zebra=True),
                    )
                ],
                charts=[
                    SlideChart(
                        id="chart-1",
                        type="column",
                        categories=["Before", "After"],
                        series=[
                            ChartSeries(name="効果", values=[10, 5], color_hex="#abcdef"),
                        ],
                        options=ChartOptions(data_labels=True, y_axis_format="{0}%"),
                    )
                ],
            )
        ],
    )

    table = spec.slides[0].tables[0]
    chart = spec.slides[0].charts[0]

    assert table.style is not None
    assert table.style.header_fill == "#112233"
    assert chart.series[0].color_hex == "#abcdef"
    assert chart.options is not None
    assert chart.options.data_labels is True
