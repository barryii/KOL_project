class Chienseating:
	@property
	def channel_display_name(self) -> str:
		return '千千進食中'
	@property
	def channel_name(self) -> str:
		return 'Chienseating'
	@property
	def channel_id(self) -> str:
		return 'UC9i2Qgd5lizhVgJrdnxunKw'
	@property
	def playlist_id(self) -> str:
		return 'UU' + self.channel_id[2:]
	@property
	def playlist_id_shorts(self) -> str:
		return 'UUSH' + self.channel_id[2:]
	@property
	def playlist_id_stream(self) -> str:
		return 'UULV' + self.channel_id[2:]

class HowHowEat:
	@property
	def channel_display_name(self) -> str:
		return '吃貨豪豪HowHowEat'
	@property
	def channel_name(self) -> str:
		return 'HowHowEat'
	@property
	def channel_id(self) -> str:
		return 'UCa2YiSXNTkmOA-QTKdzzbSQ'
	@property
	def playlist_id(self) -> str:
		return 'UU' + self.channel_id[2:]
	@property
	def playlist_id_shorts(self) -> str:
		return 'UUSH' + self.channel_id[2:]
	@property
	def playlist_id_stream(self) -> str:
		return 'UULV' + self.channel_id[2:]
