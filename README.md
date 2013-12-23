# Docatron
Docatron generates documentation from source files. Look at the
[Move.js website](http://clarkduvall.github.io/move/documentation.html) for an
example of the generated docs, and the
[Move.js source](https://github.com/clarkduvall/move) for an example of
Docatron style comments.

## How to use
Docatron comments must start with a specific character sequence. For example,
the default is `///`, which means that any line starting with `///` is parsed as
a Docatron comment. This prefix can specified when running `docatron.py`.

Run `docatron.py --help` to show the help message.

## Syntax
Links to other parts of the documentation are prefixed with `@`. For example, if
there is a `Node` class, `@Node` anywhere in a Docatron comment will link to the
documentation for that class.

Most of the syntax is specified in [config.py](config.py) in the Regex section.
The HTML output can also be customized in [config.py](config.py).

A more complete overview of the syntax is on its way, but for now, look at the
[Move.js source](https://github.com/clarkduvall/move) for a complete example.

## TODO
Finish adding Docatron comments to docatron.py
