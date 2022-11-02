all: qtail_ui.py

%.py: %.ui
	pyuic5 -o $@ $<

SRCFILES=*.ui Makefile noacli-ideas.txt qtail.py qtail.png
DISTFILES=$(SRCFILES) qtail_ui.py

tar: noacli.tgz

noacli.tgz: $(DISTFILES)
	rm -f noacli.tgz
	tar czvf noacli.tgz $(DISTFILES)

clean:
	rm *~
clobber: clean
	rm -f noacli.tgz

