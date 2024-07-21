"""
anki-chinese CLI
"""
import os
import stanza
import argparse
import pandas as pd
from hanziconv import HanziConv
from ankichinese.tokenizer import load_text, tokenize_text
from ankichinese.translate import translate_chinese, parse_translate_result

class CLI():
    def __init__(self):
        """
        """
        # parse command-line arguments
        args = self.parse_args()

        print("Loading Stanza...")

        # download traditional chinese language model
        if args.format == "traditional":
            lang = "zh-hant"
        else:
            lang = "zh"

        stanza.download(lang)

        # initialize pipeline
        nlp = stanza.Pipeline(lang, processors="tokenize")

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
                trans_lines = []

                for line in lines:
                    trans = HanziConv.toTraditional(line)

                    # fix common mistranslations
                    trans = trans.replace("瞭", "了")
                    trans = trans.replace("彆", "别")
                    trans = trans.replace("齣", "出")

                    trans_lines.append(trans)

                lines = trans_lines
            else:
                lines = [HanziConv.toSimplified(x) for x in lines]

        # detect words and phrases in text
        print("Extracting individual words...")
        tokens = tokenize_text(lines, nlp)

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
            entry = parse_translate_result(trans, chinese)

            # add sentence(s) where the word appears
            sentence_text = ""
            sentence_html = ""

            # keep track of sentences to avoid adding the same one multiple times when a word is present
            # more than one
            sentences_seen = []

            for j, sentence in enumerate(token_dict["sentences"]):
                if sentence in sentences_seen:
                    continue
                else:
                    sentences_seen.append(sentence)

                # remove any stray newlines due to uncommon sentence delimiters
                sentence = sentence.replace("\n", "")
                
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

        # anki result
        anki_dat = dat[["chinese", "pinyin_html", "english_long", "definition_html", "sentences_html"]]

        anki_dat.set_index("chinese").to_csv(args.outfile, header=False, sep="\t")

    def parse_args(self):
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


def run():
    """Initialize and run CLI"""
    CLI()
