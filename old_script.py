#!/usr/bin/python3

"""
Script: RSA300 Streamed Data File Parser
Date: 12/2015
Author: Morgan Allison
Software: Anaconda 2.1.0 (Python 2.7.8, 64-bit) http://continuum.io/downloads
Description: This script reads in a .r3f/.r3a/.r3h file created by the RSA306,
parses out all the metadata, saves the raw data, converts to IQ data, and
exports a .mat file that is readable by SignalVu-PC and a .txt file
containing footer data
Directions: 
1. Save a streamed data file from your RSA300
2. Put it in C:\SignalVu-PC Files\
3. Run the script, enter the name of your source file
4. Choose display features
5. Choose to save or discard IQ data
6. Choose to save or discard footer (iff .r3f file)
"""

from struct import *
import numpy as np
from scipy import signal
import scipy.io as sio
import matplotlib.pyplot as plt
import os, time, math
from argparse import ArgumentParser
from os.path import abspath

class R3F:
	def __init__(self, infile, corr_table = False, head_data = False, footer_data = False, iq_data = False, outfile = ""):
		# base_directory = 'C:\\Users\\alkir\\OneDrive\\Рабочий стол\\VKR\\data\\'
		# fname = input(
		# 	'Enter input file name including extension (.r3f/.r3a/.r3h).\n> ')
		self.infilename = infile
		self.outfile = outfile

		# md_instructions = ("0=display nothing\n1=display header data" +
		# "\n2=plot correction tables\n3=display 1 and 2\n> ")
		self.disp_flag = '0'
		
		if head_data and corr_table:
			self.disp_flag = '3'
		elif head_data:
			self.disp_flag = '1' 
		elif corr_table:
			self.disp_flag = '2'
		
		self.iq_flag = '1' if iq_data else '0' 

		if '.r3h' in self.infilename or '.r3a' in self.infilename:
			print('\nBecause a .r3f file was not chosen, ' +
				'footer data cannot be extracted.\n')
			self.footer_flag = '0'
		else:
			self.footer_flag = '1' if footer_data else '0'

		self.ADC = []
		self.IQ = []
		self.footer = []
		self.vinfo = VersionInfo()
		self.inststate = InstrumentState()
		self.dformat = DataFormat()
		self.chcorr = ChannelCorrection()

	def convert(self):
		# Main conversion function
		# The order of these calls is important because display_control() 
		# and file_muncher() are dependent on data from file_manager()
		self.file_manager()
		self.display_control()
		self.file_muncher()

	def display_control(self):
		# Depending on the status of 'disp_flag,' print header data, 
		# display correction plots, do both, or do neither
		if self.disp_flag == '3':
			self.print_header_data()
			print('Header printed and channel correction graphs plotted.\n')
			self.plot_graphs()
		elif self.disp_flag == '2':
			print('Channel correction graphs plotted.\n')
			self.plot_graphs()
		elif self.disp_flag == '1':
			self.print_header_data()
			print('Header printed.\n')
		elif self.disp_flag== '0':
			print('Header parsed.')
		else: 
			print('Invalid choice. Select 0, 1, 2, or 3.')
			quit()

	def get_header_data(self):
		# Parses the header section of *.r3f and *.r3h files.
		# Certain fields use np.frombuffer() rather than unpack() because
		# np.frombuffer() allows the user to specify data type.
		# unpack() saves data as a tuple, which can be used for printing
		# but not calculations
		data = self.headerfile.read(16384)

		# Get File ID and Version Info sections of the header
		self.vinfo.fileid = data[:27]
		self.vinfo.endian = np.frombuffer(
			data[512:516], dtype=np.uint32)
		self.vinfo.fileformatversion = unpack('4B', data[516:520])
		self.vinfo.apiversion = unpack('4B', data[520:524])
		self.vinfo.fx3version = unpack('4B', data[524:528])
		self.vinfo.fpgaversion = unpack('4B', data[528:532])
		self.vinfo.devicesn = data[532:596]
		
		# Get the Instrument State section of the header
		self.inststate.referencelevel = unpack('1d', data[1024:1032])
		self.inststate.centerfrequency = unpack('1d', data[1032:1040])
		self.inststate.temperature = unpack('1d', data[1040:1048])
		self.inststate.alignment = unpack('1I', data[1048:1052])
		self.inststate.freqreference = unpack('1I', data[1052:1056])
		self.inststate.trigmode = unpack('1I', data[1056:1060])
		self.inststate.trigsource = unpack('1I', data[1060:1064])
		self.inststate.trigtrans = unpack('1I', data[1064:1068])
		self.inststate.triglevel = unpack('1d', data[1068:1076])

		# Get Data Format section of the header
		#self.dformat.datatype = unpack('1I', data[2048:2052])
		self.dformat.datatype = np.frombuffer(
			data[2048:2052], dtype=np.uint32)[0]
		if self.dformat.datatype == 161:
			self.dformat.datatype = 2 #bytes per sample
		self.dformat.frameoffset = np.frombuffer(
			data[2052:2056], dtype=np.uint32)[0]
		self.dformat.framesize = np.frombuffer(
			data[2056:2060], dtype=np.uint32)[0]
		self.dformat.sampleoffset = unpack('1I', data[2060:2064])
		self.dformat.samplesize = np.frombuffer(
			data[2064:2068], dtype=np.int32)[0]
		self.dformat.nonsampleoffset = np.frombuffer(
			data[2068:2072], dtype=np.uint32)[0]
		self.dformat.nonsamplesize = np.frombuffer(
			data[2072:2076], dtype=np.uint32)[0]
		self.dformat.ifcenterfrequency = np.frombuffer(
			data[2076:2084], dtype=np.double)[0]
		#self.dformat.samplerate = unpack('1d', data[2084:2092])
		self.dformat.samplerate = np.frombuffer(
			data[2084:2092], dtype=np.double)[0]
		self.dformat.bandwidth = unpack('1d', data[2092:2100])
		self.dformat.corrected = unpack('1I', data[2100:2104])
		self.dformat.timetype = unpack('1I', data[2104:2108])
		self.dformat.reftime = unpack('7i', data[2108:2136])
		self.dformat.clocksamples = unpack('1Q', data[2136:2144])
		self.dformat.timesamplerate = np.frombuffer(
			data[2144:2152], dtype=np.uint64)[0]

		# Get Signal Path and Channel Correction data
		self.chcorr.adcscale = np.frombuffer(
			data[3072:3080], dtype=np.double)[0]
		self.chcorr.pathdelay = np.frombuffer(
			data[3080:3088], dtype=np.double)[0]
		self.chcorr.correctiontype = np.frombuffer(
			data[4096:4100], dtype=np.uint32)[0]
		tableentries = np.frombuffer(data[4352:4356], dtype=np.uint32)
		self.chcorr.tableentries = tableentries	#purely for use in IQ_correction()
		freqindex = 4356
		phaseindex = freqindex + 501*4
		ampindex = phaseindex + 501*4
		self.chcorr.freqtable = np.frombuffer(
			data[freqindex:(freqindex+501*4)], dtype=np.float32)
		self.chcorr.phasetable = np.frombuffer(
			data[phaseindex:ampindex], dtype=np.float32)
	
		# TODO was error
		self.chcorr.amptable = np.frombuffer(
			data[ampindex:(ampindex+tableentries*4)[0]], dtype=np.float32)
		self.headerfile.close()
		
	def print_header_data(self):
		# This function simply prints out all the header data
		print('FILE INFO')
		print('FileID: {}'.format(str(self.vinfo.fileid)))
		print('Endian Check: 0x{}'.format(self.vinfo.endian))
		print('File Format Version: {}.{}.{}.{}'.format(*self.vinfo.fileformatversion))
		print('API Version: {}.{}.{}.{}'.format(*self.vinfo.apiversion))
		print('FX3 Version: {}.{}.{}.{}'.format(*self.vinfo.fx3version))
		print('FPGA Version: {}.{}.{}.{}'.format(*self.vinfo.fpgaversion))
		print('Device Serial Number: {}'.format(str(self.vinfo.devicesn)))

		print('INSTRUMENT STATE')
		print('Reference Level: {} dBm'.format(self.inststate.referencelevel))
		print('Center Frequency: {} Hz'.format(self.inststate.centerfrequency))
		print('Temperature: {} C'.format(self.inststate.temperature))
		print('Alignment status: {}'.format(self.inststate.alignment))
		print('Frequency Reference: {}'.format(self.inststate.freqreference))
		print('Trigger mode: {}'.format(self.inststate.trigmode))
		print('Trigger Source: {}'.format(self.inststate.trigsource))
		print('Trigger Transition: {}'.format(self.inststate.trigtrans))
		print('Trigger Level: {} dBm\n'.format(self.inststate.triglevel))

		print('DATA FORMAT')
		print('Data Type: {} bytes per sample'.format(self.dformat.datatype))
		print('Offset to first frame (bytes): {}'.format(self.dformat.frameoffset))
		print('Frame Size (bytes): {}'.format(self.dformat.framesize))
		print('Offset to sample data (bytes): {}'.format(self.dformat.sampleoffset))
		print('Samples in Frame: {}'.format(self.dformat.samplesize))
		print('Offset to non-sample data: {}'.format(self.dformat.nonsampleoffset))
		print('Size of non-sample data: {}'.format(self.dformat.nonsamplesize))
		print('IF Center Frequency: {} Hz'.format(self.dformat.ifcenterfrequency))
		print('Sample Rate: {:.0f} S/sec'.format(self.dformat.samplerate))
		print('Bandwidth: {} Hz'.format(self.dformat.bandwidth))
		print('Corrected data status: {}'.format(self.dformat.corrected))
		print('Time Type (0=local, 1=remote): {}'.format(self.dformat.timetype))
		print('Reference Time: {} {}/{} at {}:{}:{}:{}'.format(*self.dformat.reftime))
		print('Clock sample count: {}'.format(self.dformat.clocksamples))
		print('Sample ticks per second: {}\n'.format(self.dformat.timesamplerate))

		print('CHANNEL AND SIGNAL PATH CORRECTION')
		print('ADC Scale Factor: {:-f}'.format(self.chcorr.adcscale))
		print('Signal Path Delay: {} nsec'.format(float(self.chcorr.pathdelay*1e9)))
		print('Correction Type (0=LF, 1=IF): {}\n'.format(self.chcorr.correctiontype))


	def plot_graphs(self):
		# This function plots the amplitude and phase correction 
		# tables as a function of IF frequency
		plt.subplot(2,1,1)
		plt.plot(self.chcorr.freqtable/1e6,self.chcorr.amptable)
		plt.title('Amplitude and Phase Correction')
		plt.ylabel('Amplitude (dB)')
		plt.subplot(2,1,2)
		plt.plot(self.chcorr.freqtable/1e6,self.chcorr.phasetable)
		plt.ylabel('Phase (degrees)')
		plt.xlabel('IF Frequency (MHz)')
		plt.show()
		plt.clf()


	def file_manager(self):
		# Creates header and data files out of user's chosen file for use in
		# other functions, calculates file size in bytes and length in
		# seconds, and calls get_header_data()
		if '.r3f' in self.infilename:
			try:
				self.headerfile = open(self.infilename, 'rb')
				self.datafile = open(self.infilename, 'rb')
			except IOError:
				print('\nCannot open file. Check the input file name and try again.\n')
				quit()
			self.get_header_data()
			self.filesize = os.path.getsize(self.datafile.name)
			self.numframes = int((self.filesize/self.dformat.framesize) - 1)
			#because it needs to be unsigned to check looping in file_muncher correctly
			self.filelength = self.numframes*(self.dformat.samplesize/self.dformat.samplerate)
			print('Number of Frames: {}\n'.format(self.numframes))
			print('File size is: {} bytes.'.format(self.filesize))
			print('File length is: {} seconds.\n'.format(self.filelength))

		elif '.r3a' in self.infilename or '.r3h' in self.infilename:
			try:	
				self.headerfile = open((self.infilename[:-1] + 'h'), 'rb')
				self.datafile = open((self.infilename[:-1] + 'a'), 'rb')
			except IOError:
				print('\nCannot open file. Check the input file name and try again.\n')
				quit()
			self.get_header_data()
			self.filesize = int(os.path.getsize(self.datafile.name))
			self.filelength = self.filesize/self.dformat.datatype/self.dformat.samplerate
			print('File size is: {} bytes.\nFile Length is {} seconds.\n'.format(
				self.filesize, self.filelength))
		else:
			print('Compatible file extension not found, check input file and try again.')
			quit()

	def file_muncher(self):
		# Determines if the file is > 1 second long and splits accordingly
		# and calls get_adc_samples(), ddc(), and file_saver(),
		# which are really the core processing components of this script
		print('Beginning file conversion.\n')
		loop = 0
		# formatted processing loop based on number of frames in data file
		if '.r3f' in self.datafile.name:
			fps = 13698
			while self.numframes > 0:
				if self.numframes > fps:
					print('File is longer than 1 second, splitting into {} files.'
						.format(int(math.ceil(self.filelength))))
					process_data = fps
				else:
					process_data = self.numframes
				if loop == 0:
					startpoint = self.dformat.frameoffset
				elif loop > 0:
					startpoint = loop*fps*self.dformat.framesize
				self.get_adc_samples(process_data, startpoint)
				self.ddc()
				self.file_saver(loop, process_data)
				self.numframes -= fps
				loop += 1
		# raw processing loop based on file size in bytes
		elif '.r3a' in self.datafile.name:
			bytes_per_second = 224000000
			while self.filesize > 0:
				if self.filesize > bytes_per_second:
					process_data = bytes_per_second/2 #two bytes per sample
				else:
					process_data = self.filesize
				if loop == 0:
					startpoint = 0
				elif loop > 0:
					startpoint = loop*bytes_per_second
				self.get_adc_samples(process_data, startpoint)
				self.ddc()
				self.file_saver(loop, process_data)
				self.filesize -= bytes_per_second
				loop += 1
		self.datafile.close()

	def get_adc_samples(self, process_data, startpoint):
		# Reads ADC samples from input file 
		# Skips over or saves footer for .r3f files
		# Reads in everything for .r3a files

		#Filter file type and read the file appropriately
		if '.r3f' in self.datafile.name:
			#TODO was error - array input
			self.datafile.seek(startpoint)
			adcsamples = np.empty(process_data*self.dformat.samplesize)
			fstart = 0
			fstop = self.dformat.samplesize
			self.footer = list(range(process_data))
			for i in range(process_data):
				#TODO was error - array input
				frame = self.datafile.read(self.dformat.nonsampleoffset)
				adcsamples[fstart:fstop] = np.frombuffer(frame, 
					dtype=np.int16)
				fstart = fstop
				fstop = fstop + self.dformat.samplesize
				if self.footer_flag == '0':
					self.datafile.seek(self.dformat.nonsamplesize,1)
				else:
					temp_ftr = self.datafile.read(self.dformat.nonsamplesize)
					self.footer[i] = FooterClass()
					self.footer[i] = self.parse_footer(temp_ftr)
		elif '.r3a' in self.datafile.name:
			self.datafile.seek(startpoint)
			adcsamples = np.empty(process_data)
			adcsamples = np.fromfile(self.datafile, dtype=np.int16, 
				count=process_data)
		else:
			print('Invalid file type. Please specify a .r3f, r3a, or .r3h file.\n')
			quit()

		#Scale ADC data
		self.ADC = adcsamples*self.chcorr.adcscale

	def parse_footer(self, raw_footer):
		# Parses footer based on internal footer documentation
		footer = FooterClass()
		footer.reserved = np.frombuffer(raw_footer[0:6], 
			dtype=np.uint16, count=3)
		footer.frame_id = np.frombuffer(raw_footer[8:12],
		 dtype=np.uint32, count=1)
		footer.trigger2_idx = np.frombuffer(raw_footer[12:14],
		 dtype=np.uint16, count=1)
		footer.trigger1_idx = np.frombuffer(raw_footer[14:16],
		 dtype=np.uint16, count=1)
		footer.time_sync_idx = np.frombuffer(raw_footer[16:18],
		 dtype=np.uint16, count=1)
		footer.frame_status = '{0:8b}'.format(
			int(np.frombuffer(raw_footer[18:20], dtype=np.uint16, count=1)))
		footer.timestamp = np.frombuffer(raw_footer[20:28], 
			dtype=np.uint64, count=1)
		
		return footer

	def ddc(self):
		# Digital downconverter that converts ADC data to IQ data
		if self.iq_flag =='1':

			#Generate quadrature signals
			IFfreq = self.dformat.ifcenterfrequency
			size = len(self.ADC)
			sampleperiod = 1.0/self.dformat.timesamplerate
			xaxis = np.linspace(0,size*sampleperiod,size)
			LO_I = np.sin(IFfreq*(2*np.pi)*xaxis)
			LO_Q = np.cos(IFfreq*(2*np.pi)*xaxis)
			del(xaxis)

			#Run ADC data through digital downconverter
			I = self.ADC*LO_I
			Q = self.ADC*LO_Q

			del(LO_I)
			del(LO_Q)
			nyquist = self.dformat.timesamplerate/2

			cutoff = 40e6/nyquist
			IQfilter = signal.firwin(32, cutoff, window=('kaiser', 2.23))
			I = signal.lfilter(IQfilter, 1.0, I)
			Q = signal.lfilter(IQfilter, 1.0, Q)
			IQ = I + 1j*Q
			IQ = 2*IQ

			self.IQ = IQ

	def file_saver(self, loop, process_data):
		# Saves a .mat file containing variables specified in the 
		# SignalVu-PC help file
		# Also saves a footer data in a .txt file
		if self.iq_flag == '1':
			InputCenter = self.inststate.centerfrequency
			XDelta = 1.0/self.dformat.timesamplerate
			Y = self.IQ
			InputZoom = np.uint8(1)
			Span = self.dformat.bandwidth
			filename = self.outfile + '_' + str(loop) + ".mat"
			sio.savemat(filename, {'InputCenter':InputCenter,'Span':Span, 
				'XDelta':XDelta,'Y':Y,'InputZoom':InputZoom}, format='5')
			print('Data file saved at {}.mat'.format(filename))

		if self.footer_flag == '1':
			fname = self.outfile + '_' + str(loop) + '.txt'
			ffile = open(fname, 'w')
			ffile.write('FrameID\tTrig1\tTrig2\tTSync\tFrmStatus\tTimeStamp\n')
			for i in range(process_data):
				ffile.write(', '.join(map(str, self.footer[i].frame_id)))
				ffile.write('\t')
				ffile.write(', '.join(map(str, self.footer[i].trigger2_idx)))
				ffile.write('\t')
				ffile.write(', '.join(map(str, self.footer[i].trigger1_idx)))
				ffile.write('\t')
				ffile.write(', '.join(map(str, self.footer[i].time_sync_idx)))
				ffile.write('\t')
				ffile.write(self.footer[i].frame_status)
				ffile.write('\t')
				ffile.write(', '.join(map(str, self.footer[i].timestamp)))
				ffile.write('\n')
			ffile.close()
			print('Footer file saved at {}.'.format(fname))

def main():
	parser = ArgumentParser()

	parser.add_argument("--if", dest="infile", help="input file", required=True)
	parser.add_argument("--of", dest="outfile", help="output file (default [inputFile].mat")
	parser.add_argument("--header", dest="header_data", help="display header data", action="store_true")
	parser.add_argument("--correction", dest="correction_table", help="display correction tables", action="store_true")
	parser.add_argument("--iq", dest="iq_data", help="save IQ data to mat file", action="store_true")
	parser.add_argument("--footer", dest="footer_data", help="save footer data", action="store_true")
	parser.set_defaults(feature=True)

	args = parser.parse_args()

	if (args.iq_data or args.footer_data) and not args.outfile: 
		print("Enter output filename for IQ data")
		parser.print_help()
		exit()

	infile = abspath(args.infile)

	outfile = ""

	if args.outfile:
		outfile = abspath(args.outfile)

	r3f = R3F(infile=infile, \
		head_data=args.header_data, \
		corr_table=args.correction_table, \
		footer_data=args.footer_data, \
		iq_data=args.iq_data, \
		outfile=outfile)

	r3f.convert()

if __name__ == '__main__':
	main()