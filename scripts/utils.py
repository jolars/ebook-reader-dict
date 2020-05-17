"""Utilities for internal use."""
import re
from functools import lru_cache
from typing import Tuple
from warnings import warn

from .lang import (
    pattern_file,
    templates_italic,
    templates_ignored,
    templates_multi,
    templates_other,
    template_warning_skip,
)
from . import constants as C
from .user_functions import *  # noqa


def guess_prefix(word: str) -> str:
    """Determine the word prefix for the given *word*.

    Inspiration: https://github.com/pettarin/penelope/blob/master/penelope/prefix_kobo.py#L16
    Inspiration: https://pgaskin.net/dictutil/dicthtml/prefixes.html
    Inspiration: me ᕦ(ò_óˇ)ᕤ

    Note: for words like "°GL", the Kobo will first check "11.html" and then "gl.html",
          so to speed-up the lookup, let's store such words into "11.html".

    Here are some debug logs to help understand what Kobo does:

        (dictionary.debug) got alternative search terms: "°GL", "°gl", "GL" for word "°GL"
        (ui.debug) static QByteArray Unzipper::extractFile() "/mnt/onboard/.kobo/dict/dicthtml-fr.zip", "11.html")

        (dictionary.debug) got alternative search terms: "X temps", "x temps", "X TEMPS", "Xtemps" for word "X temps"
        (ui.debug) static QByteArray Unzipper::extractFile("/mnt/onboard/.kobo/dict/dicthtml-fr.zip", "xa.html")

        (dictionary.debug) got alternative search terms: "A/cm2", "a/cm2", "A/CM2", "Acm2" for word "A/cm2"
        (ui.debug) static QByteArray Unzipper::extractFile("/mnt/onboard/.kobo/dict/dicthtml-fr.zip", "11.html")

        (dictionary.debug) got alternative search terms: ".vi", ".VI", "vi" for word ".vi"
        (ui.debug) static QByteArray Unzipper::extractFile("/mnt/onboard/.kobo/dict/dicthtml-fr.zip", "11.html")

        >>> guess_prefix("test")
        'te'
        >>> guess_prefix("a")
        'aa'
        >>> guess_prefix("aa")
        'aa'
        >>> guess_prefix("aaa")
        'aa'
        >>> guess_prefix("Èe")
        'èe'
        >>> guess_prefix("multiple words")
        'mu'
        >>> guess_prefix("àççèñts")
        'àç'
        >>> guess_prefix("à")
        'àa'
        >>> guess_prefix("ç")
        'ça'
        >>> guess_prefix("")
        '11'
        >>> guess_prefix(" ")
        '11'
        >>> guess_prefix(" x")
        'xa'
        >>> guess_prefix(" 123")
        '11'
        >>> guess_prefix("42")
        '11'
        >>> guess_prefix("x 23")
        'xa'
        >>> guess_prefix("дaд")
        'дa'
        >>> guess_prefix("未未")
        '11'
        >>> guess_prefix("未")
        '11'
        >>> guess_prefix(" 未")
        '11'
        >>> guess_prefix(".vi")
        '11'
        >>> guess_prefix("/aba")
        '11'
        >>> guess_prefix("a/b")
        '11'
        >>> guess_prefix("’alif")
        '11'
        >>> guess_prefix("°GL")
        '11'
        >>> guess_prefix("وهيبة")
        '11'
    """
    prefix = word.strip()[:2].lower().strip()
    if not prefix or prefix[0].isnumeric():
        return "11"
    return (
        prefix.ljust(2, "a")
        if all(c.isalpha() and c.islower() for c in prefix)
        else "11"
    )


def clean(word: str, text: str) -> str:
    """Cleans up the provided Wikicode.
    Removes templates, tables, parser hooks, magic words, HTML tags and file embeds.
    Keeps links.
    Source: https://github.com/macbre/mediawiki-dump/blob/3f1553a/mediawiki_dump/tokenizer.py#L8

        >>> clean("foo", "{{unknown}}")
        '<i>(Unknown)</i>'
        >>> clean("foo", "<span style='color:black'>[[♣]]</span>")
        "<span style='color:black'>♣</span>"
        >>> clean("foo", "{{foo|{{bar}}|123}}")
        ''
        >>> clean("foo", "<ref>{{Import:CFC}}</ref>")
        ''
        >>> clean("foo", '<ref name="CFC" />')
        ''
        >>> clean("foo", '<ref name="CFC">{{Import:CFC}}</ref>')
        ''
        >>> clean("foo", "''italic''")
        '<i>italic</i>'
        >>> clean("foo", "'''strong'''")
        '<b>strong</b>'
        >>> clean("foo", "''italic and '''strong'''''")
        '<i>italic and <b>strong</b></i>'
        >>> clean("aux", "''Contraction de [[préposition]] ''[[à]]'' et de l'[[article]] défini ''[[les]]'' .''")
        "<i>Contraction de préposition </i>à<i> et de l'article défini </i>les<i>.</i>"
        >>> clean("aux", "'''Contraction de [[préposition]] '''[[à]]''' et de l'[[article]] défini '''[[les]]''' .'''")
        "<b>Contraction de préposition </b>à<b> et de l'article défini </b>les<b>.</b>"
        >>> clean("μGy", "[[Annexe:Principales puissances de 10|10{{e|&minus;6}}]] [[gray#fr-nom|gray]]")
        '10<sup>-6</sup> gray'
        >>> clean("base", "[[Fichier:Blason ville .svg|vignette|120px|'''Base''' d’or ''(sens héraldique)'']]")
        ''
    """

    # Speed-up lookup
    sub = re.sub

    # HTML
    # '''foo''' -> <b>foo></b> (source: https://stackoverflow.com/a/54388869/1117028)
    text = sub(r"'''([^']*(?:'[^']+)*)'''", "<b>\\1</b>", text)
    # ''foo'' -> <i>foo></i>
    text = sub(r"''([^']*(?:'[^']+)*)''", "<i>\\1</i>", text)
    # <br> / <br /> -> ''
    text = sub(r"<br[^>]+/?>", "", text)
    # HTML characters
    text = text.replace("&minus;", "-")

    # Files
    # (see https://stackoverflow.com/a/10591106/1117028 for benchmark)
    file = "|".join("(?:%s)" % p for p in pattern_file)
    text = sub(fr"\[\[{file}:[^\]]+\]\]", "", text)

    # Local links
    text = sub(r"\[\[([^|\]]+)\]\]", "\\1", text)  # [[a]] -> a
    text = sub(r"\[\[[^|]+\|([^\]]+)\]\]", "\\1", text)  # [[a|b]] -> b

    text = text.replace("[[", "").replace("]]", "")

    # Tables
    text = sub(r"{\|[^}]+\|}", "", text)  # {|foo..|}

    # Headings
    text = sub(
        r"^=+\s?([^=]+)\s?=+",
        lambda matches: matches.group(1).strip(),
        text,
        flags=re.MULTILINE,
    )  # == a == -> a

    # Files and other links with namespaces
    text = sub(r"\[\[[^:\]]+:[^\]]+\]\]", "", text)  # [[foo:b]] -> ''

    # External links
    text = sub(
        r"\[http[^\s]+ ([^\]]+)\]", "\\1", text
    )  # [[http://example.com foo]] -> foo
    text = sub(r"https?://[^\s]+", "", text)  # remove http://example.com

    # Parser hooks
    # <ref>foo</ref> -> ''
    # <ref name="CFC"/> -> ''
    # <ref name="CFC">{{Import:CFC}}</ref> -> ''
    text = sub(r"<ref[^>]*/?>(?:.+</ref>)?", "", text)

    # Lists
    text = sub(r"^\*+\s?", "", text, flags=re.MULTILINE)

    # Magic words
    text = sub(r"__\w+__", "", text)  # __TOC__

    # Remove extra quotes left
    text = text.replace("''", "")

    # Templates
    # {{foo}}
    # {{foo|bar}}
    # {{foo|{{bar}}|123}}
    # {{foo|{{bar|baz}}|123}}

    # Simplify the parsing logic: this line will return a list of nested templates.
    for tpl in set(re.findall(r"({{[^{}]*}})", text)):
        # Transform the nested template.
        # This will remove any nested templates from the original text.
        text = text.replace(tpl, transform(word, tpl[2:-2]))

    # Now that all nested templates are done, we can process top-level ones
    while "{{" in text:
        start = text.find("{{")
        pos = start + 2
        subtext = ""

        while pos < len(text):
            if text[pos : pos + 2] == "}}":
                # We hit the end of the template
                pos += 1
                break

            # Save the template contents
            subtext += text[pos]
            pos += 1

        # The template is now completed
        transformed = transform(word, subtext)
        text = f"{text[:start]}{transformed}{text[pos + 1 :]}"

    # Remove extra spaces
    text = sub(r"\s{2,}", " ", text)
    text = sub(r"\s{1,}\.", ".", text)

    return text.strip()


def transform(word: str, template: str) -> str:
    """Convert the data from the *template" template.
    This function also checks for template style.

        >>> transform("foo", "w|ISO 639-3")
        'ISO 639-3'
        >>> transform("foo spaces", "w | ISO 639-3")
        'ISO 639-3'
    """

    parts_raw = template.split("|")
    parts = [p.strip() for p in parts_raw]
    tpl = parts[0]

    # Help fixing formatting on Wiktionary (some templates are more complex and cannot be fixed)
    if parts != parts_raw and tpl not in template_warning_skip[C.LOCALE]:
        warn(f"Extra spaces found in the Wikicode of {word!r} (parts={parts_raw})")

    # Convert *parts* from a list to a tuple because list are not hashable and thus cannot be used
    # with the LRU cache.
    return transform_apply(tpl, tuple(parts))


@lru_cache(maxsize=None)
def transform_apply(tpl: str, parts: Tuple[str, ...]) -> str:
    """Convert the data from the *template" template.

        >>> transform("foo", "w|ISO 639-3")
        'ISO 639-3'
        >>> transform("test", "w|Gesse aphaca|Lathyrus aphaca")
        'Lathyrus aphaca'
        >>> transform("foo", "grammaire|fr")
        '<i>(Grammaire)</i>'
        >>> transform("foo", "conj|grp=1|fr")
        ''
    """
    if tpl in templates_ignored[C.LOCALE]:
        return ""

    # {{w|ISO 639-3}} -> ISO 639-3
    # {{w|Gesse aphaca|Lathyrus aphaca}} -> Lathyrus aphaca
    if tpl == "w":
        return parts[-1]

    if tpl in templates_multi[C.LOCALE]:
        res: str = eval(templates_multi[C.LOCALE][tpl])
        return res

    if tpl in templates_italic[C.LOCALE]:
        return f"<i>({templates_italic[C.LOCALE][tpl]})</i>"

    if tpl in templates_other[C.LOCALE]:
        return templates_other[C.LOCALE][tpl]

    # {{grammaire|fr}} -> (Grammaire)
    if len(parts) == 2:
        return f"<i>({capitalize(tpl)})</i>"  # noqa

    # {{conj|grp=1|fr}} -> ''
    if len(parts) > 2:
        return ""

    # May need custom handling in lang/$LOCALE.py
    return f"<i>({capitalize(tpl)})</i>" if tpl else ""  # noqa
