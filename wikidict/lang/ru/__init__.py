"""Russian language."""
from typing import Tuple

# Regex to find the pronunciation
# TODO need to expand template for russian Произношение (rn just get stem)
pronunciation = r"(?:transcriptions-ru.)(\w*)"

# Regex to find the gender
# https://ru.wiktionary.org/wiki/%D0%A8%D0%B0%D0%B1%D0%BB%D0%BE%D0%BD:%D1%81%D1%83%D1%89-ru
gender = r"(?:{сущ.ru.)([fmnмжс])|(?:{сущ.ru.*\|)([fmnмжс])"

# Float number separator
float_separator = ","
# Thousads separator
thousands_separator = " "

# Markers for sections that contain interesting text to analyse.
section_level = 1
section_sublevels = (3, 4)
head_sections = "{{-ru-}}"
etyl_section = ("Этимология",)
sections = (
    *etyl_section,
    "Значение",
    "Семантические свойства",
    "{{Значение}}",
    "{{Семантические свойства}}",
    "Морфологические и синтаксические свойства",
    "Как самостоятельный глагол",  # for verbs with aux
    "В значении вспомогательного глагола или связки",  # for verbs with aux
)

# Some definitions are not good to keep (plural, gender, ... )
templates_ignored = ("семантика",)


def last_template_handler(
    template: Tuple[str, ...], locale: str, word: str = ""
) -> str:

    from .langs import langs
    from ..defaults import last_template_handler as default
    from .template_handlers import render_template, lookup_template

    if lookup_template(template[0]):
        return render_template(template)

    tpl, *parts = template

    # This is a country in the current locale
    if tpl in langs:
        return langs[tpl]

    return default(template, locale, word=word)


# Release content on GitHub
# https://github.com/BoboTiG/ebook-reader-dict/releases/tag/ru
release_description = """\
Количество слов : {words_count}
Экспорт Викисловаря : {dump_date}

Доступные файлы :

- [Kobo]({url_kobo}) (dicthtml-{locale}-{locale}.zip)
- [StarDict]({url_stardict}) (dict-{locale}-{locale}.zip)
- [DictFile]({url_dictfile}) (dict-{locale}-{locale}.df.bz2)

<sub>Обновлено по {creation_date}</sub>
"""  # noqa

# Dictionary name that will be printed below each definition
wiktionary = "Викисловарь (ɔ) {year}"