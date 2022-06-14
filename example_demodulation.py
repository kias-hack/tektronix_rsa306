from fractions import Fraction
from math import ceil

import matplotlib.pyplot as plt
import numpy as np
from scipy.signal import get_window
from scipy.interpolate import CubicSpline
from scipy.io.wavfile import write

from RSA306.reader import get_reader, BaseReader
from RSA306.conversion import fir_coefs, PPResample, PassbandToBaseband_IH, FM_Demodulate


fm_r3f_path = 'data/FM-2022.06.07.14.40.46.902.r3f'

rsa_reader = get_reader(fm_r3f_path)

print(f'\n==============\nrsa_file info:\n==============\n{rsa_reader}\n')

f_station = 101.9e6

Fs1 = rsa_reader.data_format.sample_rate
Fs2 = 224e3
Fs3 = 32e3

r1 = Fraction(Fs2) / Fraction(Fs1)
r2 = Fraction(Fs3) / Fraction(Fs2)

f_dev = 75e3

fpass1 = 75e3
fstop1 = 100e3
b1 = fir_coefs(fpass1, fstop1, 60, Fs=Fs1)

fpass2 = 15e3
fstop2 = 16e3
b2 = fir_coefs(fpass2, fstop2, 60, Fs=Fs2)

f1 = rsa_reader.data_format.if_center_frequency
f0 = rsa_reader.instrument_state.center_frequency

block_size_1 = int(1.05e6)
block_size_2 = ceil(r1 * block_size_1)
block_size_3 = ceil(r2 * block_size_2)

resampler1 = PPResample(r1, b1, block_size_1, block_size_2, dtype=np.complex64)

bconv = PassbandToBaseband_IH(block_size_1, Fs1, f1-f0+f_station, np.float32, decimator=resampler1)

demod = FM_Demodulate(block_size_2, Fs2, f_dev, np.float32)

resampler2 = PPResample(r2, b2, block_size_2, block_size_3, dtype=np.float32)

print(f'{Fs1}')
print(f'{Fs2}')
print(f'{Fs3}')
print(f'{len(b1)}')
print(f'{len(b2)}')
print(f'{r1}')
print(f'{r2}')
print(f'{block_size_1}')
print(f'{block_size_2}')
print(f'{block_size_3}')

out_lst = []

Nblocks = 0
for i, block_samples in enumerate(rsa_reader.readblock(block_size_1, False)):
    duration_done = (i + 1) * block_size_1 / Fs1

    if duration_done > 25:
        break

    print(f'\r{i} ({duration_done:.3f} s)', end='', flush=True)
    block_IQ = bconv(block_samples)
    block_demod = demod(block_IQ)
    block_out = resampler2(block_demod)
    out_lst.append(block_out.copy())

s_out = np.concatenate(out_lst)
s_out /= np.max(np.abs(s_out))
s_out *= 2**15-1

write(f'dist/{f_station/1e6:.1f} FM.wav', int(Fs3), s_out.astype(np.int16))


