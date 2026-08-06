"""Unit tesztek a cli.banner modulhoz."""

from __future__ import annotations

from hangoskonyv.cli.banner import render_banner


class TestRenderBanner:
    def test_all_lines_have_equal_width(self) -> None:
        banner = render_banner()
        lines = banner.split("\n")
        widths = {len(line) for line in lines}
        assert len(widths) == 1, f"Nem egyforma hosszú sorok: {widths}"

    def test_starts_and_ends_with_box_border(self) -> None:
        lines = render_banner().split("\n")
        assert lines[0].startswith("┌") and lines[0].endswith("┐")
        assert lines[-1].startswith("└") and lines[-1].endswith("┘")

    def test_contains_basic_usage_example(self) -> None:
        banner = render_banner()
        assert "hangoskonyv convert konyv.epub --voice-model hang.onnx" in banner

    def test_contains_comma_pauses_example(self) -> None:
        assert "--comma-pauses" in render_banner()

    def test_contains_help_pointer(self) -> None:
        assert "hangoskonyv convert --help" in render_banner()

    def test_every_body_line_wrapped_by_vertical_bars(self) -> None:
        lines = render_banner().split("\n")
        for line in lines[1:-1]:
            assert line.startswith("│ ") and line.endswith(" │")
