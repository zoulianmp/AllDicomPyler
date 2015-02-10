Source code for the MCSIM Export Plugin for Varian LINACs.

This plugin can convert DICOM RT plan data to the format required by the MCSIM monte carlo dose calculation tool from Fox Chase Cancer Center.  

It can also create an input file to convert DICOM CT data to an EGS4 phantom using ctcreate from the National Research Council of Canada.

Supported plan types include: Open Field, Static MLC, Dynamic MLC, Dynamic Arc, Dose Dynamic Arc (RapidArc).

Requires: MCSIM from Fox Chase Cancer Center, EGS4, Reference Phase Space Data from MD Anderson Radiological Physics Center

Tested with dicompyler-0.4a1
Place files in baseplugins directory.

See Wiki for more information.