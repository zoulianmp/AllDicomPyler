#!/usr/bin/env python
# -*- coding: ISO-8859-1 -*-
# dicomeditor.py
"""dicompyler plugin that displays a tree view of the DICOM data structure.
Int this treeview,you can select any one dicom tag and modify it's value.
When you make sure,you can save current modified contents to new dicom format file"""



import threading, Queue
import wx
from wx.xrc import XmlResource, XRCCTRL, XRCID
from wx.lib.pubsub import Publisher as pub
from wx.gizmos import TreeListCtrl as tlc
from dicompyler import guiutil, util
#import pydicom as dicom
import dicom

def pluginProperties():
    """Properties of the plugin."""

    props = {}
    props['name'] = 'DICOM Editor'
    props['description'] = "Edit tag's value in a tree view of a DICOM data stucture"
    props['author'] = 'Zou Lian'
    props['version'] = 0.4
    props['plugin_type'] = 'menu'
    props['plugin_version'] = 1
    props['min_dicom'] = []
    props['recommended_dicom'] = ['rtss', 'rtdose', 'rtplan', 'ct']

    return props



        
        
class plugin:

    def __init__(self, parent):

        self.parent = parent

        # Set up pubsub
        pub.subscribe(self.OnUpdatePatient, 'patient.updated.raw_data')

        # Load the XRC file for our gui resources
        self.res = XmlResource(util.GetExtraPluginsPath('dicomeditor/dicomeditor.xrc'))
    
    def OnUpdatePatient(self, msg):
        """Update and load the patient data."""

        self.data = msg.data

        
    def pluginMenu(self, evt):
        """Anonymize DICOM / DICOM RT data."""

        dlgDicomEditor = self.res.LoadDialog(self.parent, "DicomEditorDialog")
        dlgDicomEditor.Init(self.data,self.res)
        
        if dlgDicomEditor.ShowModal() == wx.ID_OK:
            print "show the Dicom EditorDialog"            
            pass
            
        
        
        
        
        
        
class DicomEditorDialog(wx.Dialog):
    """Plugin to display DICOM data in a tree view."""

    def __init__(self):
        pre = wx.PreDialog()
        # the Create step is done by XRC.
        self.PostCreate(pre)


    def Init(self, data,res):
        """Method called after the dialog has been initialized."""

        # Initialize the panel controls
        self.choiceDICOM = XRCCTRL(self, 'choiceDICOM')
        self.saveNewDICOM = XRCCTRL(self, 'newFILEsave')
        self.tlcTreeView = DICOMTree(self)
        res.AttachUnknownControl('tlcTreeView', self.tlcTreeView, self)

        self.InitDICOMChoice(data)


        # Bind interface events to the proper methods
        wx.EVT_CHOICE(self, XRCID('choiceDICOM'), self.OnLoadTree)
        wx.EVT_BUTTON(self, XRCID('newFILEsave'), self.OnSaveNewDicom)
        
       # self.Bind(wx.EVEVT_TREELIST_SELECTION_CHANGED,self.OnTagSelectedChanged,self.tlcTreeView)
        self.Bind(wx.EVT_TREE_SEL_CHANGED,self.OnTagSelectedChanged,self.tlcTreeView)

        self.Bind(wx.EVT_WINDOW_DESTROY, self.OnDestroy)

                      


        # Decrease the font size on Mac
        font = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
        if guiutil.IsMac():
            font.SetPointSize(10)
            self.tlcTreeView.SetFont(font)


   

    def InitDICOMChoice(self, data):
        """Update and load the patient data."""
        
        self.choiceDICOM.Enable()
        self.choiceDICOM.Clear()
        self.choiceDICOM.Append("Select a DICOM dataset...")
        self.choiceDICOM.Select(0)
        self.tlcTreeView.DeleteAllItems()
        # Iterate through the message and enumerate the DICOM datasets
        for k, v in data.iteritems():
            if isinstance(v, dicom.dataset.FileDataset):
                i = self.choiceDICOM.Append(v.SOPClassUID.name.split(' Storage')[0])
                self.choiceDICOM.SetClientData(i, v)
            # Add the images to the choicebox
            if (k == 'images'):
                for imgnum, image in enumerate(v):
                    i = self.choiceDICOM.Append(
                        image.SOPClassUID.name.split(' Storage')[0] + \
                        ' Slice ' + str(imgnum + 1))
                    self.choiceDICOM.SetClientData(i, image)

    def OnDestroy(self, evt):
        """Unbind to all events before the plugin is destroyed."""

        pub.unsubscribe(self.OnUpdatePatient)

    def OnLoadTree(self, event):
        """Update and load the DICOM tree."""
        
        choiceItem = event.GetInt()
        # Load the dataset chosen from the choice control
        if not (choiceItem == 0):
            dataset = self.choiceDICOM.GetClientData(choiceItem)
        else:
            return
        
        self.tlcTreeView.DeleteAllItems()
        self.root = self.tlcTreeView.AddRoot(text=dataset.SOPClassUID.name)
        self.tlcTreeView.Collapse(self.root)

        # Initialize the progress dialog
        dlgProgress = guiutil.get_progress_dialog(
            wx.GetApp().GetTopWindow(),
            "Loading DICOM data...")
        # Set up the queue so that the thread knows which item was added
        self.queue = Queue.Queue()
        # Initialize and start the recursion thread
        self.t=threading.Thread(target=self.RecurseTreeThread,
            args=(dataset, self.root, self.AddItemTree,
            dlgProgress.OnUpdateProgress, len(dataset)))
        self.t.start()
        # Show the progress dialog
        dlgProgress.ShowModal()
        dlgProgress.Destroy()
        self.tlcTreeView.SetFocus()
        self.tlcTreeView.Expand(self.root)

    def RecurseTreeThread(self, ds, parent, addItemFunc, progressFunc, length):
        """Recursively process the DICOM tree."""
        for i, data_element in enumerate(ds):
            # Check and update the progress of the recursion
            if (length > 0):
                wx.CallAfter(progressFunc, i, length, 'Processing DICOM data...')
                if (i == length-1):
                    wx.CallAfter(progressFunc, i, len(ds), 'Done')
            # Add the data_element to the tree if not a sequence element
            if not (data_element.VR == 'SQ'):
                wx.CallAfter(addItemFunc, data_element, parent)
            # Otherwise add the sequence element to the tree
            else:
                wx.CallAfter(addItemFunc, data_element, parent, needQueue=True)
                item = self.queue.get()
                # Enumerate for each child element of the sequence
                for i, ds in enumerate(data_element.value):
                    sq_item_description = data_element.name.replace(" Sequence", "")
                    sq_element_text = "%s %d" % (sq_item_description, i+1)
                    # Add the child of the sequence to the tree
                    wx.CallAfter(addItemFunc, data_element, item, sq_element_text, needQueue=True)
                    sq = self.queue.get()
                    self.RecurseTreeThread(ds, sq, addItemFunc, progressFunc, 0)

    def AddItemTree(self, data_element, parent, sq_element_text="", needQueue=False):
        """Add a new item to the DICOM tree."""

        # Set the item if it is a child of a sequence element
        if not (sq_element_text == ""):
            item = self.tlcTreeView.AppendItem(parent, text=sq_element_text)
        else:
            # Account for unicode or string values
            if isinstance(data_element.value, unicode):
                item = self.tlcTreeView.AppendItem(parent, text=unicode(data_element.name))
            else:
                item = self.tlcTreeView.AppendItem(parent, text=str(data_element.name))
            # Set the value if not a sequence element
            if not (data_element.VR == 'SQ'):
                if (data_element.name == 'Pixel Data'):
                    arrayLen = 'Array of ' + str(len(data_element.value)) + ' bytes'
                    self.tlcTreeView.SetItemText(item, arrayLen, 1)
                elif (data_element.name == 'Private tag data'):
                    self.tlcTreeView.SetItemText(item, 'Private tag data', 1)
                else:
                    self.tlcTreeView.SetItemText(item, unicode(data_element.value), 1)
            # Fill in the rest of the data_element properties
            self.tlcTreeView.SetItemText(item, unicode(data_element.tag), 2)
            self.tlcTreeView.SetItemText(item, unicode(data_element.VM), 3)
            self.tlcTreeView.SetItemText(item, unicode(data_element.VR), 4)
        if (needQueue):
            self.queue.put(item)
            
            
    def OnTagSelectedChanged(self,evt):
        """Respond to the Tag Selected Changed """
      
        item = evt.GetItem()
        
        itemtext1 = self.tlcTreeView.GetItemText(item, 0)
        itemtext2 = self.tlcTreeView.GetItemText(item, 1)
        itemtext3= self.tlcTreeView.GetItemText(item, 2)
        
        print "Selected itemd is ", itemtext1, itemtext2, itemtext3
            
    def OnSaveNewDicom(self, evt):
        """Get the directory selected by the user."""
        dlg = wx.DirDialog(
            self, defaultPath = self.ExportPath,
            message="Choose a folder to save the anonymized DICOM data...")
        if dlg.ShowModal() == wx.ID_OK:
            self.ExportPath = dlg.GetPath()
            self.txtExportFolder.SetValue(self.ExportPath)
        dlg.Destroy()

class DICOMTree(tlc):
    """DICOM tree view based on TreeListControl."""
    
    def __init__(self, *args, **kwargs):
        super(DICOMTree, self).__init__(*args, **kwargs)
        self.AddColumn('Name')
        self.AddColumn('Value')
        self.AddColumn('Tag')
        self.AddColumn('VM')
        self.AddColumn('VR')
        self.SetMainColumn(0)
        self.SetColumnWidth(0, 200)
        self.SetColumnWidth(1, 200)
        self.SetColumnWidth(3, 50)
        self.SetColumnWidth(4, 50)

        
    
        

