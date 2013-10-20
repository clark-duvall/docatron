#!/usr/bin/env python2

import argparse
from collections import OrderedDict
import re
import sys

REQ_RE = r'(?P<name>[\w_\-]+)\s+{(?P<type>[^}]+)}:'
OPT_RE = r'(?P<name>[\w_\-]+)\s+\((?P<default>[^)]+)\)\s+{(?P<type>[^}]+)}:'
RET_RE = r'{(?P<type>[^}]+)}:'
PAR_SEC_RE = r'(params|parameters|props|properties):\s*$'
RET_SEC_RE = r'returns:\s*$'

BASE = '<div>\n%s\n</div>'
BASE_ITEM = '<div>\n%s\n</div>'
TOP_LEVEL = '<h2 id="%(url)s">%(type)s %(name)s</h2>'
SECONDARY = '<h4 id="%(url)s">%(name)s:%(type)s</h4>'
SECONDARY_DEF = '<h4 id="%(url)s">%(name)s:%(type)s (%(default)s)</h4>'
SUB = '<h3 id="%(url)s">%(name)s</h3>'
DESC = '<p>%s</p>'
PARAMS = '<h3>%s</h3>\n<ul>\n%s\n</ul>'
CHILDREN = '<div><h3>%s</h3>\n<ul>\n%s\n</ul></div>'
RETURNS = '<h3>Returns: %s</h3>'
PARAM = '<li>\n%s\n</li>'

class DocatronSyntaxError(Exception):
    def __init__(self, message, filename, lineno):
        Exception.__init__(self, '%s: %s line %d' % (message, filename, lineno))


def _indent_block(text):
    return '\n'.join(['  %s' % line for line in text.split('\n')])


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
    OBJECT = 'object'
    FUNCTION = 'function'
    PROPERTY = 'property'
    EVENT = 'event'

    TOP_LEVEL_TYPES = (CLASS, OBJECT, FUNCTION, PROPERTY, EVENT)

    def __init__(self, block, filename, parent):
        self.name = None
        self.filename = filename
        self.lineno = block[0].lineno
        self.parent = parent

        self.children = []
        self.return_type = None
        self.return_description = None
        self.default = None
        self.description = None
        self.type = None
        self.top_level_type = None

        self._parse_block(block)

    def get_name_url_map(self):
        mapping = {self.name: self.url()}
        for child in self.children:
            mapping.update(child.get_name_url_map())
        return mapping

    def url(self):
        url = self.name.lower().replace('.', '-')
        if self.parent:
            url = '%s-%s' % (self.parent.url(), url)
        if self.top_level_type:
            url = '%s-%s' % (self.top_level_type, url)
        return url

    def to_html(self, top_level=False):
        html = []
        name = self.name.split('.')[-1]
        if top_level:
            html.append(TOP_LEVEL % {
                'name': name,
                'type': self.top_level_type,
                'url': self.url()
            })
        else:
            if self.type is None:
                html.append(SUB % {
                    'name': name,
                    'url': self.url()
                })
            else:
                html.append(
                    (SECONDARY if self.default is None else SECONDARY_DEF) % {
                        'name': name,
                        'type': self.type,
                        'default': self.default,
                        'url': self.url()
                    })

        if self.description:
            html.append(DESC % self.description)

        if self.children:
            html.append(CHILDREN % ('Params:', _indent_block(
                '\n'.join([PARAM % _indent_block(p.to_html())
                           for p in self.children]))))

        if self.return_type:
            html.append(RETURNS % self.return_type)
            if self.return_description:
                html.append(DESC % self.return_description)

        return '\n'.join(html)

    def __repr__(self):
        return '%s: %s\nType %s, Default %s\nReturns %s: %s\nChildren: %s' % (
            self.name, self.description, self.type or self.top_level_type,
            self.default, self.return_type, self.return_description,
            ', '.join([c.name for c in self.children]))

    def _get_description(self, block, indent, desc):
        desc_list = [desc]
        while len(block):
            desc_line = block[0]
            if desc_line.indent < indent + 2:
                break

            block.pop(0)
            desc_list.append(desc_line.text)
        return ' '.join(desc_list)

    def _parse_return(self, block):
        # Pop off "Returns:" first.
        block.pop(0)

        line = block[0]
        block.pop(0)

        result = _parse_line([RET_RE], line.text)
        if result is None:
            raise DocatronSyntaxError('bad return', self.filename, line.lineno)

        groups, rest = result

        self.return_type = groups.get('type')
        self.return_description = self._get_description(block,
                                                        line.indent,
                                                        rest)

    def _parse_params(self, block):
        # Pop off "Params:" first.
        block.pop(0)

        if not len(block):
            raise DocatronSyntaxError('params section needs at least one param',
                                      self.filename,
                                      line.lineno)

        indent = block[0].indent
        while len(block):
            line = block[0]

            # Next line is indented less, we're done here.
            if indent > line.indent:
                break

            self.children.append(Node(block, self.filename, self))

    def _parse_param(self, block):
        # Grab the line then pop it off.
        line = block[0]
        block.pop(0)

        result = _parse_line([OPT_RE, REQ_RE], line.text)
        if result is None:
            raise DocatronSyntaxError('param malformed',
                                      self.filename,
                                      line.lineno)

        groups, rest = result
        self.type = groups.get('type', '')
        self.name = groups.get('name', '')
        self.default = groups.get('default')

        self.description = self._get_description(block, line.indent, rest)

        if len(block) and block[0].indent == line.indent + 1:
            self._parse_block(block)

    def _parse_top_level(self, block):
        line = block[0]
        block.pop(0)

        self.top_level_type, self.name = line.text.split()
        if self.top_level_type not in Node.TOP_LEVEL_TYPES:
            raise DocatronSyntaxError(
                'type must be one of: %s' % str(Node.TOP_LEVEL_TYPES),
                self.filename,
                line.lineno)

        desc_list = []
        while len(block):
            line = block[0]
            if _is_params(line.text) or _is_return(line.text):
                break

            block.pop(0)
            desc_list.append(line.text)
        self.description = ' '.join(desc_list)

    def _parse_block(self, block):
        line = block[0]
        if self.parent is None:
            self._parse_top_level(block)

        if not len(block):
            return

        line = block[0]
        indent = line.indent
        lineno = line.lineno
        while len(block):
            line = block[0]
            if line.lineno != lineno and indent and line.indent <= indent:
                break
            if _is_params(line.text):
                self._parse_params(block)
            elif _is_param(line.text):
                self._parse_param(block)
            elif _is_return(line.text):
                self._parse_return(block)
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

## class Docatron
## This class parses the doc.
##     WEIRD INDENT
##
## Params:
##   files {string[]}: The files to parse. If this is a really long description
##       then we can continue two indents in and the parser will be very happy
##       about this @Docatron.
##
##   token ('///') {string}: The token to start on.
##
##   callback {function}: The callback function
##     Params:
##       data {string}: Some data this is a super
##           long description too.
##
##       callback2 {function}: Another callback
##
##         Params:
##           data2 {string}: More data!
##
##     Returns:
##       {string}: The return value

## property Docatron.name
## The name of the thing @Docatron.doit.

## function Docatron.doit
## Do some stuff.
## Params:
##   food (5) {int}: Food to eat
##   cheese {function}: a callback
##
## Returns:
##   {int}: How much food got eaten
class DocatronParser(object):
    def __init__(self, files, token='///', indent=2):
        self._token = token.strip()
        self._indent = indent
        self._blocks = OrderedDict()
        self._nodes = OrderedDict()
        for name in files:
            self._parse_file(name)
        for filename, blocks in self._blocks.iteritems():
            for block in blocks:
                node = self._parse_block(block, filename)
                self._nodes[node.name] = node

    def get_nodes(self):
        return self._nodes

    def _has_token(self, line):
        return line.strip().startswith(self._token)

    def _strip_token(self, line):
        return line.strip()[len(self._token + ' '):]

    def _parse_block(self, block, filename):
        node = Node(block, filename, None)
        prev_node = self._nodes.get(node.name)
        if prev_node is not None:
            raise DocatronSyntaxError(
                'duplicate nodes: found here first: %s line %s' %
                    (prev_node.filename, prev_node.lineno),
                filename,
                node.lineno)
        return node

    def _parse_file(self, filename):
        current_block = []
        with open(filename) as f:
            for i, line in enumerate(f):
                if self._has_token(line):
                    line = self._strip_token(line)
                    if line:
                        current_block.append(
                            Line(line, self._indent, filename, i + 1))
                elif current_block:
                    if not filename in self._blocks:
                        self._blocks[filename] = []
                    self._blocks[filename].append(current_block)
                    current_block = []


class WriterNode(object):
    def __init__(self, node):
        self.node = node
        self.children = {t: [] for t in Node.TOP_LEVEL_TYPES}

    def add_child(self, child):
        self.children[child.node.top_level_type].append(child)

    def to_html(self, top_level=False):
        html = [self.node.to_html(top_level=top_level)]

        def to_str(section):
            if section == Node.PROPERTY:
                return 'Properties'
            return section.capitalize() + 's'

        for section, children in self.children.iteritems():
            if not children:
                continue
            html.append(PARAMS % (to_str(section) + ':', _indent_block(
                '\n'.join([PARAM % _indent_block(child.to_html())
                           for child in children]))))

        return '\n'.join(html)


class DocatronWriter(object):
    def __init__(self, nodes):
        # Turn the Nodes into WriterNodes.
        self._nodes = OrderedDict([(k, WriterNode(v))
                                   for k, v in nodes.iteritems()])

        self._name_url_map = {}
        for node in nodes.values():
            self._name_url_map.update(node.get_name_url_map())

        names = self._nodes.keys()
        added = []
        for name in names:
            parents = [n for n in names if name.startswith('%s.' % n)]
            if not parents:
                continue

            max_length = max(map(len, parents))
            parent = [p for p in parents if len(p) == max_length][0]
            self._nodes[parent].add_child(self._nodes[name])
            added.append(name)

        for added_name in added:
            self._nodes.pop(added_name)

    def create_links(self, html):
        for name, url in self._name_url_map.iteritems():
            html = re.sub(r'@%s\b' % re.escape(name),
                          '<a href="#%s">%s</a>' % (url, name), html)
        return html

    def write_html(self, f):
        html = []
        for node in self._nodes.values():
            html.append(BASE_ITEM % _indent_block(node.to_html(top_level=True)))
        f.write(self.create_links(BASE % _indent_block('\n'.join(html))))


if __name__ == '__main__':
    parser = argparse.ArgumentParser('DOCATRON documentation generator')
    parser.add_argument('-t', default='///',
                        help='Token to start DOCATRON comments (default "///")')
    parser.add_argument('-o', help='File to write output to')
    parser.add_argument('-i', default=2,
                        help='Indent level for doc strings')
    parser.add_argument('file', nargs='+', help='The files to parse')
    args = parser.parse_args()
    parser = DocatronParser(args.file, token=args.t, indent=args.i)
    writer = DocatronWriter(parser.get_nodes())

    if args.o:
        with open(args.o, 'w') as f:
            writer.write_html(f)
    else:
        writer.write_html(sys.stdout)
