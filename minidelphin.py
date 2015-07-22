
#
# minidelphin : single-module pyDelphin implementation
#
# Copyright (2015) Michael Wayne Goodman <goodman.m.w@gmail.com>
#
# This file is a subset of pyDelphin. Please see the pyDelphin project
# page for license information:
#   http://github.com/goodmami/pydelphin

from __future__ import print_function

import os
import re
import logging
from collections import (OrderedDict, deque, defaultdict, namedtuple)
from itertools import chain
from subprocess import (check_call, CalledProcessError, Popen, PIPE, STDOUT)

IVARG_ROLE = 'ARG0'
CONSTARG_ROLE = 'CARG'
QUANTIFIER_POS = 'q'
var_re = re.compile(r'^(\w*\D)(\d+)$')


class PyDelphinException(Exception):
    pass


class XmrsError(PyDelphinException):
    pass


class XmrsDeserializationError(XmrsError):
    pass


class Xmrs(object):
    def __init__(self, top=None, index=None, xarg=None,
                 eps=None, hcons=None, icons=None, vars=None,
                 lnk=None, surface=None, identifier=None):
        self.top = top
        self.index = index
        self.xarg = xarg
        self._nodeids = []
        self._eps = {}
        self._hcons = {}
        self._icons = {}
        self._vars = defaultdict(
            lambda: {'props': [], 'refs': defaultdict(list)}
        )

        # just calling __getitem__ will instantiate them on _vars
        if top is not None: self._vars[top]
        if index is not None: self._vars[index]
        if xarg is not None: self._vars[xarg]

        if vars is not None:
            _vars = self._vars
            for var, props in vars.items():
                _vars[var]['props'] = props
        if eps is not None:
            self.add_eps(eps)
        if hcons is not None:
            self.add_hcons(hcons)
        if icons is not None:
            self.add_icons(icons)

        self.lnk = lnk  # Lnk object (MRS-level lnk spans the whole input)
        self.surface = surface  # The surface string
        self.identifier = identifier  # Associates an utterance with the RMRS

    def add_eps(self, eps):
        # (nodeid, pred, label, args, lnk, surface, base)
        _nodeids, _eps, _vars = self._nodeids, self._eps, self._vars
        for ep in eps:
            eplen = len(ep)
            if eplen < 3:
                raise XmrsError(
                    'EPs must have length >= 3: (nodeid, pred, label, ...)'
                )
            nodeid, pred, lbl = ep[0], ep[1], ep[2]
            if nodeid in _eps:
                raise XmrsError(
                    'EP already exists in Xmrs: {} ({})'
                    .format(nodeid, ep[1])
                )
            _nodeids.append(nodeid)
            _eps[nodeid] = ep
            if lbl is not None:
                _vars[lbl]['refs']['LBL'].append(nodeid)
            args = None
            if eplen >= 4: args = ep[3]
            if args is None: args = {}
            for role, val in args.items():
                # if the val is not in _vars, it might still be a
                # variable; check with var_re
                if val in _vars or var_re.match(val):
                    vardict = _vars[val]
                    vardict['refs'][role].append(nodeid)

    def add_hcons(self, hcons):
        # (hi, relation, lo)
        _vars = self._vars
        _hcons = self._hcons
        for hc in hcons:
            if len(hc) < 3:
                raise XmrsError(
                    'Handle constraints must have length >= 3: '
                    '(hi, relation, lo)'
                )
            hi = hc[0]
            lo = hc[2]
            if hi in _hcons:
                raise XmrsError(
                    'Handle constraint already exists for hole %s.' % hi
                )
            _hcons[hi] = hc
            # the following should also ensure lo and hi are in _vars
            if 'hcrefs' not in _vars[lo]:
                _vars[lo]['hcrefs'] = []
            for role, refs in _vars[hi]['refs'].items():
                for nodeid in refs:
                    _vars[lo]['hcrefs'].append((nodeid, role, hi))

    def add_icons(self, icons):
        _vars, _icons = self._vars, self._icons
        for ic in icons:
            if len(ic) < 3:
                raise XmrsError(
                    'Individual constraints must have length >= 3: '
                    '(left, relation, right)'
                )
            left = ic[0]
            right = ic[2]
            if left not in _icons:
                _icons[left] = []
            _icons[left].append(ic)
            # the following should also ensure left and right are in _vars
            if 'icrefs' not in _vars[right]:
                _vars[right]['icrefs'] = []
            _vars[right]['icrefs'].append(ic)
            _vars[left]  # just to instantiate if not done yet

    def __repr__(self):
        if self.surface is not None:
            stringform = '"{}"'.format(self.surface)
        else:
            stringform = ' '.join(ep[1].lemma for ep in self.eps())
        return '<Xmrs object ({}) at {}>'.format(stringform, id(self))

    def __contains__(self, obj):
        return obj in self._eps or obj in self._vars

    def __eq__(self, other):
        # actual equality is more than isomorphism, all variables and
        # things must have the same form, not just the same shape
        if not isinstance(other, Xmrs):
            return NotImplemented
        if ((self.top, self.index, self.xarg) !=
                (other.top, other.index, other.xarg)):
            return False
        a, b = sorted(self.eps()), sorted(other.eps())
        if len(a) != len(b) or any(ep1 != ep2 for ep1, ep2 in zip(a, b)):
            return False
        a, b = sorted(self.hcons()), sorted(other.hcons())
        if len(a) != len(b) or any(hc1 != hc2 for hc1, hc2 in zip(a, b)):
            return False
        a, b = sorted(self.icons()), sorted(other.icons())
        if len(a) != len(b) or any(ic1 != ic2 for ic1, ic2 in zip(a, b)):
            return False
        return True

    @property
    def ltop(self):
        return self.top

    @property
    def cfrom(self):
        cfrom = -1
        if self.lnk is not None and self.lnk[0] == 0:
            cfrom = self.lnk[1][0]
        return cfrom

    @property
    def cto(self):
        cto = -1
        if self.lnk is not None and self.lnk[0] == 0:
            cfrom = self.lnk[1][1]
        return cto

    # basic access to internal structures

    def ep(self, nodeid): return self._eps[nodeid]

    def eps(self, nodeids=None):
        if nodeids is None: nodeids = self._nodeids
        _eps = self._eps
        return [_eps[nodeid] for nodeid in nodeids]

    def hcon(self, hi): return self._hcons[hi]

    def hcons(self): return list(self._hcons.values())

    def icons(self, left=None):
        if left is not None:
            return self._icons[left]
        else:
            return list(chain.from_iterable(self._icons.values()))

    def variables(self): return list(self._vars)

    # access to internal sub-structures

    def properties(self, var_or_nodeid):
        if var_or_nodeid in self._vars:
            return dict(self._vars[var_or_nodeid]['props'])
        elif var_or_nodeid in self._eps:
            var = self._eps[var_or_nodeid][3].get(IVARG_ROLE)
            return dict(self._vars.get(var, {}).get('props', []))
        else:
            raise KeyError(var_or_nodeid)

    def pred(self, nodeid): return self._eps[nodeid][1]

    def preds(self, nodeids=None):
        if nodeids is None: nodeids = self._nodeids
        _eps = self._eps
        return [_eps[nid][1] for nid in nodeids]

    def label(self, nodeid): return self._eps[nodeid][2]

    def labels(self, nodeids=None):
        if nodeids is None: nodeids = self._nodeids
        _eps = self._eps
        return [_eps[nid][2] for nid in nodeids]

    def args(self, nodeid): return self._eps[nodeid][3]

    # calculated sub-structures

    def outgoing_args(self, nodeid):
        _vars = self._vars
        args = self.args(nodeid)
        for arg, val in args.items():
            pass

    def incoming_args(self, nodeid):
        _vars = self._vars
        _eps = self._eps
        ep = _eps[nodeid]
        lbl = ep[2]
        iv = ep[3].get(IVARG_ROLE)
        in_args = []
        if 'hcrefs' in vd:
            pass

    def labelset(self, label):
        return self._vars[label]['refs']['LBL']

    def labelset_heads(self, label):
        _eps = self._eps
        _vars = self._vars
        nodeids = {nodeid: _eps[nodeid][3].get(IVARG_ROLE, None)
                for nodeid in _vars[label]['refs']['LBL']}
        if len(nodeids) <= 1:
            return list(nodeids)

        ivs = {iv: nodeid for nodeid, iv in nodeids.items() if iv is not None}

        out = {n: len(list(filter(ivs.__contains__, _eps[n][3].values())))
               for n in nodeids}
        # out_deg is 1 for ARG0, but <= 1 because sometimes ARG0 is missing
        candidates = [n for n, out_deg in out.items() if out_deg <= 1]
        in_ = {}
        q = {}
        for n in candidates:
            iv = nodeids[n]
            if iv in _vars:
                in_[n] = sum(1 for slist in _vars[iv]['refs'].values()
                             for s in slist if s in nodeids)
            else:
                in_[n] = 0
            q[n] = 1 if _eps[n][1].is_quantifier() else 0

        return sorted(
            candidates,
            key=lambda n: (
                # prefer fewer outgoing args to eps in the labelset
                out[n],
                # prefer more incoming args from eps in the labelset
                -in_[n],
                # prefer quantifiers (if it has a labelset > 1, it's a
                # compound quantifier, like "nearly all")
                -q[n],
                # finally sort by the nodeid itself
                n
            )
        )

    def subgraph(self, nodeids):
        _eps, _vars = self._eps, self._vars
        _hcons, _icons = self._hcons, self._icons
        top = index = xarg = None
        eps = [_eps[nid] for nid in nodeids]
        lbls = set(ep[2] for ep in eps)
        hcons = []
        icons = []
        subvars = {}
        if self.top:
            top = self.top
            tophc = _hcons.get(top, None)
            if top in lbls:
                subvars[top] = {}
            elif tophc is not None and tophc[2] in lbls:
                subvars[top] = {}
                hcons.append(tophc)
            else:
                top = None  # nevermind, set it back to None
        # do index after we know if it is an EPs intrinsic variable.
        # what about xarg? I'm not really sure.. just put it in
        if self.xarg:
            xarg = self.xarg
            subvars[self.xarg] = _vars[self.xarg]['props']
        subvars.update((lbl, {}) for lbl in lbls)
        subvars.update(
            (var, _vars[var]['props'])
            for ep in eps for var in ep[3].values()
            if var in _vars
        )
        if self.index in subvars:
            index = self.index
        # hcons and icons; only if the targets exist in the new subgraph
        for var in subvars:
            hc = _hcons.get(var, None)
            if hc is not None and hc[2] in lbls:
                hcons.append(hc)
            for ic in _icons.get(var, []):
                if ic[0] in subvars and ic[2] in subvars:
                    icons.append(ic)
        return Xmrs(
            top=top, index=index, xarg=xarg,
            eps=eps, hcons=hcons, icons=icons, vars=subvars,
            lnk=self.lnk, surface=self.surface, identifier=self.identifier
        )

    def is_connected(self):
        nids = set(self._nodeids)  # the nids left to find
        nidlen = len(nids)
        if nidlen == 0:
            raise XmrsError('Cannot compute connectedness of an empty Xmrs.')
        _eps, _hcons, _vars = self._eps, self._hcons, self._vars
        explored = set()
        seen = set()
        agenda = [next(iter(nids))]

        while agenda:
            curnid = agenda.pop()
            ep = _eps[curnid]
            lbl = ep[2]
            conns = set()

            # labels can be shared, targets of HCONS, or targets of args
            if lbl in _vars:  # every EP should have a LBL
                for refrole, ref in _vars[lbl]['refs'].items():
                    if refrole == 'hcons':
                        for hc in ref:
                            if hc[0] in _vars:
                                refnids = _vars[hc[0]]['refs'].values()
                                conns.update(chain.from_iterable(refnids))
                    elif refrole != 'icons':
                        conns.update(ref)

            for role, var in ep[3].items():
                if var not in _vars:
                    continue
                vd = _vars[var]
                if IVARG_ROLE in vd['refs']:
                    conns.update(chain.from_iterable(vd['refs'].values()))
                # if 'iv' in vd:
                #     conns.add(vd['iv'])
                # if 'bv' in vd:
                #     conns.add(vd['bv'])
                if var in _hcons:
                    lo = _hcons[var][2]
                    if lo in _vars:
                        conns.update(_vars[lo]['refs']['LBL'])
                if 'LBL' in vd['refs']:
                    conns.update(vd['refs']['LBL'])

            explored.add(curnid)
            for conn in conns:
                if conn not in explored:
                    agenda.append(conn)
            seen.update(conns)
            # len(seen) is a quicker check
            if len(seen) == nidlen and len(nids.difference(seen)) == 0:
                break

        return len(nids.difference(seen)) == 0

    def is_well_formed(self):
        _eps = self._eps
        _vars = self._vars
        nodeids = self._nodeids
        hcons = [_vars[argval]['hcons']
                 for nid in nodeids
                 for argval in _eps[nid][3].values()
                 if 'hcons' in _vars.get(argval, {})]
        return (
            self.is_connected() and
            all(_eps[nid][2] in _vars for nid in nodeids) and
            all(lo in _vars and len(_vars[lo]['refs'].get('LBL', [])) > 0
                for _, _, lo in hcons)
        )


class Pred(namedtuple('Pred', ('type', 'lemma', 'pos', 'sense', 'string'))):
    pred_re = re.compile(
        r'_?(?P<lemma>.*?)_'  # match until last 1 or 2 parts
        r'((?P<pos>[a-z])_)?'  # pos is always only 1 char
        r'((?P<sense>([^_\\]|(?:\\.))+)_)?'  # no unescaped _s
        r'(?P<end>rel(ation)?)$',  # NB only _rel is valid
        re.IGNORECASE
    )
    # Pred types (used mainly in input/output, not internally in pyDelphin)
    GRAMMARPRED = 0  # only a string allowed (quoted or not)
    REALPRED = 1  # may explicitly define lemma, pos, sense
    STRINGPRED = 2  # quoted string form of realpred

    def __eq__(self, other):
        if other is None:
            return False
        if isinstance(other, Pred):
            other = other.string
        return self.string.strip('"\'') == other.strip('"\'')

    def __str__ (self):
        return self.string

    def __repr__(self):
        return '<Pred object {} at {}>'.format(self.string, id(self))

    def __hash__(self):
        return hash(self.string)

    @classmethod
    def stringpred(cls, predstr):
        lemma, pos, sense, end = split_pred_string(predstr.strip('"\''))
        return cls(Pred.STRINGPRED, lemma, pos, sense, predstr)

    @classmethod
    def grammarpred(cls, predstr):
        lemma, pos, sense, end = split_pred_string(predstr.strip('"\''))
        return cls(Pred.GRAMMARPRED, lemma, pos, sense, predstr)

    @staticmethod
    def string_or_grammar_pred(predstr):
        if predstr.strip('"').lstrip("'").startswith('_'):
            return Pred.stringpred(predstr)
        else:
            return Pred.grammarpred(predstr)

    @classmethod
    def realpred(cls, lemma, pos, sense=None):
        string_tokens = [lemma, pos]
        if sense is not None:
            sense = str(sense)
            string_tokens.append(sense)
        predstr = '_'.join([''] + string_tokens + ['rel'])
        return cls(Pred.REALPRED, lemma, pos, sense, predstr)

    def short_form(self):
        return self.string.strip('"').lstrip("'").rsplit('_', 1)[0]

    def is_quantifier(self):
        return self.pos == QUANTIFIER_POS


def split_pred_string(predstr):
    match = Pred.pred_re.search(predstr)
    if match is None:
        return (predstr, None, None, None)
    # _lemma_pos(_sense)?_end
    return (match.group('lemma'), match.group('pos'),
            match.group('sense'), match.group('end'))


def links(xmrs):
    links = []
    prelinks = []

    _eps = xmrs._eps
    _hcons = xmrs._hcons
    _vars = xmrs._vars
    _pred = xmrs.pred

    lsh = xmrs.labelset_heads
    lblheads = {v: lsh(v) for v, vd in _vars.items() if 'LBL' in vd['refs']}

    top = xmrs.top
    if top is not None:
        prelinks.append((0, top, None, top, _vars[top]))

    for nid, ep in _eps.items():
        for role, val in ep[3].items():
            if role == IVARG_ROLE or val not in _vars:
                continue
            prelinks.append((nid, ep[2], role, val, _vars[val]))

    for src, srclbl, role, val, vd in prelinks:
        if IVARG_ROLE in vd['refs']:
            tgtnids = [n for n in vd['refs'][IVARG_ROLE]
                       if not _pred(n).is_quantifier()]
            if len(tgtnids) == 0:
                continue  # maybe some bad MRS with a lonely quantifier
            tgt = tgtnids[0]  # what do we do if len > 1?
            tgtlbl = _eps[tgt][2]
            post = 'EQ' if srclbl == tgtlbl else 'NEQ'
        elif val in _hcons:
            lbl = _hcons[val][2]
            if lbl not in lblheads or len(lblheads[lbl]) == 0:
                continue  # broken MRS; log this?
            tgt = lblheads[lbl][0]  # sorted list; first item is most "heady"
            post = 'H'
        elif 'LBL' in vd['refs']:
            if val not in lblheads or len(lblheads[val]) == 0:
                continue  # broken MRS; log this?
            tgt = lblheads[val][0]  # again, should be sorted already
            post = 'HEQ'
        else:
            continue  # CARGs, maybe?
        links.append((src, tgt, role, post))

    # now EQ links unattested by arg links
    for lbl, heads in lblheads.items():
        # I'm pretty sure this does what we want
        if len(heads) > 1:
            first = heads[0]
            for other in heads[1:]:
                links.append((first, other, None, 'EQ'))
    return sorted(links) #, key=lambda link: (link.start, link.end))


def nodes(xmrs):
    """The list of Nodes."""
    nodes = []
    _vars = xmrs._vars
    _props = xmrs.properties
    for p in xmrs.eps():
        eplen = len(p)
        nid = p[0]
        pred = p[1]
        args = p[3]
        sortinfo = lnk = surface = base = None
        iv = args.get(IVARG_ROLE, None)
        if iv is not None:
            sort, _ = var_re.match(iv).groups()
            sortinfo = _props(iv)
            sortinfo['cvarsort'] = sort
        if eplen >= 5:
            lnk = p[4]
        if eplen >= 6:
            surface = p[5]
        if eplen >= 7:
            base = p[6]
        carg = args.get(CONSTARG_ROLE, None)
        nodes.append((nid, pred, sortinfo, lnk, surface, base, carg))
    return nodes


def rargname_sortkey(rargname):
    # canonical order: LBL ARG* RSTR BODY *-INDEX *-HNDL CARG ...
    rargname = rargname.upper()
    return (
        rargname != 'LBL',
        rargname in ('BODY', 'CARG'),
        rargname.endswith('HNDL'),
        rargname
    )


# SimpleMRS codec

# versions are:
#  * 1.0 long running standard
#  * 1.1 added support for MRS-level lnk, surface and EP-level surface
_default_version = 1.1
_latest_version = 1.1

_top = r'TOP'
_ltop = r'LTOP'

# pretty-print options
_default_mrs_delim = '\n'


def load(fh, single=False, strict=False):
    if isinstance(fh, str):
        return loads(open(fh, 'r').read(), single=single, strict=strict)
    return loads(fh.read(), single=single, strict=strict)


def loads(s, single=False, **kwargs):
    ms = deserialize(s)
    if single:
        return next(ms)
    else:
        return ms


def dump(fh, ms, single=False, version=_default_version,
         pretty_print=False, **kwargs):
    print(dumps(ms,
                single=single,
                version=version,
                pretty_print=pretty_print,
                **kwargs),
          file=fh)


def dumps(ms, single=False, version=_default_version,
          pretty_print=False, **kwargs):
    if single:
        ms = [ms]
    return serialize(ms, version=version,
                     pretty_print=pretty_print, **kwargs)


# for convenience

load_one = lambda fh, **kwargs: load(fh, single=True, **kwargs)
loads_one = lambda s, **kwargs: loads(s, single=True, **kwargs)
dump_one = lambda fh, m, **kwargs: dump(fh, m, single=True, **kwargs)
dumps_one = lambda m, **kwargs: dumps(m, single=True, **kwargs)

# Deserialization

tokenizer = re.compile(r'("[^"\\]*(?:\\.[^"\\]*)*"'
                       r'|[^\s:#@\[\]<>"]+'
                       r'|[:#@\[\]<>])')


def tokenize(string):
    return deque(tokenizer.findall(string))


def deserialize(string):
    # FIXME: consider buffering this so we don't read the whole string at once
    tokens = tokenize(string)
    while tokens:
        yield _read_mrs(tokens)


def _read_mrs(tokens, version=_default_version):
    #return read_mrs(tokens)
    try:
        if tokens[0] != '[':
            return None
        top = idx = surface = lnk = None
        vars_ = {}
        tokens.popleft()  # [
        if tokens[0] == '<':
            lnk = _read_lnk(tokens)
        if tokens[0].startswith('"'):  # and tokens[0].endswith('"'):
            surface = tokens.popleft()[1:-1]  # get rid of first quotes
        if tokens[0] in (_ltop, _top):
            tokens.popleft()  # LTOP / TOP
            tokens.popleft()  # :
            top = tokens.popleft()
            vars_[top] = []
        if tokens[0] == 'INDEX':
            tokens.popleft()  # INDEX
            tokens.popleft()  # :
            idx = tokens.popleft()
            vars_[idx] = _read_props(tokens)
        rels = _read_rels(tokens, vars_)
        hcons = _read_cons(tokens, 'HCONS', vars_)
        icons = _read_cons(tokens, 'ICONS', vars_)
        tokens.popleft()  # ]
        # at this point, we could uniquify proplists in vars_, but most
        # likely it isn't necessary, and might night harm things if we
        # leave potential dupes in there. let's see how it plays out.
        m = Xmrs(top=top, index=idx, eps=rels,
                 hcons=hcons, icons=icons, vars=vars_,
                 lnk=lnk, surface=surface)
    except IndexError:
        raise XDE('Invalid MRS: Unexpected termination.')
    return m


def _read_props(tokens):
    props = []
    if tokens[0] == '[':
        tokens.popleft()  # [
        vartype = tokens.popleft()  # this gets discarded though
        while tokens[0] != ']':
            key = tokens.popleft()
            tokens.popleft()  # :
            val = tokens.popleft()
            props.append((key, val))
        tokens.popleft()  # ]
    return props


def _read_rels(tokens, vars_):
    rels = None
    nid = 10000
    if tokens[0] == 'RELS':
        rels = []
        tokens.popleft()  # RELS
        tokens.popleft()  # :
        tokens.popleft()  # <
        while tokens[0] != '>':
            rels.append(_read_ep(tokens, nid, vars_))
            nid += 1
        tokens.popleft()  # >
    return rels


def _read_ep(tokens, nid, vars_):
    # reassign these locally to avoid global lookup
    CARG = CONSTARG_ROLE
    _var_re = var_re
    # begin parsing
    tokens.popleft()  # [
    pred = Pred.string_or_grammar_pred(tokens.popleft())
    lnk = _read_lnk(tokens)
    surface = label = None
    if tokens[0].startswith('"'):
        surface = tokens.popleft()[1:-1]  # get rid of first quotes
    if tokens[0] == 'LBL':
        tokens.popleft()  # LBL
        tokens.popleft()  # :
        label = tokens.popleft()
        vars_[label] = []
    args = {}
    while tokens[0] != ']':
        role = tokens.popleft()
        tokens.popleft()  # :
        val = tokens.popleft()
        if _var_re.match(val) is not None and role.upper() != CARG:
            props = _read_props(tokens)
            if val not in vars_:
                vars_[val] = []
            vars_[val].extend(props)
        args[role] = val
    tokens.popleft()  # ]
    return (nid, pred, label, args, lnk, surface)


def _read_cons(tokens, constype, vars_):
    cons = None
    if tokens[0] == constype:
        cons = []
        tokens.popleft()  # (H|I)CONS
        tokens.popleft()  # :
        tokens.popleft()  # <
        while tokens[0] != '>':
            left = tokens.popleft()
            reln = tokens.popleft()
            rght = tokens.popleft()
            cons.append((left, reln, rght))
            # now just make sure they are in the vars_ dict
            vars_.setdefault(left, [])
            vars_.setdefault(rght, [])
        tokens.popleft()  # >
    return cons


def _read_lnk(tokens):
    # < FROM : TO >
    lnk = None
    if tokens[0] == '<':
        tokens.popleft()  # we just checked this is a left angle
        if tokens[0] == '>':
            pass  # empty <> brackets the same as no lnk specified
        # character span lnk: [FROM, ':', TO, ...]
        elif tokens[1] == ':':
            # first 0 is the CHARSPAN type (can be ignored)
            lnk = (0, (int(tokens.popleft()), int(tokens[1])))
            tokens.popleft()  # this should be the colon
            tokens.popleft()  # and this is the cto
        tokens.popleft()  # should be '>'
    return lnk


# Encoding


def serialize(ms, version=_default_version, pretty_print=False, **kwargs):
    delim = '\n' if pretty_print else _default_mrs_delim
    output = delim.join(
        serialize_mrs(m, version=version, pretty_print=pretty_print)
        for m in ms
    )
    return output


def serialize_mrs(m, version=_default_version, pretty_print=False):
    # note that varprops is modified as a side-effect of the lower
    # functions
    varprops = {v: vd['props'] for v, vd in m._vars.items() if vd['props']}
    toks = []
    if version >= 1.1:
        header_toks = []
        if m.lnk is not None:
            header_toks.append(serialize_lnk(m.lnk))
        if m.surface is not None:
            header_toks.append('"{}"'.format(m.surface))
        if header_toks:
            toks.append(' '.join(header_toks))
    if m.top is not None:
        toks.append(serialize_argument(
            _top if version >= 1.1 else _ltop, m.top, varprops
        ))
    if m.index is not None:
        toks.append(serialize_argument(
            'INDEX', m.index, varprops
        ))
    delim = ' ' if not pretty_print else '\n          '
    toks.append('RELS: < {eps} >'.format(
        eps=delim.join(serialize_ep(ep, varprops, version=version)
                       for ep in m.eps())
    ))
    toks += [serialize_hcons(m.hcons())]
    icons_ = m.icons()
    if version >= 1.1 and icons_:  # remove `and icons_` for "ICONS: < >"
        toks += [serialize_icons(icons_)]
    delim = ' ' if not pretty_print else '\n  '
    return '{} {} {}'.format('[', delim.join(toks), ']')


def serialize_argument(rargname, value, varprops):
    _argument = '{rargname}: {value}{props}'
    props = ''
    if value in varprops:
        props = ' [ {} ]'.format(
            ' '.join(
                [var_re.match(value).group(1)] +
                list(map('{0[0]}: {0[1]}'.format, varprops[value]))
            )
        )
        del varprops[value]  # only print props once
    return _argument.format(
        rargname=rargname,
        value=str(value),
        props=props
    )


def serialize_ep(ep, varprops, version=_default_version):
    # ('nodeid', 'pred', 'label', 'args', 'lnk', 'surface', 'base')
    args = ep[3]
    arglist = ' '.join([serialize_argument(rarg, args[rarg], varprops)
                        for rarg in sorted(args, key=rargname_sortkey)])
    if version < 1.1 or len(ep) < 6 or ep[5] is None:
        surface = ''
    else:
        surface = ' "%s"' % ep[5]
    lnk = None if len(ep) < 5 else ep[4]
    pred = ep[1]
    predstr = pred.string
    return '[ {pred}{lnk}{surface} LBL: {label}{s}{args} ]'.format(
        pred=predstr,
        lnk=serialize_lnk(lnk),
        surface=surface,
        label=str(ep[2]),
        s=' ' if arglist else '',
        args=arglist
    )


def serialize_lnk(lnk):
    s = ""
    if lnk is not None and lnk[0] == 0:
        cfrom, cto = lnk[1]
        s = ''.join(['<', str(cfrom), ':', str(cto), '>'])
    return s


def serialize_hcons(hcons):
    toks = ['HCONS' + ':', '<']
    for hc in hcons:
        toks.extend(hc)
        # reln = hcon[1]
        # toks += [hcon[0], rel, str(hcon.lo)]
    toks += ['>']
    return ' '.join(toks)

def serialize_icons(icons):
    toks = ['ICONS' + ':', '<']
    for ic in icons:
        toks.extend(ic)
        # toks += [str(icon.left),
        #          icon.relation,
        #          str(icon.right)]
    toks += ['>']
    return ' '.join(toks)


# ACE interface

class AceProcess(object):

    _cmdargs = []

    def __init__(self, grm, cmdargs=None, executable=None, env=None, **kwargs):
        if not os.path.isfile(grm):
            raise ValueError("Grammar file %s does not exist." % grm)
        self.grm = grm
        self.cmdargs = cmdargs or []
        self.executable = executable or 'ace'
        self.env = env or os.environ
        self._open()

    def _open(self):
        self._p = Popen(
            [self.executable, '-g', self.grm] + self._cmdargs + self.cmdargs,
            stdin=PIPE,
            stdout=PIPE,
            stderr=STDOUT,
            env=self.env,
            universal_newlines=True
        )

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
        return False  # don't try to handle any exceptions

    def send(self, datum):
        self._p.stdin.write(datum.rstrip() + '\n')
        self._p.stdin.flush()

    def receive(self):
        return self._p.stdout

    def interact(self, datum):
        self.send(datum)
        result = self.receive()
        return result

    def read_result(self, result):
        return result

    def close(self):
        self._p.stdin.close()
        for line in self._p.stdout:
            logging.debug('ACE cleanup: {}'.format(line.rstrip()))
        retval = self._p.wait()
        return retval


class AceParser(AceProcess):

    def receive(self):
        response = {
            'NOTES': [],
            'WARNINGS': [],
            'ERRORS': [],
            'SENT': None,
            'RESULTS': []
        }

        blank = 0

        stdout = self._p.stdout
        line = stdout.readline().rstrip()
        while True:
            if line.strip() == '':
                blank += 1
                if blank >= 2:
                    break
            elif line.startswith('SENT: ') or line.startswith('SKIP: '):
                response['SENT'] = line.split(': ', 1)[1]
            elif (line.startswith('NOTE:') or
                  line.startswith('WARNING') or
                  line.startswith('ERROR')):
                level, message = line.split(': ', 1)
                response['{}S'.format(level)].append(message)
            else:
                mrs, deriv = line.split(' ; ')
                response['RESULTS'].append({
                    'MRS': mrs.strip(),
                    'DERIV': deriv.strip()
                })
            line = stdout.readline().rstrip()
        return response


class AceGenerator(AceProcess):

    _cmdargs = ['-e']

    def receive(self):
        response = {
            'NOTE': None,
            'WARNING': None,
            'ERROR': None,
            'SENT': None,
            'RESULTS': None
        }
        results = []

        stdout = self._p.stdout
        line = stdout.readline().rstrip()
        while not line.startswith('NOTE: '):
            if line.startswith('WARNING') or line.startswith('ERROR'):
                level, message = line.split(': ', 1)
                response[level] = message
            else:
                results.append(line)
            line = stdout.readline().rstrip()
        # sometimes error messages aren't prefixed with ERROR
        if line.endswith('[0 results]') and len(results) > 0:
            response['ERROR'] = '\n'.join(results)
            results = []
        response['RESULTS'] = results
        return response


def compile(cfg_path, out_path, log=None):
    #debug('Compiling grammar at {}'.format(abspath(cfg_path)), log)
    try:
        check_call(
            ['ace', '-g', cfg_path, '-G', out_path],
            stdout=log, stderr=log, close_fds=True
        )
    except (CalledProcessError, OSError):
        logging.error(
            'Failed to compile grammar with ACE. See {}'
            .format(log.name if log is not None else '<stderr>')
        )
        raise
    #debug('Compiled grammar written to {}'.format(abspath(out_path)), log)


def parse_from_iterable(dat_file, data, **kwargs):
    with AceParser(dat_file, **kwargs) as parser:
        for datum in data:
            yield parser.interact(datum)


def parse(dat_file, datum, **kwargs):
    return next(parse_from_iterable(dat_file, [datum], **kwargs))


def generate_from_iterable(dat_file, data, **kwargs):
    with AceGenerator(dat_file, **kwargs) as generator:
        for datum in data:
            yield generator.interact(datum)


def generate(dat_file, datum, **kwargs):
    return next(generate_from_iterable(dat_file, [datum], **kwargs))