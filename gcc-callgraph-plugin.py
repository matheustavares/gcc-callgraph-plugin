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

EXCLUDE = {"sha1-file.c:oid_object_info_extended"}
START = {"builtin/grep.c:cmd_grep", "builtin/grep.c:run"}
END = {"object.c:parse_object"}

OUT_FILE = 'callgraph.svg'

PROG_NAME = 'callgraph-plugin'

# HACK: print on stderr by default to avoid messing with the pipe to ld.
sys.stdout = sys.stderr

class Out:
    RED = '\033[1;31;49m'
    GREEN = '\033[1;32;49m'
    YELLOW = '\033[1;33;49m'
    END = '\033[m'

    @classmethod
    def cprint(cls, msg, color):
        print(color + msg + cls.END)

    @classmethod
    def info(cls, msg):
        print("%s: %s" % (PROG_NAME, msg))

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
           the functions in start to any in of the ones in end'''
        forward = self.__search("forward", start)
        backward = self.__search("backward", end)
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
            Out.abort("failed to call 'dot'. Got:\n %s" % out.stdout)

    def print_final_report(self, output_file, graph, start, end, exclude):
        for f in start | end | exclude:
            if f not in graph:
                Out.warn('function "%s" not found.' % f)
        Out.success("written to %s" % output_file)

    def execute(self):
        if gcc.is_lto():
            graph = self.get_graph()
            finder = PathFinder(graph, EXCLUDE)
            nodes = finder.find(START, END)
            dot_str = self.to_dot(graph, nodes, START, END)
            self.write_out_file(dot_str, OUT_FILE)
            self.print_final_report(OUT_FILE, graph, START, END, EXCLUDE)

if sys.version_info.major != 3 or sys.version_info.minor < 5:
    Out.abort("must have python >= 3.5")

cg = OutputCallgraph(name='output-callgraph')
cg.register_before('whole-program')

