"""
testmodule.py
=============
Simple demo module that shows how processing modules can be written for mercure

This module takes the incoming DICOM series and applies a 2D Gaussian filter to each slice. The 
strength of the Gaussian filter can be specified via the module settings (e.g., {"sigma": 7})

To use this module, clone the repository to your local Linux machine and call 'make'. Afterwards,
the module can be installed via the mercure webinterface using the Docker tag 
'mercureimaging/mercure-testmodule:latest'. This tag can be changed in the file 'Makefile'
"""

# Standard Python includes
import os
import sys
import json
from pathlib import Path

# Imports for loading DICOMs
import pydicom
from pydicom.uid import generate_uid

# Imports for manipulating pixel data
from scipy.ndimage import gaussian_filter


def create_sr(file, in_folder, out_folder, series_uid, settings):
    """
    Creates a lightweight DICOM SR for the given DICOM image. This function will read the
    reference file from the in_folder and create a simple SR document that will be saved
    to the out_folder using the provided series_uid.
    """
    dcm_file_in = Path(in_folder) / file
    
    # Load the reference image to get study information
    ref_ds = pydicom.dcmread(dcm_file_in)
    
    # Generate new UIDs first
    new_sop_instance_uid = generate_uid()
    # Create output filename using the new SOP Instance UID
    out_filename = series_uid + "#" + new_sop_instance_uid + ".dcm"
    dcm_file_out = Path(out_folder) / out_filename
    
    # Create new SR dataset
    ds = pydicom.Dataset()
    
    # Add mandatory SR metadata
    ds.SOPClassUID = "1.2.840.10008.5.1.4.1.1.88.11"  # Basic Text SR
    ds.SOPInstanceUID = new_sop_instance_uid  # Use the pre-generated UID
    ds.SeriesInstanceUID = series_uid
    ds.StudyInstanceUID = ref_ds.StudyInstanceUID
    ds.SeriesNumber = ref_ds.SeriesNumber + settings["series_offset"]
    ds.SeriesDescription = "SR Report"
    ds.StudyDescription = ref_ds.StudyDescription + " OUTPUT SR" if hasattr(ref_ds, 'StudyDescription') else "OUTPUT SR"
    ds.Modality = "SR"
    ds.Manufacturer = "Mercure Test Module"
    
    # Type 1 attributes
    ds.SpecificCharacterSet = 'ISO_IR 100'
    ds.InstanceNumber = '1'
    ds.ContentDate = ref_ds.StudyDate
    ds.ContentTime = ref_ds.StudyTime
    ds.CompletionFlag = 'COMPLETE'
    ds.VerificationFlag = 'UNVERIFIED'
    
    # Type 2 attributes
    ds.InstanceCreationDate = ref_ds.StudyDate
    ds.InstanceCreationTime = ref_ds.StudyTime
    ds.TimezoneOffsetFromUTC = ''
    ds.PreliminaryFlag = ''
    
    # Copy patient and study information from reference image
    ds.PatientName = ref_ds.PatientName
    ds.PatientID = ref_ds.PatientID
    ds.StudyDate = ref_ds.StudyDate
    ds.StudyTime = ref_ds.StudyTime
    ds.AccessionNumber = ref_ds.AccessionNumber
    
    # Add mandatory content
    ds.ContentDate = ref_ds.StudyDate
    ds.ContentTime = ref_ds.StudyTime
    
    # Document Content Module
    ds.ValueType = 'CONTAINER'
    ds.ContinuityOfContent = 'SEPARATE'
    
    # Document Relationship Context
    ds.ConceptNameCodeSequence = [pydicom.Dataset()]
    concept_name = ds.ConceptNameCodeSequence[0]
    concept_name.CodeValue = '11528-7'
    concept_name.CodingSchemeDesignator = 'LN'
    concept_name.CodeMeaning = 'Radiology Report'
    
    # Observation Context
    ds.ObservationDateTime = ref_ds.StudyDate + ref_ds.StudyTime
    ds.ObserverType = 'DEVICE'
    ds.ObserverIdentificationCodeSequence = [pydicom.Dataset()]
    observer = ds.ObserverIdentificationCodeSequence[0]
    observer.CodeValue = 'MERCURE_TEST'
    observer.CodingSchemeDesignator = 'L'
    observer.CodeMeaning = 'Mercure Test Module'
    
    # Content Template
    ds.ContentTemplateSequence = [pydicom.Dataset()]
    template = ds.ContentTemplateSequence[0]
    template.MappingResource = 'DCMR'
    template.TemplateIdentifier = '2000'
    
    # Content Sequence (Document Content)
    ds.ContentSequence = []
    
    # Add processing description
    proc_desc = pydicom.Dataset()
    proc_desc.RelationshipType = 'CONTAINS'
    proc_desc.ValueType = 'TEXT'
    proc_desc.TextValue = 'Image processed with Gaussian filter (sigma=' + str(settings["sigma"]) + ')'
    proc_desc.ConceptNameCodeSequence = [pydicom.Dataset()]
    proc_desc.ConceptNameCodeSequence[0].CodeValue = '121106'
    proc_desc.ConceptNameCodeSequence[0].CodingSchemeDesignator = 'DCM'
    proc_desc.ConceptNameCodeSequence[0].CodeMeaning = 'Processing Description'
    ds.ContentSequence.append(proc_desc)
    
    # Add measurements container
    meas_container = pydicom.Dataset()
    meas_container.RelationshipType = 'CONTAINS'
    meas_container.ValueType = 'CONTAINER'
    meas_container.ContinuityOfContent = 'SEPARATE'
    meas_container.ConceptNameCodeSequence = [pydicom.Dataset()]
    meas_container.ConceptNameCodeSequence[0].CodeValue = '125007'
    meas_container.ConceptNameCodeSequence[0].CodingSchemeDesignator = 'DCM'
    meas_container.ConceptNameCodeSequence[0].CodeMeaning = 'Measurements'
    meas_container.ContentSequence = []
    
    # Function to create measurement
    def create_measurement(name, value, unit='mm', side=''):
        meas = pydicom.Dataset()
        meas.RelationshipType = 'CONTAINS'
        meas.ValueType = 'NUM'
        
        # Measurement value
        meas.MeasuredValueSequence = [pydicom.Dataset()]
        meas.MeasuredValueSequence[0].NumericValue = str(value)
        meas.MeasuredValueSequence[0].MeasurementUnitsCodeSequence = [pydicom.Dataset()]
        meas.MeasuredValueSequence[0].MeasurementUnitsCodeSequence[0].CodeValue = 'mm'
        meas.MeasuredValueSequence[0].MeasurementUnitsCodeSequence[0].CodingSchemeDesignator = 'UCUM'
        meas.MeasuredValueSequence[0].MeasurementUnitsCodeSequence[0].CodeMeaning = 'millimeter'
        
        # Concept name (measurement type)
        meas.ConceptNameCodeSequence = [pydicom.Dataset()]
        meas.ConceptNameCodeSequence[0].CodeValue = '410668003'  # Length
        meas.ConceptNameCodeSequence[0].CodingSchemeDesignator = 'SCT'  # SNOMED CT
        meas.ConceptNameCodeSequence[0].CodeMeaning = f'{side} {name} Length'
        
        return meas
    
    # Add each measurement
    meas_container.ContentSequence.append(create_measurement('Tibia', 38, side='Right'))
    meas_container.ContentSequence.append(create_measurement('Tibia', 39, side='Left'))
    meas_container.ContentSequence.append(create_measurement('Femur', 38, side='Right'))
    
    # Add measurements container to main content sequence
    ds.ContentSequence.append(meas_container)
    
    # Add reference to original image
    ds.CurrentRequestedProcedureEvidenceSequence = [pydicom.Dataset()]
    evidence = ds.CurrentRequestedProcedureEvidenceSequence[0]
    evidence.StudyInstanceUID = ref_ds.StudyInstanceUID
    evidence.ReferencedSeriesSequence = [pydicom.Dataset()]
    evidence.ReferencedSeriesSequence[0].SeriesInstanceUID = ref_ds.SeriesInstanceUID
    evidence.ReferencedSeriesSequence[0].ReferencedSOPSequence = [pydicom.Dataset()]
    evidence.ReferencedSeriesSequence[0].ReferencedSOPSequence[0].ReferencedSOPClassUID = ref_ds.SOPClassUID
    evidence.ReferencedSeriesSequence[0].ReferencedSOPInstanceUID = ref_ds.SOPInstanceUID
    
    # Create file meta information
    file_meta = pydicom.Dataset()
    file_meta.MediaStorageSOPClassUID = ds.SOPClassUID
    file_meta.MediaStorageSOPInstanceUID = ds.SOPInstanceUID
    file_meta.ImplementationClassUID = generate_uid()
    file_meta.TransferSyntaxUID = pydicom.uid.ExplicitVRLittleEndian
    
    # Create the final dataset
    ds.file_meta = file_meta
    ds.is_implicit_VR = False
    ds.is_little_endian = True
    
    # Save the SR
    ds.save_as(dcm_file_out, write_like_original=False)


def process_image(file, in_folder, out_folder, series_uid, settings):
    """
    Processes the DICOM image specified by 'file'. This function will read the
    file from the in_folder, apply a Gaussian filter, and save it to the out_folder
    using a new series UID given by series_uid. Processing paramters are passed
    via the settings argument
    """
    dcm_file_in = Path(in_folder) / file
    # Compose the filename of the modified DICOM using the new series UID
    out_filename = series_uid + "#" + file.split("#", 1)[1]
    dcm_file_out = Path(out_folder) / out_filename

    # Load the input slice
    ds = pydicom.dcmread(dcm_file_in)
    # Set the new series UID
    ds.SeriesInstanceUID = series_uid
    # Set a UID for this slice (every slice needs to have a unique instance UID)
    ds.SOPInstanceUID = generate_uid()
    # Add an offset to the series number (to avoid collosion in PACS if sending back into the same study)
    ds.SeriesNumber = ds.SeriesNumber + settings["series_offset"]
    # Update the series description to indicate which the modified DICOM series is
    ds.SeriesDescription = "FILTER(" + ds.SeriesDescription + ")"
    ds.StudyDescription = ds.StudyDescription + " OUTPUT FILTER" if hasattr(ds, 'StudyDescription') else "OUTPUT FILTER"
    # Access the pixel data of the input image, filter it, and store it
    pixels = ds.pixel_array
    blurred_pixels = gaussian_filter(pixels, sigma=settings["sigma"])
    ds.PixelData = blurred_pixels.tobytes()
    # Write the modified DICOM file to the output folder
    ds.save_as(dcm_file_out)


def main(args=sys.argv[1:]):
    """
    Main entry function of the test module. 
    The module is called with two arguments from the function docker-entrypoint.sh:
    'testmodule [input-folder] [output-folder]'. The exact paths of the input-folder 
    and output-folder are provided by mercure via environment variables
    """
    # Print some output, so that it can be seen in the logfile that the module was executed
    print(f"Hello, I am the mercure test module - Arogya")

    # Check if the input and output folders are provided as arguments
    if len(sys.argv) < 3:
        print("Error: Missing arguments!")
        print("Usage: testmodule [input-folder] [output-folder]")
        sys.exit(1)

    # Check if the input and output folders actually exist
    in_folder = sys.argv[1]
    out_folder = sys.argv[2]
    if not Path(in_folder).exists() or not Path(out_folder).exists():
        print("IN/OUT paths do not exist")
        sys.exit(1)

    # Load the task.json file, which contains the settings for the processing module
    try:
        with open(Path(in_folder) / "task.json", "r") as json_file:
            task = json.load(json_file)
    except Exception:
        print("Error: Task file task.json not found")
        sys.exit(1)

    # Create default values for all module settings
    settings = {"sigma": 7, "series_offset": 3000}

    # Overwrite default values with settings from the task file (if present)
    if task.get("process", ""):
        settings.update(task["process"].get("settings", {}))

    # Print the filter strength for debugging purpose
    print(f"Filter strength: {settings['sigma']}")

    # Collect all DICOM series in the input folder. By convention, DICOM files provided by
    # mercure have the format [series_UID]#[file_UID].dcm. Thus, by splitting the file
    # name at the "#" character, the series UID can be obtained
    series = {}
    for entry in os.scandir(in_folder):
        if entry.name.endswith(".dcm") and not entry.is_dir():
            # Get the Series UID from the file name
            seriesString = entry.name.split("#", 1)[0]
            # If this is the first image of the series, create new file list for the series
            if not seriesString in series.keys():
                series[seriesString] = []
            # Add the current file to the file list
            series[seriesString].append(entry.name)

    # Now loop over all series found
    for item in series:
        # Create a new series UID, which will be used for the modified DICOM series (to avoid
        # collision with the original series)
        series_uid = generate_uid()
        # Now loop over all slices of the current series and call the processing function
        for image_filename in series[item]:
            process_image(image_filename, in_folder, out_folder, series_uid, settings)
        
        # Create an SR document for the first image in the series
        if series[item]:
            sr_series_uid = generate_uid()
            create_sr(series[item][0], in_folder, out_folder, sr_series_uid, settings)


if __name__ == "__main__":
    main()
