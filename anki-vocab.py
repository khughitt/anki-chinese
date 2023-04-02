#!/usr/bin/env python3
#
# anki chinese flashcard generator
# keith hughitt (aug 2020)
#
import argparse
import os
import re
import time
from typing import Any
import stanza
import pandas as pd
from zhon import pinyin
from dragonmapper import hanzi
from hanziconv import HanziConv
from subprocess import PIPE, Popen
from dragonmapper import hanzi

# common words to exclude (a _very_ incomplete list..)
COMMON_WORDS = [
    "一",
    "二",
    "三",
    "四",
    "五",
    "六",
    "七",
    "八",
    "九",
    "十",
    "一些",
    "一定",
    "一樣",
    "上",
    "下",
    "不",
    "不是",
    "不會",
    "不能",
    "中",
    "也",
    "事",
    "人",
    "什麼",
    "他",
    "他們",
    "你",
    "你們",
    "來",
    "個",
    "做",
    "先生",
    "兩",
    "再",
    "分",
    "到",
    "十分",
    "去",
    "又",
    "口",
    "叫",
    "可",
    "可以",
    "可是",
    "告訴",
    "呢",
    "和",
    "啊",
    "嗎",
    "四",
    "因為",
    "在",
    "多",
    "多麼",
    "大",
    "天",
    "她",
    "好",
    "它",
    "對",
    "小",
    "就",
    "就是",
    "已",
    "已經",
    "幾",
    "張",
    "很",
    "後",
    "得",
    "從",
    "應",
    "我",
    "我們",
    "把",
    "是",
    "時",
    "時間",
    "最",
    "會",
    "有",
    "朋友",
    "東西",
    "機會",
    "次",
    "比",
    "沒有",
    "為",
    "現在",
    "的",
    "看",
    "看到",
    "真",
    "知道",
    "第一",
    "給",
    "而",
    "能夠",
    "自己",
    "被",
    "裏",
    "要",
    "見",
    "話",
    "說",
    "讓",
    "起來",
    "跟",
    "這",
    "這樣",
    "過",
    "還",
    "那",
    "那些",
    "那麼",
    "都",
    "馬上",
    "點",
    "能",
    "還是",
    "打",
    "氣",
    "前",
    "車子",
    "二早",
    "明白",
    "這話",
    "往",
    "每個",
    "或",
    "如",
    "杯",
    "作",
    "不得",
    "大小",
    "找到",
    "毛",
    "一下",
    "哪",
    "日",
    "名",
    "一些",
    "成",
    "個人",
    "以",
    "也是",
    "有人",
]


def parse_args():
    parser = argparse.ArgumentParser(
        description="Generate Anki Chinese vocabulary flashcards for a given text."
    )

    parser.add_argument(
        "infile",
        metavar="INFILE",
        type=str,
        help="path to .txt input text to be parsed",
    )
    parser.add_argument(
        "outfile",
        metavar="OUTFILE",
        type=str,
        default="vocab.tsv",
        help="path to store processed flashcards in",
    )
    parser.add_argument(
        "--append",
        "-a",
        action="store_true",
        help="If set, vocab will be appended to output file, if it already exists.",
    )
    parser.add_argument(
        "--convert",
        "-c",
        action="store_true",
        help="If set, input text will be converted to the specified output format (traditional/simplified)",
    )
    parser.add_argument(
        "--format",
        "-f",
        type=str,
        choices=["traditional", "simplified"],
        default="traditional",
        help="Format to use for vocab cards: traditional / simplified (default: traditional)",
    )

    # parse command line args
    args = parser.parse_args()

    # check to make sure input file exists
    if not os.path.exists(args.infile):
        raise Exception("Specified input file cannot be found!")

    return args


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


def add_pinyin_tone_html(pinyin_word:str) -> str:
    """Detects the tone of pinyin for a single character and generates a corresponding
    <span> block"""
    tone1_re = re.compile("[āēīōūǖ]")
    tone2_re = re.compile("[áéíóúǘ]")
    tone3_re = re.compile("[ǎěǐǒǔǚ]")
    tone4_re = re.compile("[àèìòùǜ]")

    if len(tone1_re.findall(pinyin_word)) > 0:
        return f"<span class='tone1'>{pinyin_word}</span>"
    if len(tone2_re.findall(pinyin_word)) > 0:
      return f"<span class='tone2'>{pinyin_word}</span>"
    if len(tone3_re.findall(pinyin_word)) > 0:
      return f"<span class='tone3'>{pinyin_word}</span>"
    if len(tone4_re.findall(pinyin_word)) > 0:
      return f"<span class='tone4'>{pinyin_word}</span>"
    else:
      return f"<span class='tone5'>{pinyin_word}</span>"


def get_pinyin(chinese_phrase:str) -> tuple:
    # first, query pinyin for complete phrase
    pinyin_phrase = hanzi.to_pinyin(chinese_phrase)

    # split by syllable and add relevant html container elements
    # e.g. "niǔdài" -> ['niǔ', 'dài']
    pinyin_parts = re.findall(pinyin.syllable, pinyin_phrase)

    pinyin_html = "".join([add_pinyin_tone_html(x) for x in pinyin_parts])

    return (pinyin_phrase, pinyin_html)


def load_text(infile:str) -> list[str]:
    """Parses input text and returns a list of lines from the file with punctuation and
    extra white-space removed"""
    # load text
    with open(infile) as fp:
        lines = fp.readlines()

    # strip english letters, punctuation, and numbers
    eng_regex = r"[a-zA-Z0-9\[\]\{\}\(\)`~\-_=\.\?\+!@#\$%^&\*\|\\/,<>:;'\"]+"

    lines = [re.sub(eng_regex, "", x) for x in lines]

    # strip punctuation (double-width)
    # https://stackoverflow.com/questions/36640587/how-to-remove-chinese-punctuation-in-python
    punc_chars = (
        '"！？｡。＂＃＄％＆＇（）＊＋，－·／：；＜＝＞＠［＼］＾＿｀｛｜｝～｟｠｢｣､、〃》「」『』【】〔〕〖〗〘〙〚〛〜〝〞〟〰〾〿–—‘’‛“”„‟…‧﹏'
    )
    punc_regex = r"[%s]+" % punc_chars

    lines = [re.sub(punc_regex, "", x) for x in lines]

    # strip empty lines and newline characters
    lines = [x.strip() for x in lines if x != "\n"]

    # remove any remaining empty lines
    lines = [x for x in lines if x != ""]

    return lines


def tokenize_text(lines:list[str], nlp:stanza.pipeline.core.Pipeline, common_words:list[str]) -> dict[str, dict[str,Any]]:
    """Uses Stanza to tokenize input chinese text"""
    tokens:dict[str, dict[str,Any]] = {}

    for line in lines:
        # since we are parsing single sentences, each result is of length 1
        entries = nlp(line).to_dict()[0]

        # iterate over tokens and add unique ones
        for token in entries:
            
            if token["text"] in common_words:
                continue

            # new token
            if token["text"] not in tokens:
                tokens[token["text"]] = {
                    "token": token["text"],
                    "sentences": [line],
                    "start_positions": [token["start_char"]],
                    "end_positions": [token["end_char"]]
                }
            else:
                # new sentence
                tokens[token["text"]]["sentences"].append(line)
                tokens[token["text"]]["start_positions"].append(token["start_char"])
                tokens[token["text"]]["end_positions"].append(token["end_char"])

    return tokens

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
        raise f"Unable to translate {chinese}. Exiting..."

    return trans

def parse_translate_result(raw_trans:str) -> dict[str,Any]:
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
    bold_regex = re.compile("<b>\s+")
    space_regex = re.compile("<br />\s+")

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

        for i, line in enumerate(defn_lines):
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


#
# MAIN
#
if __name__ == "__main__":
    # parse command-line arguments
    args = parse_args()

    # download traditional chinese language model
    print("Loading Stanza...")
    stanza.download("zh-hant")

    # initialize pipeline
    nlp = stanza.Pipeline("zh-hant", processors="tokenize")

    # parse input text
    lines = load_text(args.infile)

    # if append is set to True, check for and load existing output file
    dat = None

    if args.append and os.path.exists(args.outfile):
        print("Appending to existing file...")
        dat = pd.read_csv(args.outfile, sep="\t")

    # convert from simplified -> traditional chinese, if requested
    if args.convert:
        if args.format == "traditional":
            lines = [HanziConv.toTraditional(x) for x in lines]
        else:
            lines = [HanziConv.toSimplified(x) for x in lines]

    # detect words and phrases in text
    print("Extracting individual words...")
    tokens = tokenize_text(lines, nlp, COMMON_WORDS)

    # if appending to existing output, skip tokens that are already present
    if dat is not None:
        for word in dat.chinese:
            if word in tokens:
                del tokens[word]

    print(f"Translating {len(tokens)} unique words...")

    # list to store result entries in
    result = []

    # iterate over words and add translations, etc.
    for i, chinese in enumerate(tokens):
        print("Processing %s...[%d/%d]" % (chinese, i + 1, len(tokens)))

        token_dict = tokens[chinese]

        trans = translate_chinese(chinese, args.format)
        entry = parse_translate_result(trans)

        # add sentence(s) where the word appears
        sentence_text = ""
        sentence_html = ""

        for j, sentence in enumerate(token_dict["sentences"]):
            # may not be the correct punctuation, but good enough for now..
            sentence_text += sentence + "。<br />"
            
            start = token_dict["start_positions"][j]
            end = token_dict["end_positions"][j]

            sentence_html += sentence[:start] + "<span class='highlight'>"
            sentence_html += chinese + "</span>"
            sentence_html += sentence[end:] + "。<br />"
        
        entry["sentences"] = sentence_text
        entry["sentences_html"] = sentence_html

        result.append(entry)

        # periodically update output table; this way progress can be saved in case a failure is
        # encountered at some point
        if i % 25 == 0:
            print("Saving progress...")
            # convert to a pandas dataframe and store result
            if dat is None:
                dat = pd.DataFrame(result)
            else:
                dat = pd.concat([dat, pd.DataFrame(result)])

            # testing (includes raw ansi output from translate-shell)
            dat.set_index("chinese").to_csv(
                args.outfile.replace(".tsv", "-debug.tsv"), sep="\t"
            )

            # anki result
            anki_dat = dat[
                ["chinese", "pinyin_html", "english_long", "definition_html", "sentences_html"]
            ]

            anki_dat.set_index("chinese").to_csv(args.outfile, header=False, sep="\t")

            result = []

    # convert to a pandas dataframe and store result
    if dat is None:
        dat = pd.DataFrame(result)
    else:
        dat = pd.concat([dat, pd.DataFrame(result)])

    # testing (includes raw ansi output from translate-shell)
    dat.set_index("chinese").to_csv(
        args.outfile.replace(".tsv", "-debug.tsv"), sep="\t"
    )

    # anki result
    anki_dat = dat[["chinese", "pinyin_html", "english_long", "definition_html", "sentences_html"]]

    anki_dat.set_index("chinese").to_csv(args.outfile, header=False, sep="\t")
