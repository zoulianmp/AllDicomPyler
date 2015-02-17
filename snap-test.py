#code snap for debug dicompyler.

import sys
import dicom
from dicompyler.dicomparser import DicomParser





folder = "F:\\TestDataDir\\150113-2638-01"

filename = "\\RS.1.2.246.352.71.4.23531169090.5301.20150129111233.dcm"

dcmfile = folder + filename

patient = {}

tds = {}
#tds = dicom.read_file(dcmfile,defer_size=100)

#fds = dicom.read_file(dcmfile, defer_size=100, force=True)

#print fds

filename = dcmfile

try:
                # Only pydicom 0.9.5 and above supports the force read argument
    if (dicom.__version__ >= "0.9.5"):
        tds = dicom.read_file(filename, defer_size=100, force=True)
    else:
        tds = dicom.read_file(filename, defer_size=100)
except (EOFError, IOError):
    # Raise the error for the calling method to handle
    raise
else:
    # Sometimes DICOM files may not have headers, but they should always
    # have a SOPClassUID to declare what type of file it is. If the
    # file doesn't have a SOPClassUID, then it probably isn't DICOM.
    print "the try has no excepts!"
    if not "SOPClassUID" in tds:
        raise AttributeError
                

if  "SOPClassUID" in tds:
    print "has SOPClassUID: ",tds.SOPClassUID
    


#if tds.Modality in ['RTSTRUCT']:
#    patient['rtss'] = tds
    
print "tds.keys() :",tds.keys()
print "StructureSetROISequence:", tds.StructureSetROISequence   

from dicom.tag import Tag

tg = Tag(0x30060020)
print "tag 0x30060020 is :",tg

print "using the tag as key:" ,tds[tg]

if 'StructureSetROISequence' in tds:
    print "Using the StructureSetROISequence "
    
    
if  tds.has_key(tg):
  #  print "haha using the tag as key:" ,tds[tg].value  
    for item in tds.StructureSetROISequence:
        data = {}
        number = item.ROINumber
        data['id'] = number
        data['name'] = item.ROIName
        print data

