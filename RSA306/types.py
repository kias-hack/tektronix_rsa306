"""
Содержит классы заполняемые из заголовков 
"""

from collections import namedtuple

VersionInfo = namedtuple("VersionInfo", "file_id endian file_format_version api_version fx3_version fpga_version "
										"device_sn")

InstrumentState = namedtuple("InstrumentState", "reference_level center_frequency temperature alignment "
												"freq_reference trig_mode trig_source trig_trans trig_level")

DataFormat = namedtuple("DataFormat", "data_type frame_offset frame_size sample_offset sample_size non_sample_offset "
									  "non_sample_size if_center_frequency sample_rate bandwidth corrected time_type "
									  "ref_time clock_samples time_sample_rate")

ChannelCorrection = namedtuple("ChannelCorrection", "adc_scale path_delay correction_type table_entries freq_table "
													"amp_table phase_table")

Footer = namedtuple("Footer", "frame_id trigger2_idx trigger1_idx time_sync_idx "
								"frame_status timestamp reserved")