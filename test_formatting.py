from sc_telegram_clone.formatting import format_duration, relevance_marker, render_tracks
from sc_telegram_clone.models import Track


def test_format_duration() -> None:
    assert format_duration(104) == "1:44"
    assert format_duration(None) == "?:??"


def test_render_tracks_uses_soundcloud_like_layout() -> None:
    tracks = [
        Track(title="гладиатор/рыцарь", artist="fallen777angel", url="https://soundcloud.com/x", duration=104),
        Track(title="slowed+reverb", artist="Гладиатор/Рыцарь", url="https://soundcloud.com/y", duration=122),
    ]

    text = render_tracks("гладиатор/рыцарь", tracks, page=0, per_page=5)

    assert "‼️ · 1:44" in text
    assert "❗ · 2:02" in text
    assert "гладиатор/рыцарь" in text
    assert "fallen777angel" in text


def test_relevance_markers_are_unique() -> None:
    assert relevance_marker(0) == "‼️"
    assert relevance_marker(1) == "❗"
    assert relevance_marker(2) == ""
    assert relevance_marker(5) == ""
