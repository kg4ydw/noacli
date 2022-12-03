
# Written by Steven Dick, who releases this file to Public Domain
# in the hopes that the terrible ideas here might get adopted into pyqt or qt

# replace qsettings with a python type safe version
# based on a dictionary of application specific settings

# This accomplishes two things:
# * force all settings in the dictionary to the correct type, reducing bugs
# * provide a single location for all default values (overriding supplied defaults)
# * print DEBUG warnings for settings not in the dictionary, using supplied default
# This does NOT do the following:
# * handle groups
# * handle complex types
# If you need these, save them in a separate group using the original QSettings
# which this should interoperate with without issue.

# dictionary format:
#  setting: [ default, description, type ]
#
# Use this by registering a dictionary fragment in each module like this:
# typedQSettings().registerOptions({
#   'optionname': [ 10, 'sample option defaulting to ten', int ],
# })
#

import sys
from PyQt5.QtCore import QSettings


class typedQSettings(QSettings):
    setdict = {}
    beginGroup = False  # not supported, use QSettings directly if you want this
    def __init__(self):
        super().__init__()

    def value(self, key, default):
        try:
            if key in self.setdict: # replace supplied default
                default = self.setdict[key][0]
        except Exception as e:
            self.setdict = {}  # only warn first time
            frame = sys.exc_info()[2].tb_frame.f_back
            print("Warn: typedQSettings.value called before dict set: "+str(frame.f_code)+"\n"+str(e)) # EXCEPT
            # frame.f_code.co_name
            return super(typedQSettings,self).value(key,default)
        v = super(typedQSettings,self).value(key,default)
        if key not in self.setdict: # return what we have
            print("Warning: setting {} missing from settings dictionary.".format(key)) # DEBUG EXCEPT
            # add it to dict, guess at type, add caller?
            self.setdict[key] = [v,"Unknown setting", type(v)]
            return v
        # bools don't cast well
        if self.setdict[key][2]==bool:
            if type(v)==bool: return v
            if type(v)==str: v=v.lower()
            return v in ['true','yes']
        # cast everything else
        try:
            return self.setdict[key][2](v)
        except Exception as e:
            print("Bad setting value for {}: '{}'".format(key,v)) # EXCEPT
            print(str(e)) # EXCEPT
            return default

    @classmethod
    def registerOptions(cls, options):
        '''Add new options to the settings.  Call this in each module if
           desired.
        '''
        for key,val in options.items():
            if key in cls.setdict:
                if val!=cls.setdict[key]:
                    print('Warning: conflicting option '+key) # EXCEPT
            else:
                cls.setdict[key] = val
