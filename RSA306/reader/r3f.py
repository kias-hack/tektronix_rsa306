from .reader import RSAReader
import numpy as np
import os
from typing import List
from RSA306.headers import FooterClass

class R3FFile(RSAReader):
    """Чтение r3f файлов"""
    _footer : List[FooterClass]

    def footerData(self) -> List[FooterClass]:
        return self._footer

    def _openFiles(self) -> None:
        self._headerFile = open(self._pathToFile, 'rb')
        self._dataFile = open(self._pathToFile, 'rb')

    def _parseData(self) -> None:
        fileSize = os.path.getsize(self._dataFile.name)
        numFrames = int((fileSize/self._dataFormat.framesize) - 1)

        """formatted processing loop based on number of frames in data file"""
        fps = 13698
        loop = 0
        while numFrames > 0:
            if numFrames > fps:
                process_data = fps
            else:
                process_data = numFrames
            if loop == 0:
                startpoint = self._dataFormat.frameoffset
            elif loop > 0:
                startpoint = loop * fps * self._dataFormat.framesize
            self._readADCData(process_data, startpoint)
            self._ddc()
            numFrames -= fps
            loop += 1

        self._dataFile.close()

    def _readADCData(self, process_data, startpoint) -> None:
        self._dataFile.seek(startpoint)
        adcsamples = np.empty(process_data * self._dataFormat.samplesize)
        fstart = 0
        fstop = self._dataFormat.samplesize
        self._footer = list(range(process_data))
        for i in range(process_data):
            frame = self._dataFile.read(self._dataFormat.nonsampleoffset)
            adcsamples[fstart:fstop] = np.frombuffer(frame, dtype=np.int16)
            fstart = fstop
            fstop = fstop + self._dataFormat.samplesize

            self._footer[i] = self._parse_footer(self._dataFile.read(self._dataFormat.nonsamplesize))

        self._ADC = adcsamples * self._channelCorrection.adcscale

    def _parse_footer(self, raw_footer) -> FooterClass:
        # Parses footer based on internal footer documentation
        footer = FooterClass()
        footer.reserved = np.frombuffer(raw_footer[0:6], 
            dtype=np.uint16, count=3)
        footer.frame_id = np.frombuffer(raw_footer[8:12],
            dtype=np.uint32, count=1)[0]
        footer.trigger2_idx = np.frombuffer(raw_footer[12:14],
            dtype=np.uint16, count=1)[0]
        footer.trigger1_idx = np.frombuffer(raw_footer[14:16],
            dtype=np.uint16, count=1)[0]
        footer.time_sync_idx = np.frombuffer(raw_footer[16:18],
            dtype=np.uint16, count=1)[0]
        footer.frame_status = '{0:8b}'.format(
            int(np.frombuffer(raw_footer[18:20], dtype=np.uint16, count=1)))
        footer.timestamp = np.frombuffer(raw_footer[20:28], 
            dtype=np.uint64, count=1)[0]
        
        return footer