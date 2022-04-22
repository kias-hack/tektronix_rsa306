import numpy as np
from RSA306.types import VersionInfo, InstrumentState, ChannelCorrection, Footer, DataFormat
from struct import unpack
from RSA306.rc import BYTES_PER_SAMPLE, BYTES_PER_SAMPLE_SIGN, FREQ_INDEX_LENGTH, PHASE_INDEX_LENGTH


def parse_version_info(raw_bytes: bytes) -> None:
	""" Извлекает данные версии устройства и файла из заголовка """

	file_id = "".join(map(chr, raw_bytes[:27]))
	endian = np.frombuffer(raw_bytes[512:516], dtype=np.uint32)[0]
	file_format_version = unpack('4B', raw_bytes[516:520])
	api_version = unpack('4B', raw_bytes[520:524])
	fx3_version = unpack('4B', raw_bytes[524:528])
	fpga_version = unpack('4B', raw_bytes[528:532])
	device_sn = "".join(map(chr, raw_bytes[532:596]))

	return VersionInfo(file_id=file_id, endian=endian, file_format_version=file_format_version, api_version=api_version,
					   fx3_version=fx3_version, fpga_version=fpga_version, device_sn=device_sn)


def parse_instrument_state(raw_bytes: bytes) -> InstrumentState:
	""" Извлекает данные состояния устройства из заголовка """

	reference_level = unpack('1d', raw_bytes[1024:1032])[0]
	center_frequency = unpack('1d', raw_bytes[1032:1040])[0]
	temperature = unpack('1d', raw_bytes[1040:1048])[0]
	alignment = unpack('1I', raw_bytes[1048:1052])[0]
	freq_reference = unpack('1I', raw_bytes[1052:1056])[0]
	trig_mode = unpack('1I', raw_bytes[1056:1060])[0]
	trig_source = unpack('1I', raw_bytes[1060:1064])[0]
	trig_trans = unpack('1I', raw_bytes[1064:1068])[0]
	trig_level = unpack('1d', raw_bytes[1068:1076])[0]

	return InstrumentState(reference_level=reference_level, center_frequency=center_frequency, temperature=temperature,
						   alignment=alignment, freq_reference=freq_reference, trig_mode=trig_mode, trig_source=trig_source,
						   trig_trans=trig_trans, trig_level=trig_level)


def parse_data_format(raw_bytes: bytes):
	""" Извлекает данные о форматах из заголовка """

	data_type = np.frombuffer(raw_bytes[2048:2052], dtype=np.uint32)[0]

	if data_type == BYTES_PER_SAMPLE_SIGN:
		data_type = BYTES_PER_SAMPLE

	frame_offset = np.frombuffer(raw_bytes[2052:2056], dtype=np.uint32)[0]
	frame_size = np.frombuffer(raw_bytes[2056:2060], dtype=np.uint32)[0]
	sample_offset = unpack('1I', raw_bytes[2060:2064])[0]
	sample_size = np.frombuffer(raw_bytes[2064:2068], dtype=np.int32)[0]
	non_sample_offset = np.frombuffer(raw_bytes[2068:2072], dtype=np.uint32)[0]
	non_sample_size = np.frombuffer(raw_bytes[2072:2076], dtype=np.uint32)[0]
	if_center_frequency = np.frombuffer(raw_bytes[2076:2084], dtype=np.double)[0]
	sample_rate = np.frombuffer(raw_bytes[2084:2092], dtype=np.double)[0]
	bandwidth = unpack('1d', raw_bytes[2092:2100])[0]
	corrected = unpack('1I', raw_bytes[2100:2104])[0]
	time_type = unpack('1I', raw_bytes[2104:2108])[0]
	ref_time = list(unpack('7i', raw_bytes[2108:2136]))
	clock_samples = unpack('1Q', raw_bytes[2136:2144])[0]
	time_sample_rate = np.frombuffer(raw_bytes[2144:2152], dtype=np.uint64)[0]

	return DataFormat(data_type=data_type, frame_offset=frame_offset, frame_size=frame_size, sample_offset=sample_offset,
					  sample_size=sample_size, non_sample_offset=non_sample_offset, non_sample_size=non_sample_size,
					  if_center_frequency=if_center_frequency, sample_rate=sample_rate, bandwidth=bandwidth,
					  corrected=corrected, time_type=time_type, ref_time=ref_time, clock_samples=clock_samples,
					  time_sample_rate=time_sample_rate)


def parse_channel_correction(raw_bytes: bytes) -> ChannelCorrection:
	""" Извлекает данные коррекции из заголовка """

	adc_scale = np.frombuffer(raw_bytes[3072:3080], dtype=np.double)[0]
	path_delay = np.frombuffer(raw_bytes[3080:3088], dtype=np.double)[0]
	correction_type = np.frombuffer(raw_bytes[4096:4100], dtype=np.uint32)[0]

	table_entries = np.frombuffer(raw_bytes[4352:4356], dtype=np.uint32)[0]

	freq_index = 4356
	freq_index_end = freq_index + FREQ_INDEX_LENGTH

	phase_index = freq_index + FREQ_INDEX_LENGTH

	amp_index = phase_index + PHASE_INDEX_LENGTH
	amp_index_end = amp_index + table_entries * 4

	freq_table = np.frombuffer(raw_bytes[freq_index:freq_index_end], dtype=np.float32)
	phase_table = np.frombuffer(raw_bytes[phase_index:amp_index], dtype=np.float32)
	amp_table = np.frombuffer(raw_bytes[amp_index:amp_index_end], dtype=np.float32)

	return ChannelCorrection(adc_scale=adc_scale, path_delay=path_delay, correction_type=correction_type,
							 table_entries=table_entries, freq_table=freq_table, phase_table=phase_table,
							 amp_table=amp_table)


def parse_footer(raw_bytes: bytes) -> Footer:
	""" Извлекает footer заголовки """

	reserved = np.frombuffer(raw_bytes[0:6], dtype=np.uint16, count=3)
	frame_id = np.frombuffer(raw_bytes[8:12], dtype=np.uint32, count=1)[0]
	trigger2_idx = np.frombuffer(raw_bytes[12:14], dtype=np.uint16, count=1)[0]
	trigger1_idx = np.frombuffer(raw_bytes[14:16], dtype=np.uint16, count=1)[0]
	time_sync_idx = np.frombuffer(raw_bytes[16:18], dtype=np.uint16, count=1)[0]
	frame_status = '{0:8b}'.format(int(np.frombuffer(raw_bytes[18:20], dtype=np.uint16, count=1)))
	timestamp = np.frombuffer(raw_bytes[20:28], dtype=np.uint64, count=1)[0]

	return Footer(reserved=reserved, frame_id=frame_id, trigger2_idx=trigger2_idx, trigger1_idx=trigger1_idx,
				  time_sync_idx=time_sync_idx, frame_status=frame_status, timestamp=timestamp)
