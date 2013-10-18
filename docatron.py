#!/usr/bin/env python2

import argparse
import re

REQ_RE = r'(?P<name>[\w_\-]+)\s+{(?P<type>[^}]+)}:'
OPT_RE = r'(?P<name>[\w_\-]+)\s+\((?P<default>[^)]+)\)\s+{(?P<type>[^}]+)}:'
RET_RE = r'{(?P<type>[^}]+)}:'
PAR_SEC_RE = r'(params|parameters|props|properties):\s*$'
RET_SEC_RE = r'returns:\s*$'


class DocatronSyntaxError(Exception):
    def __init__(self, message, filename, lineno):
        Exception.__init__(self, '%s: %s line %d' % (message, filename, lineno))


def _is_params(text):
    return re.match(PAR_SEC_RE, text.lower())


def _is_param(text):
    return re.match(REQ_RE, text) or re.match(OPT_RE, text)


def _is_return(text):
    return re.match(RET_SEC_RE, text.lower())


def _parse_line(regex_list, line):
    for regex in regex_list:
        result = re.match(regex, line)
        if result:
            return (result.groupdict(),
                    line.replace(result.group(0), '', 1).strip())
    return None


class Node(object):
    CLASS = 'class'
    FUNCTION = 'function'
    PROPERTY = 'property'
    EVENT = 'event'

    _TOP_LEVEL_TYPES = (CLASS, FUNCTION, PROPERTY, EVENT)

    def __init__(self, chunk, filename):
        self.name = None
        self.filename = filename
        self.lineno = chunk[0].lineno

        self._children = []
        self._return = None
        self._return_description = None
        self._default = None
        self._description = None
        self._type = None
        self._top_level_type = None

        self._parse_chunk(chunk)
        print self
        print

    def __repr__(self):
        return '%s: %s\nType %s, Default %s\nReturns %s: %s\nChildren: %s' % (
            self.name, self._description, self._type, self._default,
            self._return, self._return_description,
            ', '.join([c.name for c in self._children]))

    def _get_description(self, chunk, indent, desc):
        desc_list = [desc]
        while len(chunk):
            desc_line = chunk[0]
            if desc_line.indent < indent + 2:
                break

            chunk.pop(0)
            desc_list.append(desc_line.text)
        return ' '.join(desc_list)

    def _parse_return(self, chunk):
        # Pop off "Returns:" first.
        chunk.pop(0)

        line = chunk[0]
        chunk.pop(0)

        result = _parse_line([RET_RE], line.text)
        if result is None:
            raise DocatronSyntaxError('bad return', self.filename, line.lineno)

        groups, rest = result

        self._return = groups.get('type')
        self._return_description = self._get_description(chunk,
                                                         line.indent,
                                                         rest)

    def _parse_params(self, chunk):
        # Pop off "Params:" first.
        chunk.pop(0)

        if not len(chunk):
            raise DocatronSyntaxError('params section needs at least one param',
                                      self.filename,
                                      line.lineno)

        indent = chunk[0].indent
        while len(chunk):
            line = chunk[0]

            # Next line is indented less, we're done here.
            if indent > line.indent:
                break

            self._children.append(Node(chunk, self.filename))

    def _parse_param(self, chunk):
        # Grab the line then pop it off.
        line = chunk[0]
        chunk.pop(0)

        result = _parse_line([OPT_RE, REQ_RE], line.text)
        if result is None:
            raise DocatronSyntaxError('param malformed',
                                      self.filename,
                                      line.lineno)

        groups, rest = result
        self._type = groups.get('type', '')
        self.name = groups.get('name', '')
        self._default = groups.get('default')

        self._description = self._get_description(chunk, line.indent, rest)

        if len(chunk) and chunk[0].indent == line.indent + 1:
            self._parse_chunk(chunk)

    def _parse_top_level(self, chunk):
        line = chunk[0]
        chunk.pop(0)

        self._top_level_type, self.name = line.text.split()
        if self._top_level_type not in Node._TOP_LEVEL_TYPES:
            raise DocatronSyntaxError(
                'type must be one of: %s' % str(Node._TOP_LEVEL_TYPES),
                self.filename,
                line.lineno)

        desc_list = []
        while len(chunk):
            line = chunk[0]
            if _is_params(line.text) or _is_return(line.text):
                break

            chunk.pop(0)
            desc_list.append(line.text)
        self._description = ' '.join(desc_list)

    def _parse_chunk(self, chunk):
        line = chunk[0]
        if self.name is None and line.indent == 0:
            self._parse_top_level(chunk)

        if not len(chunk):
            return

        line = chunk[0]
        indent = line.indent
        lineno = line.lineno
        while len(chunk):
            line = chunk[0]
            if line.lineno != lineno and indent and line.indent <= indent:
                break
            if _is_params(line.text):
                self._parse_params(chunk)
            elif _is_param(line.text):
                self._parse_param(chunk)
            elif _is_return(line.text):
                self._parse_return(chunk)
            else:
                raise DocatronSyntaxError('no matches',
                                          self.filename,
                                          line.lineno)


class Line(object):
    def __init__(self, line, indent, filename, lineno):
        num_spaces = len(line) - len(line.lstrip())
        if num_spaces % indent:
            raise DocatronSyntaxError('bad indent', filename, lineno)
        self.indent = num_spaces / indent
        self.lineno = lineno
        self.text = line.strip()

    def __repr__(self):
        return '%s: %s: %s' % (self.lineno, self.indent, self.text)

'''
<h2>DocParser</h2>
<p>Parses the docs</p>
<h3>Params:</h3>
<ul>
  <li>
    <h4>String[] files</h4>
    The files to parse
  </li>
  <li>
    <h4>String token:'///'</h4>
    The token to start on
  </li>
</ul>
'''
## class DocParser
## This class parses the doc.
##     WEIRD INDENT
##
## Params:
##   files {String[]}: The files to parse. If this is a really long description
##       then we can continue two indents in and the parser will be very happy
##       about this.
##   token ('///') {String}: The token to start on.
##
##   callback {Function}: The callback function
##     Params:
##       data {String}: Some data this is a super
##           long description too.
##       callback2 {Function}: Another callback
##         Params:
##           data2 {String}: More data!
##
##     Returns:
##       {String}: The return value
##
## Returns:
##   {String}: Class return
class DocParser(object):
    def __init__(self, files, token='///', indent=2):
        self._token = token.strip()
        self._indent = indent
        self._chunks = {}
        self._nodes = {}
        for name in files:
            self._parse_file(name)
        for filename, chunks in self._chunks.iteritems():
            for chunk in chunks:
                node = Node(chunk, filename)
                prev_node = self._nodes.get(node.name)
                if prev_node is not None:
                    raise DocatronSyntaxError(
                        'duplicate nodes: found here first: %s line %s' %
                            (prev_node.filename, prev_node.lineno),
                        filename,
                        node.lineno)
                self._nodes[node.name] = node

    def _has_token(self, line):
        return line.strip().startswith(self._token)

    def _strip_token(self, line):
        return line.strip()[len(self._token + ' '):]

    def _parse_file(self, filename):
        current_chunk = []
        with open(filename) as f:
            for i, line in enumerate(f):
                if self._has_token(line):
                    line = self._strip_token(line)
                    if line:
                        current_chunk.append(
                            Line(line, self._indent, filename, i + 1))
                elif current_chunk:
                    if not filename in self._chunks:
                        self._chunks[filename] = []
                    self._chunks[filename].append(current_chunk)
                    current_chunk = []


if __name__ == '__main__':
    parser = argparse.ArgumentParser('DOCATRON documentation generator')
    parser.add_argument('-t', default='///',
                        help='Token to start DOCATRON comments (default "///")')
    parser.add_argument('-i', default=2,
                        help='Indent level for doc strings')
    parser.add_argument('file', nargs='+', help='The files to parse')
    args = parser.parse_args()
    DocParser(args.file, token=args.t, indent=args.i)
