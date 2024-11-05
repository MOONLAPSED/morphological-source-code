# cognosis candidate release 0.4.20

3.13 std libs only

+++

ollama on the same machine as the python app

that's it

platforms: Win11 + Ubuntu

____
### how: ollama
go get ollama and run it
1) ollama pull gemma2
2) ollama pull nomic-embed-text
3) ollama serve

____
### how: cognosis
navigate to the cognosis folder
run `python3 -m venv venv` or simply `python .\__init__.py` or `python ./__init__.py -h`

____

current experiment:

`quimetime.py` at runtime makes a stateful quine json that, after 5 iterations, googles something, or something.

No further explanation nor rationalization shall be provided. Ever. In-general.