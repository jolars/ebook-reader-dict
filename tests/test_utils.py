import pytest

from scripts import utils


@pytest.mark.parametrize(
    "word, ignored",
    [
        ("accueil", False),
        ("2", True),
        ("22", True),
        ("222", True),
        ("222" * 12, True),
        ("en", True),
        ("", True),
        (" ", True),
    ],
)
def test_is_ignored(word, ignored):
    """Test words filtering."""
    assert utils.is_ignored(word) is ignored


@pytest.mark.parametrize(
    "wikicode, expected",
    [
        ("{{term|ne … guère que}}", "(Ne … guère que)"),
        ("{{term|Avec un mot négatif}} Presque.", "(Avec un mot négatif) Presque."),
        ("{{term|Souvent en [[apposition]]}}", "(Souvent en apposition)"),
        ("{{unknown}}", "(Unknown)"),
    ],
)
def test_clean_template(wikicode, expected):
    assert utils.clean(wikicode) == expected
