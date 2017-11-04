.. image:: https://travis-ci.org/Contextualist/goless.svg?branch=go-spec
    :target: https://travis-ci.org/Contextualist/goless?branch=go-spec
    :alt: build status
    :align: right

.. image:: https://coveralls.io/repos/github/Contextualist/goless/badge.svg?branch=go-spec
    :target: https://coveralls.io/r/Contextualist/goless?branch=go-spec
    :alt: coverage status
    :align: right

goless
======

Using the **goless** library, you can write `Go`_ language
style concurrent programs in Python.
**goless** provides functionality for channels, select, and goroutines.
**goless** allows you to use Go's beautiful and elegant
concurrency programming model,
but in the familiar and comfortable language of Python.

goless works on top of **gevent**, **PyPy**, or **Stackless Python**.
It works with PyPy, CPython, and Stackless Python interpreters,
and Python 2.6 to 3.4.

**goless** has extensive `testing`_, `documentation`_ and `examples`_.
See https://goless.readthedocs.org/ for more information.

.. _Go: http://www.golang.org
.. _testing: https://travis-ci.org/Contextualist/goless
.. _examples: https://github.com/Contextualist/goless/tree/master/examples
.. _documentation: https://goless.readthedocs.org/
