from RSA306 import reader
import matplotlib.pyplot  as plt

def plot_graphs(rsafile : reader.RSAReader):
		# This function plots the amplitude and phase correction 
		# tables as a function of IF frequency
		plt.subplot(2,1,1)
		plt.plot(rsafile.channelCorrection.freqtable/1e6,rsafile.channelCorrection.amptable)
		plt.title('Amplitude and Phase Correction')
		plt.ylabel('Amplitude (dB)')
		plt.subplot(2,1,2)
		plt.plot(rsafile.channelCorrection.freqtable/1e6,rsafile.channelCorrection.phasetable)
		plt.ylabel('Phase (degrees)')
		plt.xlabel('IF Frequency (MHz)')
		plt.show()
		plt.clf()

r3f = "./data/DATA1-2020.01.16.11.51.03.655.r3f"
r3a = "./data/DATA2-2020.01.16.12.06.56.091.r3a"

rsafile : reader.RSAReader = reader.open(r3f)

rsafile.read()

print(rsafile.ADC)

# plot_graphs(rsafile)