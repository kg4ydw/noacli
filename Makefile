
UI= qtail_ui.py noacli_ui.py
SRCFILES=*.ui Makefile noacli-ideas.txt qtail.py qtail.png
DISTFILES=$(SRCFILES) qtail_ui.py

all: $(UI)

%.py: %.ui
	pyuic5 -o $@ $<

tar: noacli.tgz


noacli.tgz: $(DISTFILES)
	rm -f noacli.tgz
	tar czvf noacli.tgz $(DISTFILES)

clean:
	rm *~
clobber: clean
	rm -f noacli.tgz

