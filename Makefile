all: qtail_ui.py

%.py: %.ui
	pyuic5 -o $@ $<

