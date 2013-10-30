#!/usr/bin/env python2

import argparse
from collections import OrderedDict
import re
import sys

from config import *

class DocatronSyntaxError(Exception):
    def __init__(self, message, filename, lineno):
        Exception.__init__(self, '%s: %s line %d' % (message, filename, lineno))


def _indent_block(text):
    return '\n'.join(['  %s' % line for line in text.split('\n')])


def _indent_line(line, indent):
    return (' ' * indent) + line


def _is_params(text):
    return re.match(PARAM_SECTION_RE, text.lower())


def _is_optional(text):
    return (re.match(OPTIONAL_PARAM_RE, text) or
        re.match(OPTIONAL_PARAM_DEFAULT_RE, text))


def _is_param(text):
    return any([re.match(regex, text) for regex in
        [PARAM_RE, OPTIONAL_PARAM_RE, PARAM_DEFAULT_RE,
         OPTIONAL_PARAM_DEFAULT_RE]])


def _is_return(text):
    return re.match(RETURN_SECTION_RE, text.lower())


def _parse_line(regex_list, line):
    for regex in regex_list:
        result = re.match(regex, line)
        if result:
            return (result.groupdict(),
                    line.replace(result.group(0), '', 1).strip())
    return None


class _Description(object):
    def __init__(self, block, indent, first_line, lineno):
        # List of tuples of the form (is_example, text).
        self.description = []
        self._parse(block, indent, first_line, lineno)

    def __nonzero__(self):
        return len(self.description)

    def to_html(self):
        html = []
        for is_example, line in self.description:
            if is_example:
                html.append(EXAMPLE_HTML % re.sub(
                    r'(^|\n)( +)',
                    lambda m: m.group(1) + EXAMPLE_LEADING_SPACE *
                        len(m.group(2)),
                    line).replace('\n', EXAMPLE_END))
            else:
                html.append(DESCRIPTION_HTML % line)
        return '\n'.join(html)

    def _parse(self, block, indent, first_line, lineno):
        def indent_example(line):
            return ('  ' * (line.indent - indent - 3)) + line.text

        final_desc = []
        desc_list = [first_line]
        prev_lineno = lineno
        was_example = False
        sep = ' '
        while len(block):
            desc_line = block[0]
            is_example = desc_line.indent > indent + 2
            sep = '\n' if was_example else ' '

            # If this is a new paragraph or an example, add what we have to the
            # description list.
            if is_example and was_example:
                if desc_line.lineno > prev_lineno + 1:
                    desc_list.append('')
            elif (desc_line.lineno > prev_lineno + 1 or
                    is_example != was_example):
                if desc_list:
                    self.description.append((was_example, sep.join(desc_list)))
                desc_list = []

            prev_lineno = desc_line.lineno

            if _is_params(desc_line.text) or _is_return(desc_line.text):
                break

            if desc_line.indent < indent + 1:
                break

            block.pop(0)
            if is_example:
                desc_list.append(indent_example(desc_line))
            else:
                desc_list.append(desc_line.text)

            was_example = is_example

        if desc_list:
            self.description.append((was_example, sep.join(desc_list).strip()))


## class Node
## Represents a single piece of docatron data.
##
## Params:
##   block {@Line[]}: The lines to be parsed.
##   filename {string}: The file this node is a part of.
##   parent {@Node}: The parent node.
class Node(object):
    CLASS = 'class'
    OBJECT = 'object'
    FUNCTION = 'function'
    PROPERTY = 'property'
    EVENT = 'event'

    TOP_LEVEL_TYPES = (CLASS, OBJECT, FUNCTION, PROPERTY, EVENT)

    @staticmethod
    def section_to_str(section):
        if section == Node.PROPERTY:
            return 'Properties'
        return section.capitalize() + 's'

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
        self.params_text = None
        self.optional = False

        self._parse_block(block)

    ## function Node.get_name_node_map
    ## Gets a mapping of names to URLs from this node.
    ##
    ## Returns:
    ##   {dict string => @Node}: Mapping of names to @Node.
    def get_name_node_map(self):
        mapping = {self.name: self}
        for child in self.children:
            mapping.update(child.get_name_node_map())
        return mapping

    def get_short_name(self):
        return self.name.split('.')[-1]

    ## function Node.url
    ## Gets the URL for this node.
    ##
    ## Returns:
    ##   {string}: The node's URL.
    def url(self):
        url = self.name.lower().replace('.', '-')
        if self.parent:
            url = '%s-%s' % (self.parent.url(), url)
        if self.top_level_type:
            url = '%s-%s' % (self.top_level_type, url)
        return url

    def _get_signature_as_html(self):
        params = ', '.join([(OPTIONAL_FUNCTION_PARAM_HTML if
                c.optional else FUNCTION_PARAM_HTML) % {
            'type': c.top_level_type or c.type,
            'name': c.name
        } for c in self.children])

        if self.return_type is not None:
            return FUNCTION_SIGNATURE_WITH_RETURN_HTML % {
                'name': self.get_short_name(),
                'params': params,
                'return': self.return_type
            }

        return FUNCTION_SIGNATURE_HTML % {
            'name': self.get_short_name(),
            'params': params
        }

    def _is_function(self):
        type_ = self.top_level_type or self.type
        return type_.lower() == Node.FUNCTION

    def get_full_name(self):
        if self._is_function():
            return self._get_signature_as_html()
        return self.get_short_name()

    def get_heading_html(self):
        return FIRST_LEVEL_HTML % {
            'name': self.get_full_name(),
            'type': self.top_level_type,
            'url': self.url()
        }

    ## function Node.to_html
    ## Converts this node to HTML.
    ##
    ## Params:
    ##   top_level (False) {boolean}: Whether this is a top level node.
    ##
    ## Returns:
    ##   {string}: The HTML representation of this node.
    def to_html(self, no_heading=False):
        html = []
        name = self.get_full_name()

        if not no_heading:
            if self.top_level_type is not None:
                html.append((SECOND_LEVEL_HTML if self.type is None else
                             SECOND_LEVEL_WITH_TYPE_HTML) % {
                    'name': name,
                    'url': self.url(),
                    'type': self.type
                })
            else:
                html.append(
                    (THIRD_LEVEL_HTML if self.default is None else
                        THIRD_LEVEL_DEFAULT_HTML) % {
                        'name': name,
                        'type': self.type,
                        'default': self.default,
                        'url': self.url(),
                        'optional_html': OPTIONAL_HTML if self.optional else ''
                    })

        if self.description:
            html.append(self.description.to_html())

        if self.children:
            title = self.params_text
            if self.top_level_type == Node.CLASS:
                title = 'Constructor params:'
            html.append(PARAM_LIST_HTML % {
                'section': title,
                'content': _indent_block(
                    '\n'.join([PARAM_ITEM_HTML % _indent_block(p.to_html())
                               for p in self.children]))
            })

        if self.return_type:
            html.append(RETURN_HTML % self.return_type)
            if self.return_description:
                html.append(self.return_description.to_html())

        return '\n'.join(html)

    def __repr__(self):
        return '%s: %s\nType %s, Default %s\nReturns %s: %s\nChildren: %s' % (
            self.name, self.description, self.type or self.top_level_type,
            self.default, self.return_type, self.return_description,
            ', '.join([c.name for c in self.children]))

    def _parse_return(self, block):
        # Pop off "Returns:" first.
        block.pop(0)

        line = block[0]
        block.pop(0)

        result = _parse_line([RETURN_RE], line.text)
        if result is None:
            raise DocatronSyntaxError('bad return', self.filename, line.lineno)

        groups, rest = result

        self.return_type = groups.get('type')
        self.return_description = _Description(block, line.indent, rest,
                                               line.lineno)

    def _parse_params(self, block):
        line = block[0]
        self.params_text = re.match(
            PARAM_SECTION_RE,
            line.text.lower()).group(0).strip().capitalize()

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

        if _is_optional(line.text):
            result = _parse_line([OPTIONAL_PARAM_DEFAULT_RE, OPTIONAL_PARAM_RE],
                                 line.text)
            self.optional = True
        else:
            result = _parse_line([PARAM_DEFAULT_RE, PARAM_RE], line.text)
        if result is None:
            raise DocatronSyntaxError('param malformed',
                                      self.filename,
                                      line.lineno)

        groups, rest = result
        self.type = groups.get('type', '')
        self.name = groups.get('name', '')
        self.default = groups.get('default')
        if self.default:
            # HACK: Replace escaped parens with normal parens.
            self.default = self.default.replace('\)', ')')

        self.description = _Description(block, line.indent, rest, line.lineno)

        if len(block) and block[0].indent == line.indent + 1:
            self._parse_block(block)

    def _parse_top_level(self, block):
        line = block[0]
        block.pop(0)

        result = line.text.split()
        if len(result) < 2:
            raise DocatronSyntaxError('top level block must have a type',
                                      self.filename,
                                      line.lineno)

        self.top_level_type, self.name = result[:2]
        if self.top_level_type not in Node.TOP_LEVEL_TYPES:
            raise DocatronSyntaxError(
                'type must be one of: %s' % str(Node.TOP_LEVEL_TYPES),
                self.filename,
                line.lineno)

        if self.top_level_type == Node.PROPERTY:
            result = _parse_line([TYPE_RE], line.text)
            if result is None:
                raise DocatronSyntaxError('property must have a type',
                                          self.filename,
                                          line.lineno)
            groups, _ = result
            self.type = groups.get('type', '')

        self.description = _Description(block, line.indent - 1, '', line.lineno)

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


## class Line
## A DOCATRON line in a file.
##
## Params:
##   line {string}: The line to parse.
##   indent {int}: The indent level of this line.
##   filename {string}: The file this line belongs to.
##   lineno {int}: The line number in the file.
class Line(object):
    def __init__(self, line, indent, filename, lineno):
        num_spaces = len(line) - len(line.lstrip())
        if num_spaces % indent:
            raise DocatronSyntaxError('bad indent', filename, lineno)

        ## property Line.indent {int}
        ## The indent level of this line.
        self.indent = num_spaces / indent

        ## property Line.lineno {int}
        ## The line number of this line.
        self.lineno = lineno

        ## property Line.text {string}
        ## The actual text of the line.
        self.text = line.strip()

    def __repr__(self):
        return '%s: %s: %s' % (self.lineno, self.indent, self.text)

## class DocatronParser
## Parses a list of files into @Nodes so they can be used with the
## @DocatronWriter. The DOCATRON comments in the files parameter will be
## cross-referenced with each other.
##
## Params:
##   files {string[]}: A list of filenames to parse.
##   token ('///') {string}: The token that DOCATRON comments will start with.
##   indent (2) {int}: The indent that makes up one indent level for a DOCATRON
##     comment.
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

    ## function DocatronParser.get_nodes
    ## Gets the @Nodes parsed from the files passed to the parser.
    ##
    ## Returns:
    ##   {@Node[]}: The list of nodes.
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


## class WriterNode
## The node used by @DocatronWriter.
##
## Params:
##   node {@Node}: The @Node this wraps.
class WriterNode(object):
    def __init__(self, node):
        self.node = node
        self.children = OrderedDict([(t, []) for t in Node.TOP_LEVEL_TYPES])

    ## function WriterNode.add_child
    ## Adds a child to this node (e.g. a function that belongs to the class).
    ##
    ## Params:
    ##   child {@WriterNode}: The child to add.
    def add_child(self, child):
        self.children[child.node.top_level_type].append(child)

    ## function WriterNode.to_html
    ## Converts this node to HTML.
    ##
    ## Params:
    ##   top_level (False) {boolean}: Is this a top level node.
    ##
    ## Returns:
    ##   {string}: This node as HTML.
    def to_html(self, top_level=False):
        if top_level:
            heading = self.node.get_heading_html()
        html = [self.node.to_html(no_heading=top_level)]

        for section, children in self.children.iteritems():
            if not children:
                continue
            html.append(PROPERTY_LIST_HTML % {
                'section': Node.section_to_str(section) + ':',
                'content': _indent_block(
                    '\n'.join([PARAM_ITEM_HTML % _indent_block(child.to_html())
                               for child in children]))
            })

        if top_level:
            return '%s\n%s' % (heading,
                FIRST_LEVEL_CONTAINER_HTML % {
                    'url': self.node.url(),
                    'content': _indent_block('\n'.join(html))
                })
        return '\n'.join(html)


## class DocatronWriter
## Writes a DOCATRON document to HTML.
##
## Params:
##   nodes {@Node[]}: A list of nodes from @DocatronParser.get_nodes.
class DocatronWriter(object):
    def __init__(self, nodes):
        # Turn the Nodes into WriterNodes.
        self._nodes = OrderedDict([(k, WriterNode(v))
                                   for k, v in nodes.iteritems()])

        self._name_node_map = {}
        for node in nodes.values():
            self._name_node_map.update(node.get_name_node_map())

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

    ## function DocatronWriter.create_links
    ## Converts "@Name" syntax to links using the nodes passed into the
    ## constructor.
    ##
    ## Params:
    ##   html {string}: The HTML to convert links in.
    ##
    ## Returns:
    ##   {string}: The HTML with links.
    def create_links(self, html):
        names = sorted(self._name_node_map.keys(), key=len, reverse=True)

        for name in names:
            def sub_link(match):
                return LINK_HTML % {
                    'url': self._name_node_map[name].url(),
                    'name': match.group(1),
                    'parent_url': self._name_node_map[name.split('.')[0]].url()
                }

            html = re.sub(r'@(%ss?)\b' % re.escape(name), sub_link, html)
        return html

    def sub_code(self, html):
        return re.sub(CODE_RE, lambda m: CODE_HTML % m.group(1), html)

    ## function DocatronWriter.get_table_of_contents
    ## Creates the table of contents.
    ##
    ## Returns:
    ##   {string}: The table of contents as HTML.
    def get_table_of_contents(self):
        toc = []

        def create_link(writer_node, parent=None):
            return (LINK_TOC if parent else TOP_LEVEL_LINK_TOC) % {
                'name': writer_node.node.get_short_name(),
                'url': writer_node.node.url(),
                'parent_url': parent.node.url() if parent else None
            }

        for node in self._nodes.values():
            item = create_link(node)
            for section, children in node.children.iteritems():
                if children:
                    section_toc = '%s\n%s' % (
                        SECTION_TITLE % Node.section_to_str(section),
                        '\n'.join([SECOND_LEVEL_TOC % create_link(c, node)
                                   for c in children]))
                    item += SECOND_BASE_TOC % section_toc

            toc.append(FIRST_LEVEL_TOC % item)

        return BASE_TOC % _indent_block('\n'.join(toc))

    ## function DocatronWriter.write_html
    ## Writes the nodes to HTML.
    ##
    ## Params:
    ##   f {file}: The open file to write to.
    def write_html(self, f):
        html = []
        for node in self._nodes.values():
            html.append(BASE_ITEM_HTML % _indent_block(
                node.to_html(top_level=True)))

        f.write(self.create_links(self.sub_code(BASE_HTML % {
            'toc': _indent_block(self.get_table_of_contents()),
            'content': _indent_block('\n'.join(html))
        })))


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
