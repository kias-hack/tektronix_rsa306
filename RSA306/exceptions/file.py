class InvalidInputFileExtension(Exception):
	def __init__(self):
		super().__init__("Compatible file extension not found, check input file and try again.")
