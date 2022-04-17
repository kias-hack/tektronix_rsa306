class FileNotContainFooterData(Exception):
	def __init__(self):
		super().__init__("Because a .r3f file was not chosen, footer data cannot be extracted.")