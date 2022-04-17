from .reader import RSAReader
import numpy as np
import os

class R3AFile(RSAReader):
    """Чтение r3a r3h файлов"""
    def _openFiles(self) -> None:
        self._headerFile = open((self._pathToFile[:-1] + 'h'), 'rb')
        self._dataFile = open((self._pathToFile[:-1] + 'a'), 'rb')

    def _parseData(self) -> None:
        fileSize = int(os.path.getsize(self._dataFile.name))

        """raw processing loop based on file size in bytes"""
        bytes_per_second = 224000000
        loop = 0
        while fileSize > 0:
            if fileSize > bytes_per_second:
                process_data = bytes_per_second / 2 #two bytes per sample
            else:
                process_data = fileSize
            if loop == 0:
                startpoint = 0
            elif loop > 0:
                startpoint = loop * bytes_per_second
            self._readADCData(process_data, startpoint)
            self._ddc()
            
            fileSize -= bytes_per_second

            loop += 1

    def _readADCData(self, process_data, startpoint) -> None:
        self._dataFile.seek(startpoint)
        adcsamples = np.empty(process_data)
        adcsamples = np.fromfile(self._dataFile, dtype=np.int16, count=process_data)

        #Scale ADC data
        self._ADC = adcsamples * self._channelCorrection.adcscale