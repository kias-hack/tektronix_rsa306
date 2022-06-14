from RSA306.rc import BYTES_PER_SAMPLE, BLOCK_R3F_SIZE, HEADER_DATA_LENGTH, SAMPLES_PER_BLOCK, TRANSPORT_FOOTER_SIZE
from RSA306.parsers import parse_footer, parse_channel_correction, parse_instrument_state, \
	parse_data_format, parse_version_info
from RSA306.types import InstrumentState, ChannelCorrection, DataFormat, VersionInfo
from math import ceil
import numpy as np


class BaseReader:
	""" Базовый класс для чтения файлов RSA-306

	Аргументы:
	---------
	path: string
		путь к файлу

	Атрибуты:
	---------
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
	Каждый наследник должен обязательно реализовать следующие методы (read, blockread, _read_header_data).
	После истанцирования для получения данных можно воспользоваться методами read и blockread.
	Предполагается что метод read будет возвращать все отсчеты из файла, а метод blockread будет возвращать данные
	блоками указанного в параметрах размера
	"""

	header_data: bytes
	version_info: VersionInfo
	instrument_state: InstrumentState
	data_format: DataFormat
	channel_correction: ChannelCorrection

	def __init__(self, path):
		self._path_to_file = path
		self._read_header_data()
		self.version_info = parse_version_info(self.header_data)
		self.channel_correction = parse_channel_correction(self.header_data)
		self.data_format = parse_data_format(self.header_data)
		self.instrument_state = parse_instrument_state(self.header_data)

	def read(self) -> np.array:
		raise NotImplementedError("Необходимо реализовать метод read")

	def readblock(self) -> np.array:
		raise NotImplementedError("Необходимо реализовать метод readblock")

	def _read_header_data(self) -> None:
		""" Специфичное открытие файла. К примеру r3a содержит отдельный файл r3h в котором хранятся заголовки """

		raise NotImplementedError("Необходимо реализовать метод _read_header_data")

	def __str__(self):
		""" Вывод информации об экземпляре класса в строку. """
		str_lst = []
		str_lst.append('------------\nData format:\n------------')
		str_lst.append(f'if_center_frequency: {self.data_format.if_center_frequency}')
		str_lst.append(f'sample_rate: {self.data_format.sample_rate}')
		str_lst.append(f'bandwidth: {self.data_format.bandwidth}')
		str_lst.append(f'corrected: {self.data_format.corrected}')
		str_lst.append(f'data_type: {self.data_format.data_type}')
		str_lst.append(f'frame_offset: {self.data_format.frame_offset}')
		str_lst.append(f'frame_size: {self.data_format.frame_size}')
		str_lst.append(f'sample_offset: {self.data_format.sample_offset}')
		str_lst.append(f'sample_size: {self.data_format.sample_size}')
		str_lst.append(f'non_sample_offset: {self.data_format.non_sample_offset}')
		str_lst.append(f'non_sample_size: {self.data_format.non_sample_size}')
		str_lst.append(f'time_type: {self.data_format.time_type}')
		str_lst.append(f'ref_time: {self.data_format.ref_time}')
		str_lst.append(f'clock_samples: {self.data_format.clock_samples}')
		str_lst.append(f'time_sample_rate: {self.data_format.time_sample_rate}')

		str_lst.append('-------------\nVersion info:\n-------------')
		str_lst.append(f'file_id: {self.version_info.file_id}')
		str_lst.append(f'endian: {self.version_info.endian}')
		str_lst.append(f'file_format_version: {self.version_info.file_format_version}')
		str_lst.append(f'api_version: {self.version_info.api_version}')
		str_lst.append(f'fx3_version: {self.version_info.fx3_version}')
		str_lst.append(f'fpga_version: {self.version_info.fpga_version}')
		str_lst.append(f'device_sn: {self.version_info.device_sn}')

		str_lst.append('-----------------\nInstrument state:\n-----------------')
		str_lst.append(f'reference_level: {self.instrument_state.reference_level}')
		str_lst.append(f'center_frequency: {self.instrument_state.center_frequency}')
		str_lst.append(f'temperature: {self.instrument_state.temperature}')
		str_lst.append(f'alignment: {self.instrument_state.alignment}')
		str_lst.append(f'freq_reference: {self.instrument_state.freq_reference}')
		str_lst.append(f'trig_mode: {self.instrument_state.trig_mode}')
		str_lst.append(f'trig_source: {self.instrument_state.trig_source}')
		str_lst.append(f'trig_trans: {self.instrument_state.trig_trans}')
		str_lst.append(f'trig_level: {self.instrument_state.trig_level}')

		str_lst.append('-------------------\nChannel correction:\n-------------------')
		str_lst.append(f'adc_scale: {self.channel_correction.adc_scale}')
		str_lst.append(f'path_delay: {self.channel_correction.path_delay}')
		str_lst.append(f'correction_type: {self.channel_correction.correction_type}')
		str_lst.append(f'table_entries: {self.channel_correction.table_entries}')

		return '\n'.join(str_lst)


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

	def read(self) -> np.array:
		""" Считывает отсчёты с АЦП из файла полностью.

		Возвращает:
		-----------
		adc_samples: np.array
			массив, содержащий все отсчёты сигнала, записанные в файл

		"""
		data_path = self._path_to_file[:-1] + 'a'
		adc_samples = np.fromfile(data_path, dtype=np.int16)
		return adc_samples

	def readblock(self, samples_per_block, short_allowed=True) -> np.array:
		""" Считывает отсчёты с АЦП из файла по блокам заданного размера.

		Аргументы:
		----------
		samples_per_block: int
			размер блока в отсчётах
		short_allowed: bool
			False - если последний блок неполный, он отбрасывается
			True - если последний блок неполный, он возвращается как массив
				   с числом отсчётов менее samples_per_block

		Возвращает:
		-----------
		adc_samples: np.array
			буфер чтения, содержащий отсчёты текущего блока данных

		Примечание:
		-----------
		Функция-генератор.

		"""
		bytes_per_block = samples_per_block * BYTES_PER_SAMPLE
		adc_bytebuf = bytearray(bytes_per_block)
		adc_samples = np.frombuffer(adc_bytebuf, dtype=np.int16)
		data_path = self._path_to_file[:-1] + 'a'
		file_exhausted = False
		with open(data_path, 'rb') as data_file:
			while True:
				n_bytes_read = data_file.readinto(adc_bytebuf)
				if n_bytes_read is None:
					file_exhausted = True
				elif n_bytes_read < bytes_per_block:
					file_exhausted = True
					if short_allowed:
						yield adc_samples[:n_bytes_read // BYTES_PER_SAMPLE]
				else:
					yield adc_samples
				if file_exhausted:
					break


class Reader(BaseReader):
	""" Чтение r3f файлов

	Примечание:
	-----------
	Дополнительно класс извлекает данные заголовков из блоков с отсчетами по запросу пользователя в методе readblock

	"""

	def _read_header_data(self) -> None:
		with open(self._path_to_file, 'rb') as header_file:
			self.header_data = header_file.read(HEADER_DATA_LENGTH)

	def read(self):
		""" Извлекает все отсчеты АЦП из файла

		Возвращает:
		-----------
		np.array
			все отсчеты АЦП из файла считанные через readblock
		"""
		return np.concatenate([adc_samples for adc_samples in self.readblock(SAMPLES_PER_BLOCK)])

	def readblock(self, samples_per_block, short_allowed=True, read_metadata=False):
		""" Считывает отсчёты с АЦП из файла по блокам заданного размера.

		Аргументы:
		----------
		samples_per_block: int
			размер блока в отсчётах
		short_allowed: bool
			False - если последний блок неполный, он отбрасывается
			True - если последний блок неполный, он возвращается как массив
				   с числом отсчётов менее samples_per_block
		read_metadata: bool
			False - не извлекает данные
			True - извлекает данные, причем формат возвращаемых данных меняется на кортеж. Первыми в кортеже
					располагаются отсчеты, вторым элементом кортежа является структура Footer с заголовками фрейма

		Возвращает:
		-----------
		np.array | tuple(np.array, RSA306.rc.Footer)
			отсчеты АЦП или фреймы с отсчетами АЦП и заголовочными данными каждого фрейма

		Примечание:
		-----------
		Функция-генератор. Меняет формат выходных данных в зависимости от параметра read_metadata

		"""
		if read_metadata and (samples_per_block % SAMPLES_PER_BLOCK) != 0:
			raise ValueError("Чтобы получать отсчеты сместе с метаданными необходимо указать размер блока с "
							 "отсчетами равный 8178. Можно воспользоваться константой RSA306.rc.SAMPLES_PER_BLOCK")

		with open(self._path_to_file, 'rb') as data_file:
			data_file.seek(HEADER_DATA_LENGTH)

			excessed_adc_samples = np.array([])

			num_blocks = ceil(samples_per_block / SAMPLES_PER_BLOCK)

			blocks_buffer = bytearray(num_blocks * BLOCK_R3F_SIZE)
			blocks_buffer_mem = memoryview(blocks_buffer)

			block_samples = np.empty(num_blocks, dtype=object)
			if read_metadata:
				block_header = np.empty(num_blocks, dtype=object)

			for block_index in range(num_blocks):
				block_start_samples = block_index * BLOCK_R3F_SIZE
				block_stop_samples = block_start_samples + BLOCK_R3F_SIZE - TRANSPORT_FOOTER_SIZE

				block_samples[block_index] = np.frombuffer(blocks_buffer_mem[block_start_samples:block_stop_samples],
														   dtype=np.int16)

				if read_metadata:
					block_start_header = block_index * BLOCK_R3F_SIZE + SAMPLES_PER_BLOCK * BYTES_PER_SAMPLE
					block_stop_header = block_start_header + TRANSPORT_FOOTER_SIZE

					block_header[block_index] = blocks_buffer_mem[block_start_header:block_stop_header]

			file_exhausted = False
			while True:
				n_read_block_size = data_file.readinto(blocks_buffer)

				if len(excessed_adc_samples) >= samples_per_block:
					divided = np.split(excessed_adc_samples, [samples_per_block])

					excessed_adc_samples = divided[1]

					yield divided[0]

				if n_read_block_size is None:
					file_exhausted = True
				elif n_read_block_size < len(blocks_buffer):
					file_exhausted = True

					if short_allowed:
						blocks_count = n_read_block_size // BLOCK_R3F_SIZE

						if read_metadata:
							yield tuple(zip(block_samples[:blocks_count],
											map(parse_footer, block_header)[:blocks_count]))
						else:
							samples_from_blocks = np.concatenate(block_samples[:blocks_count])

							yield np.concatenate((excessed_adc_samples, samples_from_blocks))

				else:
					if read_metadata:
						yield tuple(zip(block_samples, list(map(parse_footer, block_header))))
					else:
						samples_from_blocks = np.concatenate(block_samples)

						divided = np.split(samples_from_blocks, [samples_per_block - len(excessed_adc_samples)])

						data = np.concatenate((excessed_adc_samples, divided[0]))

						excessed_adc_samples = divided[1]

						yield data

				if file_exhausted:
					break


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
