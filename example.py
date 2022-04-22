from RSA306.reader import get_reader, BaseReader
import matplotlib.pyplot as plt


def plot_graphs(reader: BaseReader):
	# This function plots the amplitude and phase correction
	# tables as a function of IF frequency
	plt.subplot(2, 1, 1)
	plt.plot(reader.channel_correction.freq_table / 1e6, reader.channel_correction.amp_table)
	plt.title('Amplitude and Phase Correction')
	plt.ylabel('Amplitude (dB)')
	plt.subplot(2, 1, 2)
	plt.plot(reader.channel_correction.freq_table / 1e6, reader.channel_correction.phase_table)
	plt.ylabel('Phase (degrees)')
	plt.xlabel('IF Frequency (MHz)')
	plt.show()
	plt.clf()


r3f = "./data/DATA1-2020.01.16.11.51.03.655.r3f"
r3a = "./data/DATA2-2020.01.16.12.06.56.091.r3a"

rsa_file = get_reader(r3f)

print(rsa_file.read())

# plot_graphs(reader)
