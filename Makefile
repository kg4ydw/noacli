
UI= qtail_ui.py noacli_ui.py
SRCFILES=$(shell git ls-files | grep -v gitignore)
DISTFILES=$(SRCFILES) qtail_ui.py

all: $(UI)

%.py: %.ui
	pyuic5 -o $@ $<

tar: noacli.tgz


noacli.tgz: $(DISTFILES)
	rm -f noacli.tgz
	tar czvf noacli.tgz $(DISTFILES)

clean:
	rm *~ TAGS
clobber: clean
	rm -f noacli.tgz

