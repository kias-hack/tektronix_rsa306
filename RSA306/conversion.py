from scipy import signal
from scipy.signal import kaiserord, firwin, firwin2
import numpy as np
from numpy import pi, exp, angle, unwrap, diff


class FM_Demodulate(object):
    """ Демодуляция комплексной огибающей ЧМ-сигнала. """

    __slots__ = 'chunk_size', 'Fs', 'f_dev', 'Katt', 'buf', 'y'

    def __init__(self, chunk_size, Fs, f_dev, dtype_out, Katt=1.0):
        self.chunk_size = chunk_size
        self.Fs = Fs
        self.f_dev = f_dev
        self.Katt = Katt
        self.buf = np.zeros(self.chunk_size+1, dtype=dtype_out)
        self.y = np.zeros(self.chunk_size, dtype=dtype_out)

    def __call__(self, x_in):
        self.buf[1:] = angle(x_in)
        last_phase = self.buf[-1]
        self.buf[:] = unwrap(self.buf)
        self.y[:] = diff(self.buf)
        self.buf[0] = last_phase
        self.y *= self.Katt * self.Fs / (2 * pi * self.f_dev)
        return self.y


class PassbandToBaseband_IH(object):
    """ ВКО -- выделитель комплексной огибающей (с внутренним гетеродином).

    IH -- Internal Heterodyne

    Выделяет комплексную огибающую радиосигнала по алгоритму:
    1) спектр сигнал смещается на нулевую частоту путем умножения на
       комплексную экспоненту (формируемую внутренним некогерентным
       гетеродином)
    2) при помощи ФНЧ подавляются мешающие ВЧ-составляющие (возможно совмещение
       фильтрации с прореживанием)

    Примечания:
    -----------
    1. Преобразователь работает от внутреннего гетеродина, не
       синхронизированного со входным колебанием. По этой причине комплексная
       огибающая выделяется с точностью до постоянной начальной фазы и
       расстройки по частоте (если задана fh, не равная несущей частоте
       сигнала).

    """

    def __init__(self, chunk_size, Fs, fh, dtype, phi0=0,
                 lowpass=None, decimator=None):
        """ Конструктор выделителя комплексной огибающей.

        Аргументы:
        ----------
        chunk_size: int
            размер отрезка входного сигнала
        Fs: float
            частота дискретизации входного сигнала, Гц
        fh: float
            частота гетеродина, Гц
        dtype: str
            тип данных входного сигнала
        phi0: float
            начальная фаза колебания гетеродина, рад
        lowpass: lib.dsp.lfilters.IIRFilterChunkwise |
                 lib.dsp.lfilters.FIRFilterChunkwise
            фильтр нижних частот для подавления ВЧ-компонент сигнала после
            сдвига спектра
        decimator: lib.dsp.resampling.polyphase.PPResample
            преобразователь частоты дискретизации на основе полифазного фильтра

        Примечания:
        -----------
        1. Если задан аргумент lowpass, то частота дискретизации и размер
        отрезка выходного сигнала совпадают с частотой дискретизации и размером
        отрезка входного сигнала.

        2. Если задан аргумент decimator, то частота дискретизации и размер
        отрезка выходного сигнала определяются настройками преобразователя
        частоты дискретизации.

        3. Должен быть передан ровно один из аргументов lowpass, decimator.
        Если переданы два или ни одного, вызывается исключение TypeError.

        """

        if lowpass is None and decimator is None:
            msg = 'Не задан ни ФНЧ, ни дециматор'
            raise TypeError(msg)
        elif lowpass is not None and decimator is not None:
            msg = 'Задан и ФНЧ, и дециматор'
            raise TypeError(msg)
        elif lowpass is None:
            self.postproc = decimator
        elif decimator is None:
            self.postproc = lowpass

        self.chunk_size = chunk_size
        self.Fs = Fs
        self.fh = fh
        self.phi0 = phi0
        self.omega_h = 2 * pi * self.fh
        self.phase_shift = 0

        if np.dtype(dtype).kind == 'c':
            compdtype = dtype
        elif np.dtype(dtype).itemsize <= 4:
            compdtype = 'complex64'
        elif np.dtype(dtype).itemsize == 8:
            compdtype = 'complex128'
        else:
            compdtype = 'complex256'

        nT = np.arange(chunk_size, dtype=compdtype) / Fs
        self.x_h = exp(1j * self.omega_h * nT + phi0)
        self.x_mix = np.zeros(chunk_size, dtype=compdtype)
        self.y = self.postproc.y

    def __call__(self, x_in):
        """ Обработка отрезка сигнала """
        self.x_mix[:] = x_in * self.x_h * exp(1j*self.phase_shift)
        self.phase_shift += self.omega_h * self.chunk_size / self.Fs
        self.phase_shift %= 2 * pi
        self.postproc(self.x_mix)
        return self.y


class PPResample(object):
    """ Преобразователь частоты дискретизации на основе полифазного фильтра.

    Fд2 = p*Fд1/q

    Для фильтрации применяется банк из q полифазных фильтров.
    Отсчеты подаются на вход одного из фильтров банка через ключ, который
    перемещается против часовой стрелки на p % q положений за каждый такт Fд1.

    Реализован по схеме, эффективной при p << q.

    Каждый такт Fд2 срабатывают все фильтры, результаты складываются для
    получения отсчета выходного сигнала.

    """

    __slots__ = ('r', 'p', 'q', 'chunk_size_in', 'chunk_size_out', 'b',
                 'bpartial', 'L', 'Lpartial', 'buffers', 'y', 'm_in')

    def __init__(self, r, b, chunk_size_in, chunk_size_out, dtype=float):
        """ Инициализация преобразователя частоты дискретизации

        Аргументы:
        ----------
        r: fractions.Fraction
            рациональный коэффициент преобразования частоты дискретизации;
            r = Fs2 / Fs1
        b: 1-D numpy.array
            импульсная характеристика ФНЧ
        chunk_size_in: int
            размер отрезка входного сигнала
        chunk_size_out: int
            размер отрезка выходного сигнала
        dtype: str | numpy.dtype, необязательный
            тип данных, обрабатываемых преобразователем

        """
        _checkchunk_size_out(chunk_size_in, chunk_size_out, r)
        p, q = r.numerator, r.denominator
        self.r, self.p, self.q = r, p, q
        self.chunk_size_in, self.chunk_size_out = chunk_size_in, chunk_size_out
        self.b = b
        self.L = b.size

        Nphases = q  # число фаз
        # Длина фильтра для каждой фазы:
        self.Lpartial = int(np.ceil(self.L / q))
        self.buffers = np.zeros((Nphases, self.Lpartial), dtype=dtype)
        self.bpartial = np.zeros((Nphases, self.Lpartial), dtype=dtype)
        for k in range(self.L):
            i = k % q
            j = k // q
            self.bpartial[i, j] = b[k]
        self.y = np.zeros(chunk_size_out, dtype=dtype)
        self.m_in = 0  # номер ветви, подключенной ко входу

    def __call__(self, x):
        p, q = self.p, self.q
        bufs, y = self.buffers, self.y
        bpart, m_in = self.bpartial, self.m_in
        i = 0  # счетчик входных отсчетов
        j = 0  # счетчик выходных отсчетов
        for j in range(self.chunk_size_out):
            while i <= j * q // p:
                bufs[m_in, 0] = x[i]
                i += 1
                m_in = (m_in - p % q) % q  # поворот ключа против часовой
            y[j] = np.sum(bufs * bpart)
            j += 1
            bufs[:, 1:] = bufs[:, :-1]
            bufs[:, 0] = 0
        for k in range(i, self.chunk_size_in):
            # Добавление оставшихся входных отсчетов в буферы
            bufs[m_in, 0] = x[k]
            m_in = (m_in - p % q) % q  # поворот ключа против часовой
        y *= p
        self.m_in = m_in
        return y


def _checkchunk_size_out(chunk_size_in, chunk_size_out, r):
    """ Проверка корректности значений chunk_size_in и out

    Проверка делимости p*chunk_size_in на q
    и равенства p*chunk_size_in/q == chunk_size_out.

    """
    if (chunk_size_in * r).denominator != 1:
        msg = 'p * chunk_size_in (%d * %d) не делится на q (%d)'
        raise ValueError(msg % (r.numerator, chunk_size_in, r.denominator))
    if chunk_size_in * r != chunk_size_out:
        msg = ('chunk_size_out (%g) != p * chunk_size_in / q '
               '(%d * %d / %d = %g)')
        raise ValueError(msg % (chunk_size_out, r.numerator, chunk_size_in,
                                r.denominator, r*chunk_size_in))


def _determine_band_type(wp, ws):
    """ Вспомогоательная функция для определения типа ЦФ и ширины перех. полосы
    """
    print(f'{wp}; {ws}')
    try:
        if ws[0] < wp[0]:
            btype = 'bandpass'
            dw_tr = min([wp[0] - ws[0], ws[1] - wp[1]])
        else:
            btype = 'bandstop'
            dw_tr = min([ws[0] - wp[0], ws[1] - ws[1]])
    except (TypeError, IndexError):
        if ws < wp:
            btype = 'highpass'
            dw_tr = wp - ws
        else:
            btype = 'lowpass'
            dw_tr = ws - wp
    return btype, dw_tr


def fir_coefs(fp, fs, r, Fs=2, oddL=False, antisymmetric=False):
    """ Синтез КИХ-фильтра методом взвешивания импульсной характеристики.

    Для синтеза используется окно Кайзера.

    Аргументы:
    ----------
    fp: float | iterable
        для ФНЧ и ФВЧ -- граница полосы гарантированного пропускания (ГП), Гц;
        для ПФ и ЗФ -- граничные частоты полос(ы) ГП (пара чисел), Гц
    fs: float | iterable
        для ФНЧ и ФВЧ -- граница полосы гарантированного задерживания (ГЗ), Гц;
        для ПФ и ЗФ -- граничные частоты полос(ы) ГЗ (пара чисел), Гц
    r: float
        наибольшее допустимое отклонение АЧХ от идеальной в полосах ГП, ГЗ, дБ
    Fs: float, необязательный
        частота дискретизации, Гц (не требуется, если частоты fs и fp заданы
        нормированными на Fs/2)
    oddL: bool
        False: синтезировать фильтр с любой длиной ИХ (если L будет четной, то
               задержка сигнала будет на дробное число периодов дискретизации)
        True: синтезировать фильтр с нечетной длиной ИХ (обеспечивает
              задержку сигнала на целое число отсчетов)
    antisymmetric: bool
        False: синтезировать КИХ-фильтр типа I (если L нечетное) или II (если
               L четное)
        True: синтезировать КИХ-фильтр типа III (если L нечетное) или IV (если
               L четное)

    Примечание:
    -----------
    Функция firwin2 не всегда точно обеспечивает желаемые параметры АЧХ,
    поэтому для КИХ фильтров типов I и II используется firwin.
    Для фильтров типов III и IV используется firwin2, т.к. firwin не позволяет
    синтезировать такие фильтры.

    Ссылки:
    -------
    1. https://docs.scipy.org/doc/scipy/reference/signal.html

    2. Теория и применение цифровой обработки сигналов [Текст] / Л. Рабинер,
    Б. Гоулд : пер. с англ. А. Л. Зайцева [и. др.] ; под ред.
    Ю. Н. Александрова. – Москва : Мир, 1978. – 848 с.

    """
    wp = fp / (Fs/2)
    ws = fs / (Fs/2)
    wc = (wp + ws) / 2
    btype, dw_tr = _determine_band_type(wp, ws)
    L, beta = kaiserord(r, dw_tr)
    if oddL and L % 2 == 0:
        L += 1
    if not antisymmetric:
        b = firwin(L, wc, window=('kaiser', beta), fs=2, pass_zero=btype)
    else:
        if btype == 'lowpass':
            f = 0, fp, fs, Fs/2
            D = 1, 1, 0, 0
        elif btype == 'highpass':
            f = 0, fs, fp, Fs/2
            D = 0, 0, 1, 1
        elif btype == 'bandpass':
            f = 0, fs[0], fp[0], fp[1], fs[1], Fs/2
            D = 0, 0, 1, 1, 0, 0
        else:  # btype == 'bandstop'
            f = 0, fp[0], fs[0], fs[1], fp[1], Fs/2
            D = 1, 1, 0, 0, 1, 1
        b = firwin2(L, f, D, nfreqs=512, fs=Fs, window=('kaiser', beta),
                    antisymmetric=True)
    return b


def ddc(adc: np.array, if_center_frequency: float, time_sample_rate: float):
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
