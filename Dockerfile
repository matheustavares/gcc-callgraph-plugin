FROM ubuntu:xenial

RUN apt-get update
RUN apt-get install -y gcc g++ git make graphviz python3 python3-dev \
		       python3-yaml python3-six python3-pygments python3-lxml \
		       libpython3.5 libgcc1 libc6 python3-sphinx \
		       gcc-5-plugin-dev libjs-sphinxdoc

WORKDIR /tmp
RUN git clone https://github.com/davidmalcolm/gcc-python-plugin.git
WORKDIR /tmp/gcc-python-plugin
RUN make -j$(nproc) install PYTHON=python3 PYTHON_CONFIG=python3-config
RUN rm -rf /tmp/gcc-python-plugin

RUN mkdir /plugin
COPY gcc-callgraph-plugin.py /plugin/

RUN mkdir /src
WORKDIR /src
CMD "bash"

