"""
Содержит классы заполняемые из заголовков 
"""

from typing import List
import numpy as np

class VersionInfo:
	fileid : str
	endian : int
	fileformatversion = []
	apiversion = []
	fx3version = []
	fpgaversion = []
	devicesn : str

class InstrumentState:
	referencelevel : float
	centerfrequency : float
	temperature : float
	alignment : int
	freqreference : int
	trigmode : int
	trigsource : int
	trigtrans : int
	triglevel : float

class DataFormat:
	datatype : int
	frameoffset : int
	framesize : int
	sampleoffset : int
	samplesize : int
	nonsampleoffset : int
	nonsamplesize : int
	ifcenterfrequency : float
	samplerate : float
	bandwidth : float
	corrected : int
	timetype : int
	reftime : List[int]
	clocksamples : int
	timesamplerate : int

class ChannelCorrection:
	adcscale : float
	pathdelay : float
	correctiontype : int
	tableentries : int
	freqtable : np.array
	amptable : np.array
	phasetable : np.array

class FooterClass:
	def __init__(self):
		self.frame_descr = []
		self.frame_id = []
		self.trigger2_idx = []
		self.trigger1_idx = []
		self.time_sync_idx = []
		self.frame_status = []
		self.timestamp = []
