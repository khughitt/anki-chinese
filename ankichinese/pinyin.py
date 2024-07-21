import re
from zhon import pinyin
from dragonmapper import hanzi

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


