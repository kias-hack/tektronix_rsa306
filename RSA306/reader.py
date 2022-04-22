from RSA306.rc import BYTES_PER_SAMPLE, BYTES_PER_SECOND, HEADER_DATA_LENGTH
from RSA306.parsers import parse_footer, parse_channel_correction, parse_instrument_state, parse_data_format
from RSA306.types import InstrumentState, ChannelCorrection, Footer, DataFormat
import numpy as np
import os
from typing import List, Tuple


class BaseReader:
	""" Базовый класс для чтения файлов RSA-306

	Аргументы:
	---------
	path: string
		путь к файлу

	Атрибуты:
	---------
	adc: np.array
		извлеченные отсчеты

	header_data: bytes[]
		данные заголовка

	instrument_state: InstrumentState
		данные состояния из заголовка

	data_format: DataFormat
		данные формата из заголовка

	channel_correction: ChannelCorrection
		данные коррекции из заголовка

	_path_to_file: string
		путь к файлу

	Примечание:
	-----------
	Каждый наследник должен обязательно реализовать следующие методы (_read_header_data, _parse_data). После истанцирования
	для получения данных необходимо вызвать метод read. Метод read вернет кортеж самых необходимых данный, остальные
	доступны по прямому обращению
	"""

	adc: np.array = np.empty(1)
	header_data: bytes
	instrument_state: InstrumentState
	data_format: DataFormat
	channel_correction: ChannelCorrection

	def __init__(self, path):
		self._path_to_file = path

	def read(self) -> Tuple[np.array, int, int]:
		""" Производит парсинг файлов RSA-306, разбирая общие заголовки и заголовки
		каждого кадра данных

		Возвращаемые значения:
		----------------------
		adc: np.array
			отсчеты АЦП перемноеженные на шаг квантования
		
		center_frequency: float
			центральная частота

		if_center_frequency: float
		"""

		self._read_header_data()

		self.channel_correction = parse_channel_correction(self.header_data)
		self.data_format = parse_data_format(self.header_data)
		self.instrument_state = parse_instrument_state(self.header_data)

		self._parse_data()

		return self.adc, self.instrument_state.center_frequency, self.data_format.if_center_frequency

	def _read_header_data(self) -> None:
		""" Специфичное открытие файла. К примеру r3a содержит отдельный файл r3h в котором хранятся заголовки """

		raise ValueError("Необходимо реализовать метод _read_header_data")

	def _parse_data(self) -> None:
		""" Специфичное чтение данных из файла """

		raise ValueError("Необходимо реализовать метод _parse_data")


class RawReader(BaseReader):
	""" Реализует чтение r3a и r3h файлов """

	def _read_header_data(self) -> None:
		""" Считывает данные из файлов

		Примечание:
		-----------
		Рядом с файлом r3a должен находиться файл с заголовками r3h
		"""

		with open(self._path_to_file[:-1] + 'h', 'rb') as header_file:
			self.header_data = header_file.read(HEADER_DATA_LENGTH)

	def _parse_data(self) -> None:
		""" Извлекает данные отсчетов из файла. Цикл основывается на размере файла в байтах """

		with open(self._path_to_file[:-1] + 'a', 'rb') as data_file:

			file_size = int(os.path.getsize(data_file.name))

			loop = 0
			start_point = 0
			while file_size > 0:
				if file_size > BYTES_PER_SECOND:
					process_data = BYTES_PER_SECOND / BYTES_PER_SAMPLE
				else:
					process_data = file_size
				if loop == 0:
					start_point = 0
				elif loop > 0:
					start_point = loop * BYTES_PER_SECOND

				self._read_adc_data(process_data, start_point, data_file)

				file_size -= BYTES_PER_SECOND

				loop += 1

	def _read_adc_data(self, process_data, start_point, data_file) -> None:
		""" Считывает данные АЦП из файла """
		data_file.seek(start_point)
		adc_samples = np.fromfile(data_file, dtype=np.int16, count=process_data)

		self.adc = np.append(self.adc, adc_samples * self.channel_correction.adc_scale)


class Reader(BaseReader):
	""" Чтение r3f файлов

	Атрибуты:
	---------
	footer: List[Footer]
		данные заголовков из блоков данных

	Примечание:
	-----------
	Дополнительно класс извлекает данные заголовков из блоков с отсчетами
	"""

	footer: List[Footer]

	def _read_header_data(self) -> None:
		with open(self._path_to_file, 'rb') as header_file:
			self.header_data = header_file.read(HEADER_DATA_LENGTH)

	def _parse_data(self) -> None:
		""" Извлекает отсчтеты АЦП из файла. Цикл основывается на количестве блоков данных в файле"""

		with open(self._path_to_file, 'rb') as data_file:

			file_size = os.path.getsize(data_file.name)
			num_frames = int((file_size / self.data_format.frame_size) - 1)

			fps = 13698
			loop = 0
			start_point = 0
			while num_frames > 0:
				if num_frames > fps:
					process_data = fps
				else:
					process_data = num_frames

				if loop == 0:
					start_point = self.data_format.frame_offset
				elif loop > 0:
					start_point = loop * fps * self.data_format.frame_size

				self._read_adc_data(process_data, start_point, data_file)

				num_frames -= fps
				loop += 1

	def _read_adc_data(self, process_data, start_point, data_file) -> None:
		""" Считывает данные АЦП из блока данных """

		data_file.seek(start_point)
		adc_samples = np.empty(process_data * self.data_format.sample_size)
		f_start = 0
		f_stop = self.data_format.sample_size

		self.footer = list(range(process_data))

		for i in range(process_data):
			frame = data_file.read(self.data_format.non_sample_offset)
			adc_samples[f_start:f_stop] = np.frombuffer(frame, dtype=np.int16)

			f_start = f_stop
			f_stop = f_stop + self.data_format.sample_size

			self.footer[i] = parse_footer(data_file.read(self.data_format.non_sample_size))

		self.adc = np.append(self.adc, adc_samples * self.channel_correction.adc_scale)


def _is_compatible_extension(extension):
	""" Проверяет совместимость файла. Возможные расширения [.3rf | .r3a | r3h]

	Аргументы:
	----------
	extension: string
		расширение файла

	Возвращаемые аргументы:
	-----------------------
	result: boolean
		совместим файл или нет
	"""

	return extension in [".r3f", ".r3a", "r3h"]


def get_reader(path) -> BaseReader:
	""" Читает файлы, сохранённые с помощью RSA-306. Поддерживает r3a и r3f

	Аргументы:
	----------
	path: string
		путь к файлу сохраненного с помощью RSA306

	Возвращаемые значения:
	----------------------
	reader: BaseReader
		класс читающий конкретный файл [r3f | r3a] переданный на вход

	Примечание:
	-----------
	Для формата r3a необходимо наличие рядом файла с расширением r3h, в
	нем хранятся заголовки
	"""

	extension = path[-4:]

	if not _is_compatible_extension(extension):
		raise ValueError("f'Допустимы расширения файлов: r3f, r3h, r3a; задано {}'".format(extension))

	if extension == ".r3f":
		return Reader(path)

	return RawReader(path)
