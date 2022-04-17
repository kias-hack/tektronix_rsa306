from RSA306.headers import VersionInfo, InstrumentState, DataFormat, ChannelCorrection
import numpy as np
from struct import unpack
from scipy import signal

class RSAReader(object):
	"""
	Интерфейс состоит из read метода который задает общий шаблон чтения файла. А также
	из методов (versionInfo, instrumentState, dataFormat, channelCorrection, ADC, IQ)
	которые дают возможность только просмотра данных которые были прочтены из файла. 

	Каждый наследник должен обязательно реализовать следующие методы (_openFiles, _parseData)

	TODO возможно будет уместно кидать исключение если не был вызван метод read?
	TODO вывести отдельное свойство на центральную частоту и полосу частот
	"""
	_ADC : np.array = None
	_IQ : np.array = None

	def __init__(self, path):
		self._pathToFile = path

		self._versionInfo = VersionInfo()
		self._instrumentState = InstrumentState()
		self._dataFormat = DataFormat()
		self._channelCorrection = ChannelCorrection()

		self._headerFile = None
		self._dataFile = None

		self._openFiles()

	@property
	def versionInfo(self) -> VersionInfo:
		return self._versionInfo

	@property
	def instrumentState(self) -> InstrumentState:
		return self._instrumentState

	@property
	def channelCorrection(self) -> ChannelCorrection:
		return self._channelCorrection

	@property
	def dataFormat(self) -> DataFormat:
		return self._dataFormat

	@property
	def ADC(self) -> np.array:
		return self._ADC

	@property
	def IQ(self) -> np.array:
		return self._IQ

	@property
	def centerFrequency(self) -> float:
		return self._instrumentState.centerfrequency

	def read(self) -> np.array:
		self._parseHeaderData()

		self._parseData()

		return self._IQ

	def _openFiles(self) -> None:
		"""
		Специфичное открытие файла. К примеру r3a содержит отдельный файл r3h 
		в котором хранятся заголовки 
		"""
		raise NotImplementedError("_openFiles")

	def _parseData(self) -> None:
		raise NotImplementedError("_parseData")

	def _parseHeaderData(self) -> None:
		# Parses the header section of *.r3f and *.r3h files.
		# Certain fields use np.frombuffer() rather than unpack() because
		# np.frombuffer() allows the user to specify data type.
		# unpack() saves data as a tuple, which can be used for printing
		# but not calculations
		data = self._headerFile.read(16384)

		# Get File ID and Version Info sections of the header
		self._versionInfo.fileid = "".join(map(chr, data[:27]))
		self._versionInfo.endian = np.frombuffer(data[512:516], dtype=np.uint32)[0]
		self._versionInfo.fileformatversion = unpack('4B', data[516:520])
		self._versionInfo.apiversion = unpack('4B', data[520:524])
		self._versionInfo.fx3version = unpack('4B', data[524:528])
		self._versionInfo.fpgaversion = unpack('4B', data[528:532])
		self._versionInfo.devicesn = "".join(map(chr, data[532:596]))
		
		# Get the Instrument State section of the header
		self._instrumentState.referencelevel = unpack('1d', data[1024:1032])[0]
		self._instrumentState.centerfrequency = unpack('1d', data[1032:1040])[0]
		self._instrumentState.temperature = unpack('1d', data[1040:1048])[0]
		self._instrumentState.alignment = unpack('1I', data[1048:1052])[0]
		self._instrumentState.freqreference = unpack('1I', data[1052:1056])[0]
		self._instrumentState.trigmode = unpack('1I', data[1056:1060])[0]
		self._instrumentState.trigsource = unpack('1I', data[1060:1064])[0]
		self._instrumentState.trigtrans = unpack('1I', data[1064:1068])[0]
		self._instrumentState.triglevel = unpack('1d', data[1068:1076])[0]

		# Get Data Format section of the header
		#self.dformat.datatype = unpack('1I', data[2048:2052])
		self._dataFormat.datatype = np.frombuffer(data[2048:2052], dtype=np.uint32)[0]
		if self._dataFormat.datatype == 161:
			self._dataFormat.datatype = 2 #bytes per sample
		self._dataFormat.frameoffset = np.frombuffer(data[2052:2056], dtype=np.uint32)[0]
		self._dataFormat.framesize = np.frombuffer(data[2056:2060], dtype=np.uint32)[0]
		self._dataFormat.sampleoffset = unpack('1I', data[2060:2064])[0]
		self._dataFormat.samplesize = np.frombuffer(data[2064:2068], dtype=np.int32)[0]
		self._dataFormat.nonsampleoffset = np.frombuffer(data[2068:2072], dtype=np.uint32)[0]
		self._dataFormat.nonsamplesize = np.frombuffer(data[2072:2076], dtype=np.uint32)[0]
		self._dataFormat.ifcenterfrequency = np.frombuffer(data[2076:2084], dtype=np.double)[0]
		#self.dformat.samplerate = unpack('1d', data[2084:2092])
		self._dataFormat.samplerate = np.frombuffer(data[2084:2092], dtype=np.double)[0]
		self._dataFormat.bandwidth = unpack('1d', data[2092:2100])[0]
		self._dataFormat.corrected = unpack('1I', data[2100:2104])[0]
		self._dataFormat.timetype = unpack('1I', data[2104:2108])[0]
		self._dataFormat.reftime = list(unpack('7i', data[2108:2136]))
		self._dataFormat.clocksamples = unpack('1Q', data[2136:2144])[0]
		self._dataFormat.timesamplerate = np.frombuffer(data[2144:2152], dtype=np.uint64)[0]

		# Get Signal Path and Channel Correction data
		self._channelCorrection.adcscale = np.frombuffer(data[3072:3080], dtype=np.double)[0]
		self._channelCorrection.pathdelay = np.frombuffer(data[3080:3088], dtype=np.double)[0]
		self._channelCorrection.correctiontype = np.frombuffer(data[4096:4100], dtype=np.uint32)[0]
		tableentries = np.frombuffer(data[4352:4356], dtype=np.uint32)[0]
		
		#purely for use in IQ_correction()
		self._channelCorrection.tableentries = tableentries
		freqindex = 4356
		phaseindex = freqindex + 501*4
		ampindex = phaseindex + 501*4
		self._channelCorrection.freqtable = np.frombuffer(data[freqindex:(freqindex+501*4)], dtype=np.float32)
		self._channelCorrection.phasetable = np.frombuffer(data[phaseindex:ampindex], dtype=np.float32)
	
		self._channelCorrection.amptable = np.frombuffer(data[ampindex:(ampindex+tableentries*4)], dtype=np.float32)
		self._headerFile.close()

	def _ddc(self) -> None:
		#Generate quadrature signals
		IFfreq = self._dataFormat.ifcenterfrequency
		size = len(self._ADC)
		sampleperiod = 1.0/self._dataFormat.timesamplerate
		xaxis = np.linspace(0, size * sampleperiod, size)
		LO_I = np.sin(IFfreq*(2*np.pi)*xaxis)
		LO_Q = np.cos(IFfreq*(2*np.pi)*xaxis)
		del(xaxis)

		#Run ADC data through digital downconverter
		I = self._ADC * LO_I
		Q = self._ADC * LO_Q

		del(LO_I)
		del(LO_Q)
		nyquist = self._dataFormat.timesamplerate/2

		cutoff = 40e6/nyquist
		IQfilter = signal.firwin(32, cutoff, window=('kaiser', 2.23))
		I = signal.lfilter(IQfilter, 1.0, I)
		Q = signal.lfilter(IQfilter, 1.0, Q)
		IQ = I + 1j * Q
		IQ = 2 * IQ

		self._IQ = IQ
