#!/usr/bin/env python3

# Copyright 2019 Matheus Tavares <matheus.bernardino@usp.br>
#
# This program is free software: you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation, version 2 only of the
# License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program (./LICENSE). If not, see
# <https://www.gnu.org/licenses/>.

import gcc
import subprocess
import os
import sys
import textwrap
import yaml
from pathlib import Path

PROG_NAME = 'callgraph-plugin'

# HACK: print on stderr by default to avoid messing with the pipe to ld.
sys.stdout = sys.stderr

class Out:
    RED = '\033[1;31;49m'
    GREEN = '\033[1;32;49m'
    YELLOW = '\033[1;33;49m'
    END = '\033[m'

    @classmethod
    def wrap(cls, msg, prefix='  ', wrap_prefix='   ', width=80):
        wrapper = textwrap.TextWrapper(width=width, initial_indent=prefix,
                                       subsequent_indent=wrap_prefix)
        return '\n'.join(map(wrapper.fill, msg.splitlines()))

    @classmethod
    def cprint(cls, msg, color=None, wrap=True):
        if wrap:
            msg = cls.wrap(msg, prefix="", wrap_prefix="", width=80)
        if color == None:
            print(msg)
        else:
            print(color + msg + cls.END)

    @classmethod
    def info(cls, msg):
        cls.cprint("%s: %s" % (PROG_NAME, msg))

    @classmethod
    def warn(cls, msg):
        cls.cprint("%s warn: %s" % (PROG_NAME, msg), cls.YELLOW)

    @classmethod
    def error(cls, msg):
        cls.cprint("%s error: %s" % (PROG_NAME, msg), cls.RED)

    @classmethod
    def success(cls, msg):
        cls.cprint("%s: %s" % (PROG_NAME, msg), cls.GREEN)

    @classmethod
    def abort(cls, msg="", err=1):
        cls.error(msg if msg != "" else "unknown error")
        sys.exit(err)

class Config:

    CONFIG_FILENAME = ".gcc-callgraph.yml"
    DEFAULT_OUT_FILE = 'callgraph.svg'
    START, END, EXCLUDE, OUT_FILE = "start", "end", "exclude", "out_file"
    KNOWN_KEYS = {START, END, EXCLUDE, OUT_FILE}

    def __init__(self, config):
        self.start = self.__coerse_to_set(config.get(self.START, []))
        self.end =  self.__coerse_to_set(config.get(self.END, []))
        self.exclude =  self.__coerse_to_set(config.get(self.EXCLUDE, []))
        self.out_file = config.get(self.OUT_FILE, self.DEFAULT_OUT_FILE)

    @classmethod
    def __coerse_to_set(cls, setting):
        t = type(setting)
        if t == list:
            return set(setting)
        elif t == str:
            return {setting}
        else:
            Out.abort("internal error at __coerse_to_set: received a '%s'" % t)

    @classmethod
    def __validate(cls, config):
        cls.__check_unknown(config)
        cls.__check_types(config)

    @classmethod
    def __check_types(cls, config):
        for k, v in config.items():
            if type(v) == list:
                if not all(type(e) == str for e in v):
                    Out.abort(('invalid value for "%s". The list must contain'
                               ' only strings.') % (k))
            elif type(v) != str:
                Out.abort(('invalid value for "%s". Must be a string or string'
                           ' list') % k)

    @classmethod
    def __check_unknown(cls, config):
        diff = set(config) - cls.KNOWN_KEYS
        if len(diff) > 0:
            Out.abort("unknown settings: %s" % ", ".join(diff))

    @classmethod
    def read(cls):
        home = str(Path.home())
        local_conf = cls.CONFIG_FILENAME
        home_conf = os.path.join(home, cls.CONFIG_FILENAME)
        if os.path.isfile(local_conf):
            conf_path = local_conf
        elif os.path.isfile(home_conf):
            conf_path = home_conf
        else:
            return Config({})

        try:
           fd = open(conf_path, "r")
           config_dict = yaml.safe_load(fd.read())
           fd.close()
        except IOError as e:
            Out.abort('failed to read config file: "%s"' % str(e))
        except yaml.YAMLError as e:
            Out.abort('failed to parse config file: "%s"' % str(e))
        except Exception as e:
            Out.abort(str(e))
        cls.__validate(config_dict)
        return Config(config_dict)

class Node():

    def __init__(self, callers, callees):
        self.callers = callers
        self.callees = callees

    def copy(self):
        return Node(self.callers.copy(), self.callees.copy())

class PathFinder():

    def __init__(self, graph, exclude):
        '''exclude is a set of functions to be excluded from the PathFinder'''
        self.graph = {}
        for fname in graph:
            if fname not in exclude:
                self.graph[fname] = graph[fname].copy()

    def find(self, start, end):
        '''Returns a set of node names that are in some path between any of
           the functions in start to any in of the ones in end. If start or end
           are empty, don't limit the callgraph in the respective direction.'''
        forward = self.__search("forward", start)
        backward = self.__search("backward", end)
        len_start, len_end = len(start), len(end)
        if len_start == 0 and len_end == 0:
            return set(self.graph)
        elif len_start == 0:
            return backward
        elif len_end == 0:
            return forward
        return forward.intersection(backward)

    def __search(self, direction, start):
        '''Performs a dfs from the functions in the @start list in the given
           @direction and returns a set of nodes reachable from it. '''
        neighbours = {s for s in start if s in self.graph}
        visited = set()

        while len(neighbours) > 0:
            fname = neighbours.pop()
            visited.add(fname)
            node = self.graph[fname]
            flist = node.callees if direction == "forward" else node.callers
            for child in flist:
                if child not in visited and child in self.graph:
                    neighbours.add(child)

        return visited

class OutputCallgraph(gcc.IpaPass):

    def gcc_node_to_str(self, gcc_node):
        return "%s:%s" % (gcc_node.decl.location.file, gcc_node.decl.name)

    def print_graph_debug(self, graph, nodes):
        '''Print @nodes from @graph.'''
        Out.info("info on the callgraph:\n")
        for fname in nodes:
            if fname not in graph: continue
            print(fname)
            print("  callers:")
            for caller in graph[fname].callers:
                print("    %s" % caller)
            print("  callees:")
            for callee in graph[fname].callees:
                print("    %s" % callee)
            print("")

    def to_dot(self, graph, nodes, start, end):
        '''Return a string in dot format of the given @graph but restricted to 
           the given @nodes. The nodes in @start are colored blue and in @end,
           green.'''
        dot = 'digraph Callgraph {\n'
        for s in start:
            if s in nodes:
                dot += '"%s" [fillcolor=blue style=filled];\n' % s
        for e in end:
            if e in nodes:
                dot += '"%s" [fillcolor=green style=filled];\n' % e
        for fname in nodes:
            if fname not in graph: continue
            for callee in graph[fname].callees:
                if callee in nodes:
                    dot += '  "%s" -> "%s";\n' % (fname, callee)
        dot += "}\n"
        return dot

    def clean_lib_functions(self, graph):
        for fname in graph:
            node = graph[fname]
            node.callers = [c for c in node.callers if c in graph]
            node.callees = [c for c in node.callees if c in graph]

    def get_graph(self):
        graph = {}
        for cgn in gcc.get_callgraph_nodes():
            fname = self.gcc_node_to_str(cgn)
            callees = []
            callers = []
            for edge in cgn.callees:
                callees.append(self.gcc_node_to_str(edge.callee))
            for edge in cgn.callers:
                callers.append(self.gcc_node_to_str(edge.caller))
            graph[fname] = Node(callers, callees)
        self.clean_lib_functions(graph)
        return graph

    def write_out_file(self, dot_str, filename):
        fmt = os.path.splitext(filename)[1][1:]
        if len(fmt) == 0:
            Out.abort("invalid filename: '%s'" % filename)
        out = subprocess.run(["dot", "-T%s" % fmt, "-o", filename],
                             stderr=subprocess.STDOUT, stdout=subprocess.PIPE,
                             encoding='ascii', input=dot_str)
        if out.returncode != 0:
            Out.abort("failed to call 'dot'. Got:\n %s" % Out.wrap(out.stdout))

    def print_final_report(self, graph, config, found_paths):
        for f in config.start | config.end | config.exclude:
            if f not in graph:
                Out.warn('function "%s" not found.' % f)
        if found_paths:
            Out.success("written to %s" % config.out_file)
        else:
            Out.info("no paths found between the given function sets")

    def execute(self):
        if gcc.is_lto():
            config = Config.read()
            graph = self.get_graph()
            finder = PathFinder(graph, config.exclude)
            nodes = finder.find(config.start, config.end)
            found_paths = len(nodes) != 0
            if found_paths:
                dot_str = self.to_dot(graph, nodes, config.start, config.end)
                self.write_out_file(dot_str, config.out_file)
            self.print_final_report(graph, config, found_paths)

if sys.version_info.major != 3 or sys.version_info.minor < 5:
    Out.abort("must have python >= 3.5")

cg = OutputCallgraph(name='output-callgraph')
cg.register_before('whole-program')

