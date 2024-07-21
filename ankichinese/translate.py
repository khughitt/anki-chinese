import re
import time
from typing import Any
from subprocess import PIPE, Popen
from ankichinese.pinyin import get_pinyin

def query_google_translate(chinese:str, char_format:str) -> str:
    """
    Uses translate-shell to query Google Translate

    Note: google translate api limits users to 600/6000 requests per day..
    https://cloud.google.com/translate/quotas
    """
    # determine input language code to use
    if char_format == "traditional":
        lang_code = "zh-TW"
    else:
        lang_code = "zh-CN"

    # submit query
    proc = Popen(
        f"trans --no-auto {lang_code}:en {chinese}",
        shell=True,
        stdout=PIPE,
        stderr=PIPE,
    )

    stdout, stderr = proc.communicate()

    # check for alternate suggestion message sent to stderr
    if stderr != b"":
        print("Alt suggestion: ", chinese)
        print(stderr.decode("utf-8"))

    # decode response
    trans = stdout.decode("utf-8")

    # if response is empty, raise an exception
    if trans == "\x1b[1m\x1b[22m\n":
        raise Exception(f"Unable to translate: {chinese}.")

    return trans

def translate_chinese(chinese:str, char_format:str) -> str:
    """Translates a single chinese phrase to english"""
    # query api up to 3 times before giving up
    num_tries = 0

    trans = None

    while trans is None and num_tries < 3:
        try:
            trans = query_google_translate(chinese, char_format)
        except Exception as e:
            print(e)
            print(
                "Waiting for an hour and then trying again (try %d...)"
                % (num_tries + 2)
            )

            num_tries = num_tries + 1
            time.sleep(60 * 60)

    # if query failed multiple time, print error message and exit
    if trans is None:
        raise Exception(f"Unable to translate {chinese}. Exiting...")

    return trans

def parse_translate_result(raw_trans:str, chinese:str) -> dict[str,Any]:
    """
    Parses raw result from Google translate API and returns a dictionary of formatted components
    """
    # convert formatting characters ansi -> html
    trans = raw_trans

    trans = trans.replace("\x1b[1m", "<b>")
    trans = trans.replace("\x1b[22m", "</b>")

    trans = trans.replace("\x1b[4m", "<u>")
    trans = trans.replace("\x1b[24m", "</u>")

    # strip unneeded whitespace
    bold_regex = re.compile(r"<b>\s+")
    space_regex = re.compile(r"<br />\s+")

    trans = bold_regex.sub("<b>", trans)
    trans = space_regex.sub("", trans)

    # split translation into separate lines
    lines = [x.strip() for x in trans.split("\n")]

    #
    # extract translation components, ex.:
    #
    #  ['會面',
    #   '(Huìmiàn)',
    #   '',
    #   '<b>meet</b>',
    #   '',
    #   'Definitions of <u>會面</u>',
    #   '[ <u>正體中文</u> -> <b>English</b> ]',
    #   '',
    #   'verb',
    #   '<b>meet</b>',
    #   '滿足, 見, 會面, 見面, 迎接, 會見',
    #   '<b>get together</b>',
    #   '聚會, 聚, 張羅, 聚合, 會, 會面',
    #   '<b>hold a meeting</b>',
    #   '開會, 會合, 會面',
    #   '',
    #   '<u>會面</u>',
    #   '<b>meet</b>, <b>Meet up</b>',
    #   '']
    #
    pinyin_trans = lines[1][1:-1]
    english_short = lines[3]
    english_long = lines[-2]

    # extract remaining definitions, if present
    defn_lines = lines[8:-4]

    defns_plain = []
    defns_html = []

    if len(defn_lines) > 0:
        # iterate over lines of definition section and add raw and html-formatted versions

        for line in defn_lines:
            # part-of-speech headings
            if line == "" or re.match("^[a-z]", line):
                defns_plain.append(line)
                defns_html.append("<span class='pos'>" + line + "</span>")
                continue
            elif re.match("^<[bu]", line):
                # english words / synonyms once
                defns_plain.append("    " + line)
                defns_html.append("<span class='defn-english'>" + line + "</span>")
                continue
            elif line == "":
                continue

            # iterate over words
            defn_words = line.split(", ")

            # lists to store characters with associated pinyin translations
            defn_words_pinyin = []
            defn_words_pinyin_fmt = []

            for defn_word in defn_words:
                defn_pinyin, fmt_pinyin = get_pinyin(defn_word)

                defn_words_pinyin.append(f"{defn_word} ({defn_pinyin})")
                defn_words_pinyin_fmt.append(f"{defn_word} ({fmt_pinyin})")

            # re-combine definition words and add to list
            defns_plain.append("        " + ", ".join(defn_words_pinyin))
            defns_html.append(
                "<span class='defn-chinese'>"
                + ", ".join(defn_words_pinyin_fmt)
                + "</span>"
            )

    # add to results
    _, pinyin_html = get_pinyin(chinese)

    return {
        "chinese": chinese,
        "pinyin": pinyin_trans,
        "pinyin_html": pinyin_html,
        "english_short": english_short,
        "english_long": english_long,
        "definition": "<br />".join(defns_plain),
        "definition_html": "<br />".join(defns_html),
        "raw_translation": raw_trans,
    }

