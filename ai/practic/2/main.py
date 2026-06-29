import argparse
import json
import sys
from pathlib import Path
from collections import Counter

from parsers.main_document_parser import MainDocumentParser
from parsers.amendment_document_parser import AmendmentDocumentParser
from nodes.base import BaseNode
from nodes.target import TargetAddress

def main():
    data = [
        # {'filename':"/home/aleksandr/development/aleksandrMac/learning/ai/practic/dd/data/md/minstroy_20200804_pr_421_data.md",         'type':'base'},
        {'filename': "/home/aleksandr/development/aleksandrMac/learning/ai/practic/dd/data/md/minstroy_20220707_pr_557-421_data.md",    'type':'amendment'}
    ]
    nodes = []
    for d in data:
        content = Path(d['filename']).read_text(encoding='utf-8')
        doc_parser = AmendmentDocumentParser() if d['type'] == 'amendment' else MainDocumentParser()
        nodes = nodes + doc_parser.parse(content)
        print(len(nodes))
        # print(nodes[10])
        print(nodes)

    


main()