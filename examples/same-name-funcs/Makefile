
.PHONY: callgraph
callgraph:
	gcc -fplugin=python \
	    -fplugin-arg-python-script=/plugin/gcc-callgraph-plugin.py \
	    -flto -flto-partition=none \
	    *.c *.h -o .tmp-bin
	rm .tmp-bin

