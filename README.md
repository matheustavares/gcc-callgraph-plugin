# gcc-callgraph-plugin

A python script to print call graphs during compilation with GCC. It uses the
[gcc-python-plugin](https://github.com/davidmalcolm/gcc-python-plugin)
architecture.

## Features

- Display the whole callgraph, considering all compilling files.
- Performs in O(V + E), where V is the number of functions and E is the number
  of calls.
- Possibility to restrict callgraph with sets of starting and ending functions.
- Possibility to exclude certain functions.
- Accept any output format known by `dot`.
- Differentiate two or more valid functions with the same name.

## Dependencies 

- python version >= 3.5
- [PyYAML](https://pyyaml.org/)
- [gcc-python-plugin](https://github.com/davidmalcolm/gcc-python-plugin)
- dot (from the [graphviz](https://www.graphviz.org/) package)

## Using

With the `gcc-python-plugin` installed, compile your code with:

```
    $ gcc -fplugin=python \
	  -fplugin-arg-python-script=<path to gcc-callgraph-plugin.py> \
	  -flto -flto-partition=none \
	  <other args>
```

This will generate a `callgraph.svg` image in the working directory, containing
the program's call graph.

Note:
- Give the full path to `-fplugin-arg-python-script`. Don't use `~/`, for
  example.
- When compiling and linking in two steps, don't forget to use those flags in
  both of them.
- If you are compilling a code with a Makefile, you can use `make CC="gcc
  -fplugin ..."`

## Configuring output

The plugin will read user specified settings from a `.gcc-callgraph.yml` file,
in the working directory or in the user's home directory (in this order). This
file must be in YAML format and can contain the following attributes:

- `start`: set of functions to start the callgraph at. Any call chain that
	   doesn't start in one of these is excluded.
- `end`: set of functions to end the callgraph at. Any call chain that does not
	 end in one of these is excluded.
- `exclude`: set of functions to be excluded from the callgraph.
- `out_file`: output file name. Extension must be one of the formats accepted by
	      `dot`, e.g. `.png` or `.svg`.

The first three can be strings or string lists and the forth must be a string.
The starting nodes will be colored blue and the end ones green.

As an example, with the following we get all paths from a function A to a
function B that don't contain a function C:

```
start: A
end: B
exclude: C
```

