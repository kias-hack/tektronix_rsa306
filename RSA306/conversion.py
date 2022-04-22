from scipy import signal
import numpy as np


def ddc(adc: np.array, if_center_frequency: float, time_sample_rate: float) -> None:
    """ Генерирует квадратурный сигнал, пропуская через фильтр нижних частот
    и на выходе генерируя iq отсчеты в комплексной форме

    Аргументы:
    ----------
    adc: np.array
        входной оцифрованный сигнал
    
    if_center_frequency: float
        ...
    
    time_sample_rate: float
        период измерений входного сигнала

    Возвращаемые значения:
    -------------------
    iq: np.array
        iq отсчеты в комплексной форме

    """
    size = len(adc)
    sample_period = 1.0 / time_sample_rate
    x_axis = np.linspace(0, size * sample_period, size)
    lo_i = np.sin(if_center_frequency * (2 * np.pi) * x_axis)
    lo_q = np.cos(if_center_frequency * (2 * np.pi) * x_axis)
    del x_axis

    i = adc * lo_i
    q = adc * lo_q

    del lo_i
    del lo_q
    nyquist = time_sample_rate / 2

    cutoff = 40e6 / nyquist
    iq_filter = signal.firwin(32, cutoff, window=('kaiser', 2.23))
    i = signal.lfilter(iq_filter, 1.0, i)
    q = signal.lfilter(iq_filter, 1.0, q)
    iq = i + 1j * q
    iq = 2 * iq

    return iq
