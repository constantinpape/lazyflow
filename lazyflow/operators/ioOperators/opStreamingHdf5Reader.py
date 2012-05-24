from lazyflow.graph import Operator, InputSlot, OutputSlot
import vigra

class OpStreamingHdf5Reader(Operator):
    """
    The top-level operator for the data selection applet.
    """
    name = "OpStreamingHdf5Reader"
    category = "Reader"
    
    # The project hdf5 File object (already opened)
    ProjectFile = InputSlot(stype='hdf5File')

    # The internal path for project-local datasets
    InternalPath = InputSlot(stype='string')

    # Output data
    OutputImage = OutputSlot()
    
    def __init__(self, graph):
        super(OpStreamingHdf5Reader, self).__init__(graph=graph)

    def setupOutputs(self):
        # Read the dataset meta-info from the HDF5 dataset
        hdf5File = self.ProjectFile.value
        internalPath = self.InternalPath.value

        dataset = hdf5File[internalPath]
        
        try:
            # Read the axistags property without actually importing the data
            axistagsJson = hdf5File[internalPath].attrs['axistags'] # Throws KeyError if 'axistags' can't be found
            axistags = vigra.AxisTags.fromJSON(axistagsJson)
        except KeyError:
            # No axistags found.
            numDimensions = len(dataset.shape) 
            assert numDimensions != 1, "OpStreamingHdf5Reader: Support for 1-D data not yet supported"
            assert numDimensions != 2, "OpStreamingHdf5Reader: BUG: 2-D was supposed to be reshaped above."
            if numDimensions == 3:
                axistags = vigra.AxisTags(
                    vigra.AxisInfo('x',vigra.AxisType.Space),
                    vigra.AxisInfo('y',vigra.AxisType.Space),
                    vigra.AxisInfo('c',vigra.AxisType.Channels))
            if numDimensions == 4:
                axistags = vigra.AxisTags(
                    vigra.AxisInfo('x',vigra.AxisType.Space),
                    vigra.AxisInfo('y',vigra.AxisType.Space),
                    vigra.AxisInfo('z',vigra.AxisType.Space),
                    vigra.AxisInfo('c',vigra.AxisType.Channels))
            if numDimensions == 5:
                axistags =  vigra.AxisTags(
                    vigra.AxisInfo('t',vigra.AxisType.Time),
                    vigra.AxisInfo('x',vigra.AxisType.Space),
                    vigra.AxisInfo('y',vigra.AxisType.Space),
                    vigra.AxisInfo('z',vigra.AxisType.Space),
                    vigra.AxisInfo('c',vigra.AxisType.Channels))

        # Configure our slot meta-info
        self.OutputImage.meta.dtype = dataset.dtype
        self.OutputImage.meta.shape = dataset.shape
        self.OutputImage.meta.axistags = axistags

    def execute(self, slot, roi, result):
        # Read the desired data directly from the hdf5File
        key = roi.toSlice()
        hdf5File = self.ProjectFile.value
        internalPath = self.InternalPath.value

        # Access the data
        result[...] = hdf5File[internalPath][key]