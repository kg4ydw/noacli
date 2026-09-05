

__license__   = 'GPL v3'
__copyright__ = '2026 Steven Dick <kg4ydw@gmail.com>'

# saved search manager

from functools import partial
import re

from PyQt6.QtCore import Qt, QSettings, pyqtSlot, QModelIndex
from PyQt6.QtWidgets import QDialog, QDialogButtonBox
from lib.saved_searches_ui import Ui_saved_searches
from lib.datamodels import simpleTable
from lib.searchdock import groupList
from lib.datamodels import itemListModel

# XXX import / export saved searches (json?)
# XXX store saved searches in qsettings?
# XXX modify qtailbrowser to execute group searches
# XXX modify qtail for saved search context menu
# XXX modify qtail for manual(menu) and automatic saved searches
# XX context type: selection, line, word
# XX context menu: find regex match closest to mouse on current line?


class search_entry():
    def __init__(self, *, name, sexp, cfilter, ctemplate, imaction=0, findshow, findhighlight, ccontext=0, hideCols):
        def fixint(val, fallback=0):
            try:
                return int(val)
            except (ValueError, TypeError):
                return fallback
        def fixbool(val):
            if isinstance(val, bool): return val
            if val is None: return False
            try:
                return val.strip().lower()=="true"
            except (ValueError, TypeError):
                return False
        self.name = name or ""
        self.sexp = sexp
        self.cfilter = cfilter
        self.ctemplate = ctemplate
        self.imaction = fixint(imaction)
        self.findshow = fixbool(findshow)
        self.findhighlight = fixbool(findhighlight)
        self.ccontext = fixint(ccontext)
        self.hideCols = hideCols

    def validate(self):
        # cursory check to see if this is a good entry
        # manditory field
        if not self.sexp: return False
        if not re.compile(self.sexp): return False
        # exception    re.PatternError
        # optional fields, but they still need to be valid
        if self.cfilter and not re.compile(self.cfilter): return False
        # template is invalid if it references bad columns, but thats too hard to check
        # XXX range check imaction ccontext but only if we're paranoid
        # note: ccontext may be invalid if ctemplate is empty or malformed
        # XXXX maybe reset it to 0 rather than marking invalid?
        return True
        
class searchModel(itemListModel):
    defaultSearchModel=None

    def __init__(self):
        super().__init__(['Name','RegEx','filter cmd', 'ctemplate' ])
        # XXXXX
        
    @classmethod
    def getDefaultSearchModel(cls):
        # reuse if possible, load if not
        if not searchModel.defaultSearchModel:
            cls.defaultSearchModel = searchModel()
        if searchModel.defaultSearchModel.isEmpty():
            cls.defaultSearchModel.loadFromSettings() # load it
        return cls.defaultSearchModel

    @classmethod
    def resetDefaultSearchModel(cls):
        # force a reload from scratch
        cls.defaultSearchModel = searchModel()
        cls.defaultSearchModel.loadFromSettings()
        return cls.defaultSearchModel

    def loadFromSettings(self):
        qs = QSettings()
        sz = qs.value("savedsettings/size")
        size = qs.beginReadArray("savedsearch")
        for i in range(size):
            qs.setArrayIndex(i)
            entry = search_entry(
                name=qs.value("name",""), sexp=qs.value("sexp"),
                cfilter=qs.value('cfilter'), ctemplate=qs.value("ctemplate"),
                imaction=qs.value('imaction'),
                findshow=qs.value('findshow'),
                findhighlight=qs.value('findhighlight'),
                ccontext=qs.value('ccontext'), hideCols=qs.value('hideCols'))
            #if entry.validate(): # XXXX
            self.appendItem(entry)
        qs.endArray()
    def saveToSettings(self):
        qs = QSettings()
        size = self.rowCount(None)
        qs.beginWriteArray("savedsearch", size )
        for row in range(size):
            qs.setArrayIndex(row)
            index = self.index(row,0)
            entry = self.getItem(index)
            qs.setValue("name", entry.name)
            qs.setValue("sexp", entry.sexp)
            qs.setValue("cfilter", entry.cfilter)
            qs.setValue("ctemplate", entry.ctemplate)
            qs.setValue("imaction", entry.imaction)
            qs.setValue("findshow", entry.findshow)
            qs.setValue("findhighlight", entry.findhighlight)
            qs.setValue("ccontext", entry.ccontext)
            qs.setValue("hideCols", entry.hideCols)
        qs.endArray()
        # XXXX handle delete

    def data(self, index, role):
        if not self.validateIndex(index): return None
        entry = self.getItem(index)
        col = index.column()
        if role==Qt.ItemDataRole.DisplayRole:
            if col==0: return entry.name
            if col==1: return entry.sexp
            if col==2: return entry.cfilter
            if col==3: return entry.ctemplate
            # didn't put the rest in the table heading
        return None


class saved_searches(QDialog):
    # XXXX self.valid = False when anything is updated?
    def __init__(self, tail, searchmodel=None):
        super().__init__()
        self.ui = Ui_saved_searches()
        self.ui.setupUi(self)
        self.qtail = tail
        self.ui.sexp.setText(self.qtail.ui.searchTerm.text())
        self.samples = groupList()
        self.old_sexp = ''
        self.extmodel = False
        if searchmodel:
            self.searchmodel = searchmodel
            self.extmodel = True
        else:
            self.searchmodel = searchModel.getDefaultSearchModel()
        self.ui.ssearches.setModel(self.searchmodel)
        # don't set smatches model until later
        # XXXX set ssearches model
        # these connections were too messy to do in designer
        self.ui.disableAll.clicked.connect(partial(self.ui.findShow.setChecked,False))
        self.ui.disableAll.clicked.connect(partial(self.ui.findShowHighlights.setChecked,False))
        self.ui.disableAll.clicked.connect(partial(self.ui.immediate_action.setCurrentIndex,0))
        self.ui.disableAll.clicked.connect(partial(self.ui.ccontext.setCurrentIndex,0))
        #
        self.valid = False # XX use this somewhere
        apply = self.ui.buttonBox.button(QDialogButtonBox.StandardButton.Apply)
        apply.clicked.connect(self.apply)
        apply.setEnabled(False) # can't apply until something is changed
        rbutton = self.ui.buttonBox.button(QDialogButtonBox.StandardButton.Reset)
        rbutton.clicked.connect(self.resetSearches)
        if self.extmodel: # can't reset non-default
            rbutton.setEnabled(False)  # XXXX hide it instead?
        self.show()
        for b in self.ui.buttonBox.buttons():
            b.setDefault(False)
            b.setAutoDefault(False)

    def resetMatches(self):
        # release old model
        self.samples = None
        self.old_sexp = ''
        # start a new one
        self.ui.smatches.setModel(None)
        self.valid = False

    @pyqtSlot()
    def saveNew(self):
        try:
            entry = self.saveEntry(append=True)
        except re.PatternError as e:
            self.ui.sresult.setPlaintText(f"{e.msg}\nat {e.pos}")

    @pyqtSlot()
    def deleteEntry(self):
        # get index of current selection and delete that row
        sel = self.ui.ssearches.selectionModel().selectedRows()
        if not sel: return
        i = sel[0].row()
        self.searchmodel.removeRows(i,1,None)
        self.somethingChanged()
        # XXXX delete from qsettings too?
        # delete entry from model and qsettings?

    @pyqtSlot()
    def saveEntry(self, append=False):
        self.somethingChanged()
        entry = self.makenewentry()
        if not entry or  not entry.validate(): return
        # XXX validate ctemplate for bad references?
        # if not valid, run test and check valid again

        # get index of current selection and replace the data there
        sel = self.ui.ssearches.selectionModel().selectedRows()
        if append or not sel:  # save new item
            index = None
        elif len(sel) != 1:  # this can't happen but just in case...
            self.ui.ssearches.clearSelection()
            return
        else:
            index = sel[0]
        if not index:
            self.searchmodel.appendItem(entry)
            # XX and select new row?
        else:
            # assume view row corresponds to model row
            self.searchmodel.setItem(index, entry)

    @pyqtSlot()
    def clearEntry(self):
        # XX prompt for accidental data loss?
        self.ui.ssearches.clearSelection()
        self.ui.sname.clear()
        self.ui.sexp.clear()
        self.ui.fcmd.clear()
        self.ui.hideCols.clear()
        self.ui.immediate_action.setCurrentIndex(0)
        self.ui.findShow.setChecked(False)
        self.ui.findShowHighlights.setChecked(False)
        self.ui.ccontext.setCurrentIndex(0)
        self.ui.ctemplate.clear()
        self.ui.sresult.clear()
        self.samples = None
        self.ui.smatches.setModel(None)
        self.valid = False
        
    @pyqtSlot(QModelIndex)
    def selectEntry(self, index):
        # copy selected entry to the form fields
        self.resetMatches()
        entry = index.model().getItem(index) # XXXX
        self.ui.sname.setText(entry.name)
        self.ui.sexp.setText(entry.sexp)
        self.ui.fcmd.setText(entry.cfilter)
        self.ui.hideCols.setText(entry.hideCols)
        self.ui.immediate_action.setCurrentIndex(entry.imaction)
        self.ui.findShow.setChecked(entry.findshow)
        self.ui.findShowHighlights.setChecked(entry.findhighlight)
        self.ui.ctemplate.setPlainText(entry.ctemplate)
        self.ui.sresult.clear()
        self.ui.ccontext.setCurrentIndex(entry.ccontext)
        self.valid = False
    
    def makenewentry(self):
        # manditory field
        sexp = self.ui.sexp.text()
        if not sexp: return None
        return search_entry(
            name=self.ui.sname.text(), sexp=sexp, cfilter=self.ui.fcmd.text(),
            ctemplate=self.ui.ctemplate.toPlainText(),
            imaction=self.ui.immediate_action.currentIndex(),
            findshow=self.ui.findShow.checkState()==Qt.CheckState.Checked, 
            findhighlight=self.ui.findShowHighlights.checkState()==Qt.CheckState.Checked, 
            ccontext=self.ui.ccontext.currentIndex(),
            hideCols=self.ui.hideCols.text()
        )

    @pyqtSlot(QModelIndex)
    def doubleSelectEntry(self, index):
        self.selectEntry(index)
        self.searchSamples()

    @pyqtSlot()
    def testTemplate(self):
        self.ui.sresult.clear()
        self.searchSamples()
        if not self.samples:
            self.ui.sresult.append("No matches found")
            return
        # get index of selection or make index of first row
        sel = self.ui.smatches.selectedIndexes()
        if sel:
            i = sel[0]
        else:
            i = self.samples.index(0,0)
        self.testTemplateRow(i)

    @pyqtSlot(QModelIndex)
    def testTemplateRow(self, index):
        searchitem = self.samples.getItem(index)
        template = self.ui.ctemplate.toPlainText()
        if not template: return
        if not searchitem or not searchitem.groups: return
        try:
            text = template.format(*searchitem.groups)
        except Exception as e:
            text = "Template failed: "+str(e)
        self.ui.sresult.setPlainText(text)
        self.valid = True
    
    @pyqtSlot()
    def newSearch(self):
        self.searchSamples()
        # anything else need done here?

    def searchSamples(self):
        sexp = self.ui.sexp.text()
        if not sexp:
            self.ui.sresult.append("Empty search")
            return
        if sexp == self.old_sexp:  # no updated needed XX?
            return
        self.resetMatches()
        self.old_sexp = sexp
        # XX could browse existing searches and see if we can reuse its model
        try:
            # XXX do some searches
            self.samples = groupList()
            self.ui.smatches.setModel(self.samples)
            i=5  # XXX SETTING or make this dynamic
            for s in self.qtail.findAllGroupIter(sexp):
               self.samples.addMatch(s)
               i-=1
               if i<0: break
            pass
        except Exception as e:
            self.ui.sresult.setPlainText(str(e))
            # XXXX reraise so sresult doesn't get clobbered?
 
    def somethingChanged(self):
        apply = self.ui.buttonBox.button(QDialogButtonBox.StandardButton.Apply)
        apply.setEnabled(True)
        
    def resetSearches(self):
        if self.extmodel: return  # don't reset non-default
        self.searchmodel = searchModel.resetDefaultSearchModel()
        self.ui.ssearches.setModel(self.searchmodel)

    def apply(self):
        apply = self.ui.buttonBox.button(QDialogButtonBox.StandardButton.Apply)
        if not self.extmodel: 
            self.searchmodel.saveToSettings()
        apply.setEnabled(False)

    def accept(self):
        if not self.extmodel: 
            self.searchmodel.saveToSettings()
        super().accept()
