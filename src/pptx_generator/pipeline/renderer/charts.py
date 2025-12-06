from __future__ import annotations

import logging

from pptx.chart.data import CategoryChartData
from pptx.enum.chart import XL_CHART_TYPE

from ...models import ChartSeries, Slide, SlideChart, TemplateChartDefaults
from .layout import LayoutBox

logger = logging.getLogger(__name__)


class ChartMixin:
    def _apply_charts(self, slide, slide_spec: Slide) -> None:
        if not slide_spec.charts:
            return

        chart_defaults = self._style.chart
        for chart_spec in slide_spec.charts:
            self._render_single_chart(slide, slide_spec, chart_spec, chart_defaults)

    def _render_single_chart(
        self,
        slide,
        slide_spec: Slide,
        chart_spec: SlideChart,
        chart_defaults: TemplateChartDefaults,
    ) -> None:
        if not chart_spec.series:
            logger.debug("チャート '%s' に系列がないためスキップ", chart_spec.id)
            return

        data = self._build_chart_data(chart_spec)
        chart_type = self._resolve_chart_type(chart_spec.type)
        fallback_box = self._determine_chart_fallback_box(chart_defaults)
        element_label = chart_spec.id or (chart_spec.anchor or "chart")
        resolution = self._resolve_anchor(
            slide,
            chart_spec.anchor,
            fallback_box,
            owner_description=f"チャート要素 '{element_label}' (slide_id='{slide_spec.id}')",
        )
        anchor_shape = resolution.shape
        if resolution.is_placeholder:
            self._prepare_placeholder(anchor_shape)

        left, top, width, height = resolution.as_box()
        chart_shape = slide.shapes.add_chart(
            chart_type,
            left,
            top,
            width,
            height,
            data,
        )
        chart = chart_shape.chart

        self._apply_chart_series_colors(chart.series, chart_spec.series, chart_defaults)
        self._style_chart(chart, chart_spec.options, chart_defaults)

        if anchor_shape is not None:
            self._remove_shape(anchor_shape)

    def _build_chart_data(self, chart_spec: SlideChart) -> CategoryChartData:
        data = CategoryChartData()
        categories = chart_spec.categories
        if not categories and chart_spec.series:
            categories = [
                str(index + 1) for index in range(len(chart_spec.series[0].values))
            ]
        data.categories = categories or []
        for series in chart_spec.series:
            data.add_series(series.name, series.values)
        return data

    def _determine_chart_fallback_box(
        self, chart_defaults: TemplateChartDefaults
    ) -> LayoutBox:
        default_box = chart_defaults.fallback_box
        if default_box is not None:
            return LayoutBox(
                default_box.left_in,
                default_box.top_in,
                default_box.width_in,
                default_box.height_in,
            )
        return LayoutBox(1.0, 1.5, 8.5, 4.0)

    def _resolve_chart_type(self, chart_type: str) -> XL_CHART_TYPE:
        mapping = {
            "column": XL_CHART_TYPE.COLUMN_CLUSTERED,
            "bar": XL_CHART_TYPE.BAR_CLUSTERED,
            "line": XL_CHART_TYPE.LINE_MARKERS,
            "pie": XL_CHART_TYPE.PIE,
        }
        return mapping.get(chart_type.lower(), XL_CHART_TYPE.COLUMN_CLUSTERED)

    def _apply_chart_series_colors(
        self,
        chart_series,
        series_specs: list[ChartSeries],
        defaults: TemplateChartDefaults,
    ) -> None:
        palette = list(defaults.palette)
        if not palette:
            palette = [
                self._style.colors.accent,
                self._style.colors.primary,
                self._style.colors.secondary,
            ]
        for index, (series, spec) in enumerate(
            zip(chart_series, series_specs, strict=False)
        ):
            fill = series.format.fill
            fill.solid()
            color = spec.color_hex or palette[index % len(palette)]
            fill.fore_color.rgb = self._color_from_hex(color)

    def _style_chart(
        self, chart, options, defaults: TemplateChartDefaults
    ) -> None:
        labels_enabled, labels_format = self._resolve_chart_label_settings(
            options, defaults
        )
        self._apply_chart_data_labels(chart, labels_enabled, labels_format)
        self._apply_chart_axis_number_format(chart, labels_format)
        self._apply_chart_axes_font(chart, defaults.axis_font or self._style.body_font)
        self._configure_chart_legend(chart)

    def _resolve_chart_label_settings(
        self, options, defaults: TemplateChartDefaults
    ) -> tuple[bool, str | None]:
        labels_enabled = defaults.data_labels_enabled
        labels_format = defaults.data_labels_format
        if options is not None:
            labels_enabled = options.data_labels
            labels_format = options.y_axis_format or labels_format
        return bool(labels_enabled), labels_format

    def _apply_chart_data_labels(
        self,
        chart,
        labels_enabled: bool,
        labels_format: str | None,
    ) -> None:
        for plot in chart.plots:
            plot.has_data_labels = labels_enabled
            if not plot.has_data_labels:
                continue
            data_labels = plot.data_labels
            data_labels.show_value = True
            if labels_format:
                data_labels.number_format = labels_format

    @staticmethod
    def _color_from_hex(value: str):
        from pptx.dml.color import RGBColor

        return RGBColor.from_string(value.lstrip("#"))
