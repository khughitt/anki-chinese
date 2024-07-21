import re
import stanza
from typing import Any
from ankichinese import COMMON_WORDS

def load_text(infile:str) -> list[str]:
    """Parses input text and returns a list of lines from the file with punctuation and
    extra white-space removed"""
    # load text
    with open(infile) as fp:
        text = fp.read()

    # split sentences
    sentences = re.split(r"[！？…｡。\.\?!]", text)

    # strip empty sentences and newline characters
    sentences = [x.strip() for x in sentences]

    # remove any remaining empty sentences
    sentences = [x for x in sentences if x != ""]

    return sentences

def tokenize_text(lines:list[str], nlp:stanza.pipeline.core.Pipeline) -> dict[str, dict[str,Any]]:
    """Uses Stanza to tokenize input chinese text"""
    tokens:dict[str, dict[str,Any]] = {}

    for line in lines:
        # since we are parsing single sentences, each result is of length 1
        entries = nlp(line).to_dict()[0]

        # iterate over tokens and add unique ones
        for token in entries:            

            # skip common words
            if token["text"] in COMMON_WORDS:
                continue

            # skip tokens starting with "不", "一", "有"
            if token["text"][0] in ["不", "一", "有"]:
                continue

            # skip tokens ending in "了"
            if token["text"][-1] == "了":
                continue

            # skip tokens including english letters/numbers/punctuation
            eng_regex = re.compile(r"[a-zA-Z0-9\[\]\{\}\(\)`~\-_=\.\?\+!@#\$%^&\*\|\\/,<>:;'\"]+")

            if eng_regex.search(token["text"]) is not None:
                continue

            # skip tokens including double-width punctuation
            # https://stackoverflow.com/questions/36640587/how-to-remove-chinese-punctuation-in-python
            punc_chars = (
                '"！？｡。＂＃＄％＆＇（）＊＋，－·／：；＜＝＞＠［＼］＾＿｀｛｜｝～｟｠｢｣､、〃》「」『』【】〔〕〖〗〘〙〚〛〜〝〞〟〰〾〿–—‘’‛“”„‟…‧﹏'
            )
            punc_regex = re.compile(r"[%s]+" % punc_chars)

            if punc_regex.search(token["text"]) is not None:
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

