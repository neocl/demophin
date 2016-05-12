#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging

try:
    import MeCab
except:
    logging.error("MeCab not found")
    
MECAB_OBJ = None
JAP_PUNCT=u"!\"!&'()*+,-−./;<=>?@[\]^_`{|}~。！？…．　○●◎＊☆★◇◆"
    
def getMecab():
    global MECAB_OBJ
    if not MECAB_OBJ:
        MECAB_OBJ = MeCab.Tagger('-O chasen')
    return MECAB_OBJ

def get_ace_input(sent):
    return "".join(jp2yy(sent))

def jp2yy (sent):
    """take a Japanese sentence in UTF8 convert to YY-mode using mecab"""
    ### (id, start, end, [link,] path+, form [surface], ipos, lrule+[, {pos p}+])
    ### set ipos as lemma (just for fun)
    ### fixme: do the full lattice
    yid = 0
    start = 0
    cfrom = 0
    cto = 0
    yy = list()
    parse_result = getMecab().parse(sent)
    print(parse_result)
    for tok in parse_result.split('\n'):
        if tok and tok != 'EOS':
            ##print tok
            (form, p, lemma, p1, p2, p3) = tok.split('\t')
            if form in JAP_PUNCT:
                continue
            p2 = p2 or 'n'
            p3 = p3 or 'n'
            # pos = '-'.join([p1, p2, p3])
            pos = "%s:%s-%s" % (p1, p2, p3) ## wierd format jacy requires
            cfrom = sent.find(form, cto)    ## first instance after last token
            cto = cfrom + len(form)         ## find the end
            yy.append('(%d, %d, %d, <%d:%d>, 1, "%s", %s, "null", "%s" 1.0)' % \
                (yid, start, start +1, cfrom, cto, form, 0, pos))
            yid += 1
            start += 1
    return yy

def main():
    pass

if __name__ == '__main__':
    main()
