#!/usr/bin/env python
# -*- coding: ISO-8859-1 -*-
# mcsimexport.py
"""dicompyler plugin that converts DICOM / DICOM RT data to MCSIM Format."""
# Copyright (c) 2011 Anthony ventura
# This file is part of dicompyler, relased under a BSD license.
#    See the file license.txt included with this distribution, also
#    available at http://code.google.com/p/dicompyler/
#

import wx
from wx.xrc import XmlResource, XRCCTRL, XRCID
from wx.lib.pubsub import Publisher as pub
import os, threading, subprocess
import guiutil, util

def pluginProperties():
    """Properties of the plugin."""
    
    props = {}
    props['name'] = 'MCSIM Export'
    props['description'] = "Exports DICOM RT Plan Data to MCSIM format"
    props['author'] = 'Anthony Ventura'
    props['version'] = 0.1
    props['plugin_type'] = 'menu'
    props['plugin_version'] = 1
    props['min_dicom'] = ['rtplan']
    props['recommended_dicom'] = ['rtplan', 'images']

    return props

class plugin:

    def __init__(self, parent):

 
        self.parent = parent

        # Set up pubsub
        pub.subscribe(self.OnUpdatePatient, 'patient.updated.raw_data')


        # Load the XRC file for our gui resources
        self.res = XmlResource(util.GetExtraPluginsPath('mcsimexport/mcsimexport.xrc'))
        print util.GetExtraPluginsPath('mcsimexport/mcsimexport.xrc')    
        print self.res
        
        


    def OnUpdatePatient(self, msg):
        """Update and load the patient data."""

        self.data = msg.data

    def pluginMenu(self, evt):
        """Export DICOM RT Plan data."""
                                       
        dlgMCSIMExport = self.res.LoadDialog(self.parent, "MCSIMExportDialog")

        
        dlgMCSIMExport.Init(self.data)

        if dlgMCSIMExport.ShowModal() == wx.ID_OK:

            ExportPath = dlgMCSIMExport.ExportPath
            Arc = dlgMCSIMExport.Arc
            TableLoc = dlgMCSIMExport.TableLoc
            DICOMPath = dlgMCSIMExport.DICOMPath
            MeanISO = dlgMCSIMExport.MeanISO
            MakePhantom = dlgMCSIMExport.MakePhantom
            
            # If the path doesn't exist, create it
            if not os.path.exists(ExportPath):
                os.mkdir(ExportPath)

            # Initialize the progress dialog
            dlgProgress = guiutil.get_progress_dialog(
                wx.GetApp().GetTopWindow(),
                "Exporting DICOM data...")
            # Initialize and start the export thread
               
            if Arc:
                self.t=threading.Thread(target=self.ExportArcThread,
                    args=(self.data, ExportPath, DICOMPath, TableLoc,
                        MeanISO, MakePhantom, dlgProgress.OnUpdateProgress))
            else:
                self.t=threading.Thread(target=self.ExportStandardThread,
                    args=(self.data, ExportPath, DICOMPath, TableLoc,
                        MeanISO, MakePhantom, dlgProgress.OnUpdateProgress))
                
            self.t.start()
                       
            # Show the progress dialog
            dlgProgress.ShowModal()
            dlgProgress.Destroy()
          
        else:
            pass
        dlgMCSIMExport.Destroy()
        
        return

    def WriteCTCreateInpFiles(self, data, ExportPath, DICOMPath, TableLoc, MeanISO):
        
        ctcreatepath = 'ctcreate'
        
        inpfile = open(os.path.join(DICOMPath,'CT_create_DICOM.inp'),"wb")
        inpfile.write('DICOM\n')
        inpfile.write('slice_names\n')
        inpfile.write('0, 0, %.2f, %.2f, %.2f, %.2f\n' % (TableLoc - 64, TableLoc, MeanISO[2] - 32, MeanISO[2] + 32))
        inpfile.write('.25, .25, .25\n')
        inpfile.write('3, 0\n')    
        inpfile.write('AIR700ICRU\n')
        inpfile.write('70, 0.001, 0.07, 1\n')
        inpfile.write('ICRUTISSUE700ICRU\n')
        inpfile.write('1250, 0.07, 1.28, 1\n')
        inpfile.write('ICRPBONE700ICRU\n')
        inpfile.write('4000, 1.28, 2.88, 1\n')
        inpfile.close()

        ctslices = open(os.path.join(DICOMPath,'slice_names'),"wb")
        images = data['images']
        for n, image in enumerate(images):
            ctslices.write("CT." + image.SOPInstanceUID + ".dcm\n")
        ctslices.close()
        
        if os.path.isfile(os.path.join(DICOMPath,'slice_names.egsphant')):
            os.remove(os.path.join(DICOMPath,'slice_names.egsphant'))
        subprocess.call([ctcreatepath, 'CT_create_DICOM.inp'], cwd = DICOMPath, shell = True)
        phantomdirty = open(os.path.join(DICOMPath,'slice_names.egsphant'), "rb")
        phantomclean = open(os.path.join(ExportPath, 'slice_names.egs4phant'), "wb")
        for line in phantomdirty:
            phantomclean.write(line.replace("\r",""))
        phantomdirty.close()
        phantomclean.close()
        os.remove(os.path.join(DICOMPath,'slice_names.egsphant'))
        
        print ' done'
        
    def ExportStandardThread(self, data, ExportPath, DICOMPath, TableLoc, MeanISO, MakePhantom, progressFunc):
        """Export DICOM RT file."""

        drefmax = 1           
        NCASE = 50000000
        ECUTIN = 0.7
        PCUTIN = 0.01
        SMAX = 5.0
        IFORCE = '1'
        IETRACK = '1'
        IETRACKBONE = '0'
        IDOSE2H2O = '0'
        TargetToTopYJAW = ''
        TargetToTopXJAW = ''
        JAWThickness = ''
        TargetToMidMLC = ''
                
        #open field chamber backscatter coefficients for Varian machine
        a = 2.8612643716458816E-02
        b = -8.1534908329873923E-02
        c = -8.6712189751831939E-02
        d = -2.9176359534884280E-03
        f = 8.1286853911369879E-04
        g = 4.9532429020009107E-05
        h = -2.9919257506036598E-05
        i = 1.0112288951621546E+00
        j = 4.1436759244528129E-05
        k = 5.0394751411264875E-04
       
        #wedged field chamber backscatter coefficients for Varian machine
        A1 = 1.0008220503867418E+00;
        B1 = -4.3572810144278013E-06;
        C1 = 4.9180892284691819E-10;
        D1 = -2.1235626516894973E-01;
        E1 = 1.8903405046830720E+01;
        F1 = -2.7505001557737546E+02;
        G1 = 1.2251657083553619E+03;

        length = 0
        progress = 0
        numofbeams = 0
        rtplan = data['rtplan']
        if rtplan.has_key('Beams'):			
            for beam in rtplan.Beams:
                if beam.TreatmentDeliveryType == 'TREATMENT':
                    numofbeams = numofbeams + 1
                    length = length + beam.NumberofControlPoints                                        
                            
        if rtplan.has_key('Beams'):	
            egs4inp = open(os.path.join(ExportPath,'sim.egs4inp'),"wb")
            egs4inp.write("%s, %s\n" % (rtplan.PatientsName, rtplan.RTPlanLabel))
            egs4inp.write("0,1,0\n")
            egs4inp.write("/home/mctp/egs4/mcsim/slice_names.egs4phant\n")
            egs4inp.write("0,0,0\n")
            egs4inp.write("%.3f,%.3f,%.3f\n" % (ECUTIN, PCUTIN, SMAX))
            egs4inp.write("%d,%d,0,0,0,%s,%s,%s,%s,0\n" % (numofbeams, NCASE, IFORCE, IETRACK, IETRACKBONE, IDOSE2H2O))
            for beam in rtplan.Beams:
                if beam.TreatmentDeliveryType == 'TREATMENT':
                    beamnum = beam.BeamNumber
                    for refbeam in rtplan.FractionGroups[0].ReferencedBeams:
                        if refbeam.ReferencedBeamNumber == beamnum:
                            mu = refbeam.BeamMeterset
                    if beam.has_key('ControlPoints'):
                        xiso = beam.ControlPoints[0].IsocenterPosition[0]/10
                        yiso = beam.ControlPoints[0].IsocenterPosition[1]/10
                        ziso = beam.ControlPoints[0].IsocenterPosition[2]/10
                        gan = beam.ControlPoints[0].GantryAngle
                        coll = beam.ControlPoints[0].BeamLimitingDeviceAngle               
                        table = beam.ControlPoints[0].PatientSupportAngle
                        if beam.NumberofWedges != 0:
                            for wedge in beam.Wedges:
                                if wedge.WedgeType == 'DYNAMIC':
                                    wang = wedge.WedgeAngle
                                    if wang < 60:
                                        wang = wang - 1
                                    if wedge.WedgeOrientation == 0:
                                        wdir = 1
                                    if wedge.WedgeOrientation == 180:
                                        wdir = 2

                        else:
                            wang = 0
                            wdir = 0

                        for bldp in beam.ControlPoints[0].BeamLimitingDevicePositions:
                            if bldp.RTBeamLimitingDeviceType == 'ASYMX':
                                x1 = bldp.LeafJawPositions[0]/-10 
                                x2 = bldp.LeafJawPositions[1]/10
                            if bldp.RTBeamLimitingDeviceType == 'ASYMY':
                                y1 = bldp.LeafJawPositions[0]/-10 
                                y2 = bldp.LeafJawPositions[1]/10
                            if bldp.RTBeamLimitingDeviceType == 'X':
                                x1 = bldp.LeafJawPositions[0]/-10 
                                x2 = bldp.LeafJawPositions[1]/10
                            if bldp.RTBeamLimitingDeviceType == 'Y':
                                y1 = bldp.LeafJawPositions[0]/-10 
                                y2 = bldp.LeafJawPositions[1]/10

                        egs4inp.write("0,2,%.2f,%.2f,%.2f,-9,9,-9,9\n" % (xiso, yiso, ziso)) 
                        egs4inp.write("2,2,1,60.0\n")
                        egs4inp.write("/home/mctp/egs4/mcsim/v6_62s_1_40x40.egsphsp1\n")
                        egs4inp.write("%0.1f,%0.1f,%0.1f,%0.1f,%0.1f,%0.1f,%0.1f\n" % (TargetToTopXJAW+JAWThickness,
                            100-TargetToTopXJAW-JAWThickness,73.0,TargetToTopYJAW,TargetToTopXJAW,JAWThickness,TargetToMidMLC))
                        egs4inp.write("5,0,%.3e\n" % drefmax)
                        egs4inp.write("%.1f,%.1f,%.1f\n" % (gan, table, coll))
                        egs4inp.write("%.1f,%.1f,%.1f,%.1f,1,0.012,0.019\n" % (x1, x2, y1,y2))
                        egs4inp.write("/home/mctp/egs4/mcsim/beam%d.mlc\n" % beamnum) 
                        egs4inp.write("%d,%d,6,1\n" % (wang, wdir))
                        if wang !=0:
                            egs4inp.write("/home/mctp/egs4/mcsim/Varian-Golden-STT-Tables\n")
                        egs4inp.write("0,0\n")
                   
                        beamfile = open(os.path.join(ExportPath,'beam%d.mlc' % beamnum),"wb")
                        beamfile.write("File Rev = G\n")
                        beamfile.write("Treatment = Dynamic Dose\n")                    
                        beamfile.write("Last Name = %s\n" % rtplan.PatientsName)
                        beamfile.write("First Name = null\n")
                        beamfile.write("Patient ID = %s\n" % rtplan.PatientID)
                        beamfile.write("Number of Fields = %d\n" % beam.NumberofControlPoints)
                        beamfile.write("Number of Leaves = 120\n")
                        beamfile.write("Tolerance = 0.2\n\n")

                        xin = x1 + x2
                        yin = y1 + y2
                        if (xin < 3): xin = 3
                        if (yin < 3): yin = 3
                        if wang == 0:
                            temp = a
                            temp = temp + b * xin
                            temp = temp + c * yin
                            temp = temp + d * pow(xin, 2.0)
                            temp = temp + f * pow(yin, 2.0)
                            temp = temp + g * pow(xin, 3.0)
                            temp = temp + h * pow(yin, 3.0)
                            temp = temp + i * xin * yin
                            temp = temp + j * pow(xin, 2.0) * yin
                            temp = temp + k * xin * pow(yin, 2.0)
                            temp = (xin * yin) / temp
                            mu = mu / temp
                        else:
                            temp = A1 
                            temp = temp + B1 * pow(xin, 2.0)
                            temp = temp + C1 * pow(xin, 4.0)
                            temp = temp + D1 / pow(xin, 2.0)
                            temp = temp + E1 / pow(xin, 4.0)
                            temp = temp + F1 / pow(xin, 6.0)
                            temp = temp + G1 / pow(xin, 8.0)
                            mu = mu / temp
                        
                        beam_has_mlc = False
                        for ctrlpt in beam.ControlPoints:
                            doseindex = ctrlpt.CumulativeMetersetWeight/beam.FinalCumulativeMetersetWeight
                            deliver = mu * doseindex
                            beamfile.write("Field = %d of %d\n" % (ctrlpt.ControlPointIndex + 1, beam.NumberofControlPoints))
                            beamfile.write("Index = %f\n" % doseindex)
                            beamfile.write("Carriage Group = 1\n")                 
                            beamfile.write("Operator = null\n")
                            beamfile.write("Collimator = %.1f\n" % coll)
                                      
                            if ctrlpt.has_key('BeamLimitingDevicePositions'):
                                for bldp in ctrlpt.BeamLimitingDevicePositions:
                                    if bldp.RTBeamLimitingDeviceType == 'MLCX':
                                        mlcbldp = bldp
                                        beam_has_mlc = True
                            if beam_has_mlc: 
                                for leafpair in range (0, 60):
                                    beamfile.write("Leaf %dA = %f\n" % (leafpair+1, mlcbldp.LeafJawPositions[60+leafpair]/10))
                                for leafpair in range (0, 60):                                    
                                    beamfile.write("Leaf %dB = %f\n" % (leafpair+1, mlcbldp.LeafJawPositions[leafpair]/-10))    
                            else: 
                                for leafpair in range (0, 60):
                                    beamfile.write("Leaf %dA = %f\n" % (leafpair+1, 20.1))
                                for leafpair in range (0, 60):                                    
                                    beamfile.write("Leaf %dB = %f\n" % (leafpair+1, 20.1))  

                            delivertxt = "Deliver %f M" % deliver
                            beamfile.write("Note = %d\n" % len(delivertxt))
                            beamfile.write(delivertxt + "\n")
                            beamfile.write("Shape = 0\n")
                            beamfile.write("Magnification = 1.0\n\n")                                                     
                            progress = progress + 1
                            wx.CallAfter(progressFunc, progress, length,
                                    'Exporting ' + str(progress) + ' of ' + str(length) + ' Control Points')
                        beamfile.write("CRC = 0")        
                        beamfile.close()
            egs4inp.close()				
        if MakePhantom:    
            wx.CallAfter(progressFunc, 98, 100, 'Converting CT to EGS Phantom')
            self.WriteCTCreateInpFiles(data, ExportPath, DICOMPath, TableLoc, MeanISO)
        wx.CallAfter(progressFunc, length-1, length, 'Done')

    def ExportArcThread(self, data, ExportPath, DICOMPath, TableLoc, MeanISO, MakePhantom, progressFunc):
        """Export Arc DICOM RT file."""

        drefmax = 1     
        NCASE = 1000000
        ECUTIN = 0.7
        PCUTIN = 0.01
        SMAX = 5.0
        IFORCE = '1'
        IETRACK = '1'
        IETRACKBONE = '0'
        IDOSE2H2O = '0'
        TargetToTopYJAW = ''
        TargetToTopXJAW = ''
        JAWThickness = ''
        TargetToMidMLC = ''
        
        #open field chamber backscatter coefficients
        a = 2.8612643716458816E-02
        b = -8.1534908329873923E-02
        c = -8.6712189751831939E-02
        d = -2.9176359534884280E-03
        f = 8.1286853911369879E-04
        g = 4.9532429020009107E-05
        h = -2.9919257506036598E-05
        i = 1.0112288951621546E+00
        j = 4.1436759244528129E-05
        k = 5.0394751411264875E-04
       

        progress = 0
        numofbeams = 0
        rtplan = data['rtplan']
        if rtplan.has_key('Beams'):			
            for beam in rtplan.Beams:
                if beam.TreatmentDeliveryType == 'TREATMENT':
                    numofbeams = numofbeams + beam.NumberofControlPoints - 1
        length = numofbeams                                        
                            

        rtplan = data['rtplan']
        if rtplan.has_key('Beams'):	
            egs4inp = open(os.path.join(ExportPath,'sim.egs4inp'),"wb")
            egs4inp.write("%s, %s\n" % (rtplan.PatientsName, rtplan.RTPlanLabel))
            egs4inp.write("0,1,0\n")
            egs4inp.write("/home/mctp/egs4/mcsim/slice_names.egs4phant\n")
            egs4inp.write("0,0,0\n")
            egs4inp.write("%.3f,%.3f,%.3f\n" % (ECUTIN, PCUTIN, SMAX))
            egs4inp.write("%d,%d,0,0,0,%s,%s,%s,%s,0\n" % (numofbeams, NCASE, IFORCE, IETRACK, IETRACKBONE, IDOSE2H2O))
            for beam in rtplan.Beams:
                if beam.TreatmentDeliveryType == 'TREATMENT':
                    beamnum = beam.BeamNumber
                    for refbeam in rtplan.FractionGroups[0].ReferencedBeams:
                        if refbeam.ReferencedBeamNumber == beamnum:
                            mu = refbeam.BeamMeterset
                    if beam.has_key('ControlPoints'):
                        xiso = beam.ControlPoints[0].IsocenterPosition[0]/10
                        yiso = beam.ControlPoints[0].IsocenterPosition[1]/10
                        ziso = beam.ControlPoints[0].IsocenterPosition[2]/10
                        coll = beam.ControlPoints[0].BeamLimitingDeviceAngle               
                        table = beam.ControlPoints[0].PatientSupportAngle
                        for bldp in beam.ControlPoints[0].BeamLimitingDevicePositions:
                            if bldp.RTBeamLimitingDeviceType == 'ASYMX':
                                x1 = bldp.LeafJawPositions[0]/-10 
                                x2 = bldp.LeafJawPositions[1]/10
                            if bldp.RTBeamLimitingDeviceType == 'ASYMY':
                                y1 = bldp.LeafJawPositions[0]/-10 
                                y2 = bldp.LeafJawPositions[1]/10
                            if bldp.RTBeamLimitingDeviceType == 'X':
                                x1 = bldp.LeafJawPositions[0]/-10 
                                x2 = bldp.LeafJawPositions[1]/10
                            if bldp.RTBeamLimitingDeviceType == 'Y':
                                y1 = bldp.LeafJawPositions[0]/-10 
                                y2 = bldp.LeafJawPositions[1]/10
            
                        xin = x1 + x2
                        yin = y1 + y2
                        if (xin < 3): xin = 3
                        if (yin < 3): yin = 3

                        temp = a
                        temp = temp + b * xin
                        temp = temp + c * yin
                        temp = temp + d * pow(xin, 2.0)
                        temp = temp + f * pow(yin, 2.0)
                        temp = temp + g * pow(xin, 3.0)
                        temp = temp + h * pow(yin, 3.0)
                        temp = temp + i * xin * yin
                        temp = temp + j * pow(xin, 2.0) * yin
                        temp = temp + k * xin * pow(yin, 2.0)
                        temp = (xin * yin) / temp
                        mu = mu / temp
                                               
                        lastdoseindex = 0
                        for ctrlpt in beam.ControlPoints:
                            if ctrlpt.ControlPointIndex == 0:
                                continue
                            egs4inp.write("0,2,%.2f,%.2f,%.2f,-9,9,-9,9\n" % (xiso, yiso, ziso)) 
                            egs4inp.write("2,2,1,60.0\n")
                            egs4inp.write("/home/mctp/egs4/mcsim/v6_62s_1_40x40.egsphsp1\n")
                            egs4inp.write("%0.1f,%0.1f,%0.1f,%0.1f,%0.1f,%0.1f,%0.1f\n" % (TargetToTopXJAW+JAWThickness,
                                100-TargetToTopXJAW-JAWThickness,73.0,TargetToTopYJAW,TargetToTopXJAW,JAWThickness,TargetToMidMLC))
                            egs4inp.write("5,0,%.3e\n" % drefmax)
                            egs4inp.write("%.1f,%.1f,%.1f\n" % (ctrlpt.GantryAngle, table, coll))
                            egs4inp.write("%.1f,%.1f,%.1f,%.1f,1,0.012,0.019\n" % (x1, x2, y1,y2))
                            egs4inp.write("/home/mctp/egs4/mcsim/beam%d-%d.mlc\n" % (beamnum, ctrlpt.ControlPointIndex+1))
                            egs4inp.write("0,0,6\n")
                            egs4inp.write("0,0\n")

                            beamfile = open(os.path.join(ExportPath,'beam%d-%d.mlc' % (beamnum, ctrlpt.ControlPointIndex+1)),"wb")
                            beamfile.write("File Rev = G\n")
                            beamfile.write("Treatment = Dynamic Dose\n")                    
                            beamfile.write("Last Name = %s\n" % rtplan.PatientsName)
                            beamfile.write("First Name = null\n")
                            beamfile.write("Patient ID = %s\n" % rtplan.PatientID)
                            beamfile.write("Number of Fields = 2\n")
                            beamfile.write("Number of Leaves = 120\n")
                            beamfile.write("Tolerance = 0.2\n\n")
                            doseindex = ctrlpt.CumulativeMetersetWeight/beam.FinalCumulativeMetersetWeight                  
                            deliver = mu * (doseindex - lastdoseindex)
                            lastdoseindex = doseindex
                            beamfile.write("Field = 1 of 2\n")
                            beamfile.write("Index = 0\n")
                            beamfile.write("Carriage Group = 1\n")                 
                            beamfile.write("Operator = null\n")
                            beamfile.write("Collimator = %.1f\n" % coll)

                            for bldp in ctrlpt.BeamLimitingDevicePositions:
                                if bldp.RTBeamLimitingDeviceType == 'MLCX':            
                                    mlcbldp = bldp
                            for leafpair in range (0, 60):
                                beamfile.write("Leaf %dA = %f\n" % (leafpair+1, mlcbldp.LeafJawPositions[60+leafpair]/10))
                            for leafpair in range (0, 60):                                
                                beamfile.write("Leaf %dB = %f\n" % (leafpair+1, mlcbldp.LeafJawPositions[leafpair]/-10))   

                            delivertxt = "Deliver 0 M"
                            beamfile.write("Note = %d\n" % len(delivertxt))
                            beamfile.write(delivertxt + "\n")
                            beamfile.write("Shape = 0\n")
                            beamfile.write("Magnification = 1.0\n\n") 

                            beamfile.write("Field = 2 of 2\n")
                            beamfile.write("Index = 1\n")
                            beamfile.write("Carriage Group = 1\n")                 
                            beamfile.write("Operator = null\n")
                            beamfile.write("Collimator = %.1f\n" % coll) 

                            for bldp in ctrlpt.BeamLimitingDevicePositions:
                                if bldp.RTBeamLimitingDeviceType == 'MLCX':            
                                    mlcbldp = bldp
                                for leafpair in range (0, 60):
                                    beamfile.write("Leaf %dA = %f\n" % (leafpair+1, mlcbldp.LeafJawPositions[60+leafpair]/10))
                                for leafpair in range (0, 60):                                
                                    beamfile.write("Leaf %dB = %f\n" % (leafpair+1, mlcbldp.LeafJawPositions[leafpair]/-10)) 
                                  
                            delivertxt = "Deliver %f M" % deliver
                            beamfile.write("Note = %d\n" % len(delivertxt))
                            beamfile.write(delivertxt + "\n")
                            beamfile.write("Shape = 0\n")
                            beamfile.write("Magnification = 1.0\n\n")   
                            beamfile.write("CRC = 0")        
                            beamfile.close()                                                  
                            progress = progress + 1
                            wx.CallAfter(progressFunc, progress, length,
                                    'Exporting ' + str(progress) + ' of ' + str(length) + ' Control Points')
            egs4inp.close()		
        if MakePhantom:    
            wx.CallAfter(progressFunc, 98, 100, 'Converting CT to EGS Phantom')
            self.WriteCTCreateInpFiles(data, ExportPath, DICOMPath, TableLoc, MeanISO)
        wx.CallAfter(progressFunc, length-1, length, 'Done')

class MCSIMExportDialog(wx.Dialog):
    """Dialog that shows the options to Export DICOM RT data."""

    def __init__(self):
        pre = wx.PreDialog()
        # the Create step is done by XRC.
        self.PostCreate(pre)

    def Init(self, data):
        """Method called after the dialog has been initialized."""

        print "Here is in the MCSIMExportDialog"
        # Set window icon
        if not guiutil.IsMac():
            self.SetIcon(guiutil.get_icon())

        # Initialize controls
        self.txtExportFolder = XRCCTRL(self, 'txtExportFolder')
        self.txtTable = XRCCTRL(self, 'txtTable')
        self.txtParameters = XRCCTRL(self, 'txtParameters')
        self.lblDescription = XRCCTRL(self, 'lblDescription')
        self.btnOK = XRCCTRL(self, 'wxID_OK')
        self.checkMakePhantom = XRCCTRL(self, 'checkMakePhantom')

        # Bind interface events to the proper methods
        wx.EVT_BUTTON(self, XRCID('btnFolderBrowse'), self.OnFolderBrowse)
        wx.EVT_BUTTON(self, wx.ID_OK, self.OnOK)
        wx.EVT_TEXT(self, XRCID('txtTable'), self.OnTableEnter)
        wx.EVT_CHECKBOX(self, XRCID('checkMakePhantom'), self.OnCheckMakePhantom)

        # Set and bold the font of the description label
        if guiutil.IsMac():
            font = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
            font.SetWeight(wx.FONTWEIGHT_BOLD)
            self.lblDescription.SetFont(font)

        # Initialize the import location via pubsub
        pub.subscribe(self.OnImportPrefsChange, 'general.dicom.import_location')
        pub.sendMessage('preferences.requested.value', 'general.dicom.import_location')

        # Pre-select the text on the text controls due to a Mac OS X bug
        #self.txtTextbox.SetSelection(-1, -1)
 
        # Initialize variables
        self.CanExport = True      
        self.Arc = False       
        self.MeanISO = [0.0, 0.0, 0.0]
        
        # Inspect Plan        
        numofbeams = 0
        numofcp = 0

        IsAll6x = True       
        rtplan = data['rtplan']
        self.txtParameters.AppendText('Patient\'s name: ' + rtplan.PatientsName + '\n')
        self.txtParameters.AppendText('Plan Label: ' + rtplan.RTPlanLabel + '\n')
        if rtplan.has_key('Beams'):			
            for beam in rtplan.Beams:
                if beam.TreatmentDeliveryType == 'TREATMENT':
                    numofbeams = numofbeams + 1
                    numofcp = numofcp + beam.NumberofControlPoints   
                    self.MeanISO[0] = self.MeanISO[0] + beam.ControlPoints[0].IsocenterPosition[0]/10
                    self.MeanISO[1] = self.MeanISO[1] + beam.ControlPoints[0].IsocenterPosition[1]/10
                    self.MeanISO[2] = self.MeanISO[2] + beam.ControlPoints[0].IsocenterPosition[2]/10
                    if numofbeams == 1:
                        if beam.ControlPoints[0].GantryRotationDirection == 'NONE':
                            self.Arc = False
                        else:
                            self.Arc = True
                    else:
                        if self.Arc:
                            if beam.ControlPoints[0].GantryRotationDirection == 'NONE':
                                self.CanExport = False
                        else:
                            if beam.ControlPoints[0].GantryRotationDirection != 'NONE':
                                self.CanExport = False
                    if (beam.ControlPoints[0].NominalBeamEnergy != 6.0) or (beam.RadiationType != 'PHOTON'):
                        self.CanExport = False
                        IsAll6x = False
            self.txtParameters.AppendText('Number of Treatment Beams: ' + str(numofbeams) + '\n')
            self.txtParameters.AppendText('Number of Control Points: ' + str(numofcp) + '\n')
            if numofbeams == 0:
                self.txtParameters.AppendText('This plan contains no Treatment Beams and therefore cannot be exported')
                self.CanExport = False
            else:
                self.MeanISO[0] = self.MeanISO[0] / numofbeams
                self.MeanISO[1] = self.MeanISO[1] / numofbeams
                self.MeanISO[2] = self.MeanISO[2] / numofbeams
                if not self.CanExport:
                    if IsAll6x:
                        self.txtParameters.AppendText('This plan contains a mix of Arc and Non-Arc beams and therefore cannot be exported')
                    else:
                        self.txtParameters.AppendText('This plan contains beams that are not 6MV Photons and is currently not supported')
        else:
            self.txtParameters.AppendText('This plan contains no Beams and therefore cannot be exported')
            self.CanExport = False       
        if self.Arc:
            self.txtParameters.AppendText('This is an Arc Plan. Each Control Point will be placed in its own Beam')       
        if not self.CanExport:
            self.btnOK.Enable(False)
            
        self.TableLoc = self.MeanISO[1] + 32
        self.txtTable.SetValue(str(self.TableLoc))
        
        if data.has_key('images'):
            self.MakePhantom = True
        else:
            self.txtTable.Enable(False)
            self.checkMakePhantom.SetValue(False)
            self.checkMakePhantom.Enable(False)
            self.MakePhantom = False
        
    def OnImportPrefsChange(self, msg):
        """When the import preferences change, update the values."""
        self.DICOMPath = unicode(msg.data)
        self.ExportPath = os.path.join(self.DICOMPath, 'mcsim') 
        self.txtExportFolder.SetValue(self.ExportPath)

    def OnFolderBrowse(self, evt):
        """Get the directory selected by the user."""
        dlg = wx.DirDialog(
            self, defaultPath = self.ExportPath,
            message="Choose a folder to save the anonymized DICOM data...")
        if dlg.ShowModal() == wx.ID_OK:
            self.ExportPath = dlg.GetPath()
            self.txtExportFolder.SetValue(self.ExportPath)
        dlg.Destroy()
        
    def OnTableEnter(self, evt):    
        val = self.txtTable.GetValue()
        if (val == '-') or (val == '.') or (val == '-.'):
            self.TableLoc = 0
        else:
            if self.is_number(val):
                self.TableLoc = float(val)
            else:
                self.txtTable.SetValue(str(self.TableLoc))
                
    def OnCheckMakePhantom(self, evt):
        self.txtTable.Enable(evt.IsChecked())
        self.MakePhantom = evt.IsChecked()
        
    def OnOK(self, evt):
        if self.CanExport:
            self.EndModal(wx.ID_OK)
        
    def is_number(self, s):       
        try:
            float(s)
            return True
        except ValueError:
            return False 
            


