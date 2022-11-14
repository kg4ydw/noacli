
UI= qtail_ui.py noacli_ui.py settingsdialog_ui.py
SRCFILES=$(shell git ls-files | grep -v gitignore)
DISTFILES=$(SRCFILES) qtail_ui.py noaclires.py smalloutput.py

all: $(UI) resources

%.py: %.ui
	pyuic5 -o $@ $<

tar: noacli.tgz

# special case, modify it to use flowlayout
noacli_ui.py: noacli_ui.ui
	pyuic5 -o noacli_ui.py noacli_ui.ui
	sed -ie '/buttonBox/s/QtWidgets.Q.BoxLayout/FlowLayout/' noacli_ui.py
	echo 'from flowlayout import FlowLayout' >> noacli_ui.py

noacli.tgz: $(DISTFILES)
	rm -f noacli.tgz
	tar czvf noacli.tgz $(DISTFILES)

clean:
	rm *~ TAGS
clobber: clean
	rm -f noacli.tgz

resources: noaclires.py smalloutputres.py

line100.pbm: line100-ascii.pbm
	convert line100-ascii.pbm line100.pbm

noaclires.py: noaclires.qrc noacli.png  qtail.png
	rcc -g python -o noaclires.py noaclires.qrc
smalloutputres.py: smalloutputres.qrc line.svg
	rcc -g python -o smalloutputres.py smalloutputres.qrc

noaclires.rcc: noacli-res.qrc line100.pbm  noacli.png  qtail.png
	rcc -binary -o noacli-res.rcc noacli-res.qrc

# for emacs
findprint:
	grep --color -nH -e print *.py|egrep -av 'DEBUG|EXCEPT'
findxx:
	grep --color -nH -e XX *.py
findxxx:
	grep --color -nH -e XXX *.py
findxxxx:
	grep --color -nH -e XXXX *.py
findxxxxxx:
	grep --color -nH -e XXXXX *.py
finddebug:
	grep --color -nH -e '^ *[^ #].*DEBUG' *.py
