"""
This is an extension for Sphinx which adds the ``scm`` domain.
"""

from sphinx import addnodes
from sphinx.roles import XRefRole
from sphinx.directives import ObjectDescription
from sphinx.domains import Domain, ObjType
from sphinx.util.nodes import make_refnode

import re

_tokens_re = re.compile(r'(\(|\)|\s+|[^\(\)\s]+)')

class Tokens(object):
    def __init__(self, tokens):
        self.tokens = tokens
        self.i = 0

    @property
    def t(self):
        try:
            return self.tokens[self.i]
        except IndexError:
            return None

    def advance(self):
        self.i += 1

def tokenize(s):
    return Tokens(_tokens_re.findall(s))

class ParseError(Exception):
    """Bad S expression."""

def _consume_space(tokens):
    while tokens.t is not None and tokens.t.isspace():
        tokens.advance()

def _parse_sexp(tokens):
    _consume_space(tokens)

    t = tokens.t
    if t == ')':
        raise ParseError('unexpected closing parenthesis')
    elif t == '(':
        tokens.advance()
        l = []
        while tokens.t is not None and tokens.t != ')':
            l.append(_parse_sexp(tokens))
            _consume_space(tokens)
        if tokens.t != ')':
            raise ParseError('expected closing parenthesis')
        tokens.advance()
        return l
    else:
        tokens.advance()
        return t
    raise ParseError('unexpected end of input')

def parse_sexp(s):
    return _parse_sexp(tokenize(s))

class FunctionObj(ObjectDescription):
    def handle_signature(self, sig, signode):
        try:
            sexpr = parse_sexp(sig)
        except ParseError, e:
            #raise ValueError('invalid function signature')
            raise

        name = sexpr[0]

        signode += addnodes.desc_name(sig, sig)

        return name

    def add_target_and_index(self, name, sig, signode):
        signode['ids'].append(name)
        inv = self.env.domaindata['scm']['objects']
        if name in inv:
            self.env.warn(
                self.env.docname,
                'duplicate Scheme object description of %s, ' % name +
                'other instance in ' + self.env.doc2path(inv[name][0]),
                self.lineno)
        inv[name] = (self.env.docname, self.objtype)

        indextext = '%s (Scheme function)' % name
        self.indexnode['entries'].append(('single', indextext, name, name))

class FunctionXRef(XRefRole):
    def process_link(self, env, refnode, has_explicit_title, title, target):
        if not has_explicit_title:
            title = '(' + title + ')'
        return title, target

class ScmDomain(Domain):
    name = 'scm'
    label = 'Scheme'

    object_types = {'function': ObjType('function', 'func')}
    directives = {'function': FunctionObj}
    roles = {'func': FunctionXRef()}
    initial_data = {
        'objects': {},  # fullname -> docname, objtype
    }

    def clear_doc(self, docname):
        for fullname, (fn, _) in self.data['objects'].items():
            if fn == docname:
                del self.data['objects'][fullname]

    def resolve_xref(self, env, fromdocname, builder,
                     typ, target, node, contnode):
        if target not in self.data['objects']:
            return None
        obj = self.data['objects'][target]
        return make_refnode(builder, fromdocname, obj[0], target,
                            contnode, target)

    def get_objects(self):
        for refname, (docname, typ) in self.data['objects'].iteritems():
            yield (refname, refname, typ, docname, refname, 1)

def setup(app):
    app.add_domain(ScmDomain)
