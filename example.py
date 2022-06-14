import matplotlib.pyplot as plt
import numpy as np
from scipy.signal import get_window
from scipy.interpolate import CubicSpline
import math

from RSA306.reader import get_reader

fm_r3f_path = 'data/FM-2022.06.07.14.40.46.902.r3f'

rsa_reader = get_reader(fm_r3f_path)

print(f'\n==============\nrsa_file info:\n==============\n{rsa_reader}\n')

Fs = rsa_reader.data_format.sample_rate
f1 = rsa_reader.data_format.if_center_frequency
f0 = rsa_reader.instrument_state.center_frequency
delta_f = rsa_reader.data_format.bandwidth
N = rsa_reader.data_format.clock_samples
amp_corrector = CubicSpline(rsa_reader.channel_correction.freq_table,
                            rsa_reader.channel_correction.amp_table)

block_size = 2**16
block_size = math.ceil(2**16/8178) * 8178
S_abs = np.zeros(block_size//2+1, dtype=np.float64)
w = get_window('hann', block_size)

Nblocks = 0
for i, block_samples in enumerate(rsa_reader.readblock(block_size, False, True)):
    duration_done = (i + 1) * block_size / Fs

    if duration_done > 5:
        break

    print(f'\r{i} ({duration_done:.3f} s)', end='', flush=True)
    S_i = np.fft.rfft(np.concatenate(list(map(lambda data: data[0], block_samples))) * w)  # для данных с заголовками
    # S_i = np.fft.rfft(block_samples * w)  # для данных без заголовков
    S_abs += np.abs(S_i)
    Nblocks += 1

f = np.fft.rfftfreq(block_size, d=1/Fs)
mask = (f1-delta_f/2 < f) & (f < f1+delta_f/2)

S_abs *= rsa_reader.channel_correction.adc_scale
S_abs /= Nblocks * Fs
S_dB = 20 * np.log10(S_abs) - amp_corrector(f)

plt.plot((f[mask] - f1 + f0) * 1e-6, S_dB[mask])
plt.grid()
plt.xlabel('f, МГц')
plt.ylabel('|S(f)|, dB')
plt.show()