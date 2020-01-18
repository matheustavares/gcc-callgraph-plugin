
.PHONY: callgraph
callgraph:
	gcc -fplugin=python \
	    -fplugin-arg-python-script=/plugin/gcc-callgraph-plugin.py \
	    -flto -flto-partition=none \
	    main.c -o .tmp-bin
	rm .tmp-bin

