# This file has the basic configuration for the DOCATRON parser and writer.
# "param" refers to any function parameter or object property.
#
# "top level" refers to a block, for example:
#     /// function Foo.bar
#     /// description of Foo.bar
#     ///
#     /// Params:
#     ///   flop {String}: floppity flop
#
#     or
#
#     /// property Foo.baz
#     /// description of Foo.baz
# Foo.bar and Foo.baz are top level types, whereas flop is not.

######################
# Regex for DOCATRON #
######################

# Standard param "name {type}:"
PARAM_RE = r'(?P<name>[\w_\-]+)\s+{(?P<type>[^}]+)}:'
OPTIONAL_PARAM_RE = r'\[(?P<name>[\w_\-]+)\]\s+{(?P<type>[^}]+)}:'

# Optional param "name (default) {type}:"
PARAM_DEFAULT_RE = r'(?P<name>[\w_\-]+)\s+\((?P<default>(?:\\.|[^)])+)\)\s+{(?P<type>[^}]+)}:'
OPTIONAL_PARAM_DEFAULT_RE = r'\[(?P<name>[\w_\-]+)\]\s+\((?P<default>(?:\\.|[^)])+)\)\s+{(?P<type>[^}]+)}:'

# Return type "{type}:"
RETURN_RE = r'{(?P<type>[^}]+)}:'

# Params section
PARAM_SECTION_RE = r'(params|parameters|props|properties):\s*$'

# Returns section
RETURN_SECTION_RE = r'returns:\s*$'

# Type of a top level property
TYPE_RE = r'.*{(?P<type>[^}]+)}'

# A piece of code in a comment "|code|"
CODE_RE = r'\|([^\s]+)\|'


#####################
# HTML for DOCATRON #
#####################

# The containing element
BASE_HTML = '''<!doctype html>
<html>
<head>
  <link rel="stylesheet" type="text/css" href="css/style.css">
</head>
<body>
<!-- START TOC -->
%(toc)s
<!-- END TOC -->
<!-- START DOCS -->
%(content)s
<!-- END DOCS -->
</body>
</html>
'''

# A link created to a DOCATRON item
LINK_HTML = '<a href="#%(url)s" data-parent="%(parent_url)s">%(name)s</a>'

# A top level item
BASE_ITEM_HTML = '<div>\n%s\n</div>'

# A top level item heading
FIRST_LEVEL_HTML = '<a href="#" class="docs-toggle" data-toggle="%(url)s"><h2 id="%(url)s">%(type)s %(name)s</h2></a>'

# The container belonging to a top level item
FIRST_LEVEL_CONTAINER_HTML= '<div class="inner" id="inner-%(url)s">\n%(content)s\n</div>'

# A child of a top level item (e.g. a function on a class)
SECOND_LEVEL_HTML = '<h3 class="api-item" id="%(url)s">%(name)s<a class="anchor-link" href="#%(url)s"><span class="anchor"></span></a></h3>'

# A child of a top level item (e.g. a property on a class)
SECOND_LEVEL_WITH_TYPE_HTML = '<h3 class="api-item" id="%(url)s">%(type)s %(name)s<a class="anchor-link" href="#%(url)s"><span class="anchor"></span></a></h3>'

# Used in THIRD_LEVEL_*_HTML for the optional_html key
OPTIONAL_HTML = '<span class="optional">optional</span> '

# A secondary item heading
THIRD_LEVEL_HTML = '<h4 id="%(url)s">%(optional_html)s%(type)s %(name)s<a class="anchor-link" href="#%(url)s"><span class="anchor"></span></a></h4>'

# A secondary item heading with default value
THIRD_LEVEL_DEFAULT_HTML = '<h4 id="%(url)s">%(optional_html)s%(type)s %(name)s: %(default)s<a class="anchor-link" href="#%(url)s"><span class="anchor"></span></a></h4>'

# A parameter description
DESCRIPTION_HTML = '<p>%s</p>'

# A list of properties of a top level item, like the functions and properties
# of a class.
PROPERTY_LIST_HTML = '<span class="prop-heading">%(section)s</span>\n<ul>\n%(content)s\n</ul>'

# A list of parameters of a function or properties of an object.
PARAM_LIST_HTML = '<div><span class="param-heading">%(section)s</span>\n<ul>\n%(content)s\n</ul></div>'

# The return value of a function.
RETURN_HTML = '<span class="return-heading">Returns: %s</span>'

# A single parameter/property
PARAM_ITEM_HTML = '<li>\n%s\n</li>'

# How to display functions.
FUNCTION_PARAM_HTML = '%(type)s %(name)s'
OPTIONAL_FUNCTION_PARAM_HTML = '[%(type)s %(name)s]'
FUNCTION_SIGNATURE_HTML = '%(name)s(%(params)s)'
FUNCTION_SIGNATURE_WITH_RETURN_HTML = '%(return)s %(name)s(%(params)s)'

# How to display examples.
EXAMPLE_HTML = '<code class="example">%s</code>'
EXAMPLE_LEADING_SPACE = '&nbsp;'
EXAMPLE_END = '<br/>'

# Code inline in comments.
CODE_HTML = '<code>%s</code>'


####################################
# HTML for Table of Contents (TOC) #
####################################

# A top level link in the TOC
TOP_LEVEL_LINK_TOC = '<a data-toggle="%(url)s" class="toc-top" href="#%(url)s">%(name)s</a>'

# A link in the TOC
LINK_TOC = '<a href="#%(url)s" data-parent="%(parent_url)s">%(name)s</a>'

# The TOC container
BASE_TOC = '<div id="toc"><ul>\n%s\n</ul></div>'

# A top level TOC item
FIRST_LEVEL_TOC = '<li>%s</li>'

# A second level TOC container
SECOND_BASE_TOC = '<ul>\n%s\n</ul>'

# A second level TOC item
SECOND_LEVEL_TOC = '<li>%s</li>'

# The title of a section (e.g. "Functions")
SECTION_TITLE = '<b>%s</b>'
