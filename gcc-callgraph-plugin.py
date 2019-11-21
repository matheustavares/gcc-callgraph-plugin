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

# HACK: print on stderr by default to avoid messing with the pipe to ld.
sys.stdout = sys.stderr

if sys.version_info.major != 3 or sys.version_info.minor < 5:
    print("callgraph-plugin error: must have python >= 3.5")
    sys.exit(1)

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
        reachable = set()
        for s in start:
            for e in end:
                forward = self.__dfs("forward", s)
                backward = self.__dfs("backward", e)
                both = forward.intersection(backward)
                reachable = reachable.union(both)
        return reachable

    def __dfs(self, direction, start):
        '''Performs a dfs from @start in the given @direction and
           returns a set of nodes reachable from it. '''
        if start not in self.graph: return set()

        visited = {start}
        stack = [(start, 0)]
        while len(stack) > 0:
            fname, index = stack.pop()
            node = self.graph[fname]
            flist = node.callees if direction == "forward" else node.callers
            for i, child in enumerate(flist, start=index):
                if child not in visited and child in self.graph:
                    visited.add(child)
                    stack.append((fname, i+1)) # save where we are
                    stack.append((child, 0)) # go to child
                    break

        return visited

class OutputCallgraph(gcc.IpaPass):

    def gcc_node_to_str(self, gcc_node):
        return "%s:%s" % (gcc_node.decl.location.file, gcc_node.decl.name)

    def print_graph_debug(self, graph, nodes):
        '''Print @nodes from @graph.'''
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
            print("callgraph-plugin error: invalid filename: '%s'" % filename)
            sys.exit(1)
        out = subprocess.run(["dot", "-T%s" % fmt, "-o", filename],
                             stderr=subprocess.STDOUT, stdout=subprocess.PIPE,
                             encoding='ascii', input=dot_str)
        if out.returncode != 0:
            print("callgraph-plugin error: failed to call 'dot'")
            sys.exit(1)

    def execute(self):
        if gcc.is_lto():
            graph = self.get_graph()
            #self.print_graph_debug(graph, graph)
            finder = PathFinder(graph, EXCLUDE)
            nodes = finder.find(START, END)
            dot_str = self.to_dot(graph, nodes, START, END)
            #print(dot)
            filename = self.write_out_file(dot_str, OUT_FILE)
            #self.print_graph_debug(graph, nodes)
            print("callgraph-plugin: written to %s" % OUT_FILE)

cg = OutputCallgraph(name='output-callgraph')
cg.register_before('whole-program')

