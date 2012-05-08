# -*- coding: utf-8 -*
import re
import string
import types

DEBUG = 0

class IRCError(Exception):
	pass

class ServerConnectionError(IRCError):
	pass

class ServerNotConnectedError(ServerConnectionError):
	pass

class Event:
	def __init__( self, eventType, source, target, arguments = None ):
		"""Constructor of Event objects.
		Arguments:
			eventtype -- A string describing the event.
			source -- The originator of the event (a nick mask or a server).
			target -- The target of the event (a nick or a channel).
			arguments -- Any event specific arguments.
		"""
		self.eventType = eventType
		self.source = source and source.decode( 'utf-8' )
		self.target = target and target.decode( 'utf-8' )
		if arguments:
			self.arguments = [ a.decode( 'utf-8' ) for a in arguments ]
		else:
			self.arguments = []


_rfc_1459_command_regexp = re.compile("^(:(?P<prefix>[^ ]+) +)?(?P<command>[^ ]+)( *(?P<argument> .+))?")

# Huh!?  Crrrrazy EFNet doesn't follow the RFC: their ircd seems to
# use \n as message separator!  :P
_linesep_regexp = re.compile("\r?\n")



# self.timerMgr.setTimeout( func, delay ):
# ircClient.processData( newData )

class IRCClient:
	def __init__( self, send, timerMgr, handler ):
		self.send = send
		self.timerMgr = timerMgr
		self.prevBuf = ''
		self.eventHandler = handler
		self.realServerName = ''
		self.realNickname = ''

	def handleEvent( self, event ):
		f = 'on_' + event.eventType
		if hasattr( self.eventHandler, f ):
			getattr( self.eventHandler, f )( self, event )
		else:
			self.eventHandler.on_default( self, event )

	def processData( self, newData ):
		lines = _linesep_regexp.split( self.prevBuf + newData )

		# Save the last, unfinished line.
		self.prevBuf = lines.pop()

		for line in lines:
			if DEBUG:
				print "FROM SERVER:", line

			if not line:
				continue

			prefix = None
			command = None
			arguments = None
#			self.handleEvent( Event("all_raw_messages",
#									 self.get_server_name(),
#									 None,
#									 [line] ) )

			m = _rfc_1459_command_regexp.match(line)
			if m.group("prefix"):
				prefix = m.group("prefix")
				if not self.realServerName:
					self.realServerName = prefix

			if m.group("command"):
				command = m.group("command").lower()

			if m.group("argument"):
				a = m.group("argument").split(" :", 1)
				arguments = a[0].split()
				if len(a) == 2:
					arguments.append(a[1])

			# Translate numerics into more readable strings.
			if command in numeric_events:
				command = numeric_events[command]

			if command == "nick":
				if nm_to_n(prefix) == self.realNickname:
					self.realNickname = arguments[0]
			elif command == "welcome":
				# Record the nickname in case the client changed nick
				# in a nicknameinuse callback.
				self.realNickname = arguments[0]

			if command in ["privmsg", "notice"]:
				target, message = arguments[0], arguments[1]
				messages = _ctcp_dequote(message)

				if command == "privmsg":
					if is_channel(target):
						command = "pubmsg"
				else:
					if is_channel(target):
						command = "pubnotice"
					else:
						command = "privnotice"

				for m in messages:
					if type(m) is types.TupleType:
						if command in ["privmsg", "pubmsg"]:
							command = "ctcp"
						else:
							command = "ctcpreply"

						m = list(m)
						if DEBUG:
							print "command: %s, source: %s, target: %s, arguments: %s" % (
								command, prefix, target, m)
						self.handleEvent(Event(command, prefix, target, m))
						if command == "ctcp" and m[0] == "ACTION":
							self.handleEvent(Event("action", prefix, target, m[1:]))
					else:
						if DEBUG:
							print "command: %s, source: %s, target: %s, arguments: %s" % (
								command, prefix, target, [m])
						self.handleEvent(Event(command, prefix, target, [m]))
			else:
				target = None

				if command == "quit":
					arguments = [arguments[0]]
				elif command == "ping":
					target = arguments[0]
				else:
					target = arguments[0]
					arguments = arguments[1:]

				if command == "mode":
					if not is_channel(target):
						command = "umode"

				if DEBUG:
					print "command: %s, source: %s, target: %s, arguments: %s" % (
						command, prefix, target, arguments)
				self.handleEvent( Event( command, prefix, target, arguments ) )

	def send_raw( self, u ):
		assert( isinstance( u, unicode ) )
		"""Send raw string to the server.
		The string will be padded with appropriate CR LF.
		"""
		self.send( u.encode( 'utf-8' ) + "\r\n" )
		if DEBUG:
			print u"TO SERVER:", u

	# Commands --------------------------------------------------------------
	def nick( self, newnick ):
		"""Send a NICK command."""
		self.send_raw( u"NICK " + newnick )

	def user( self, username, realname ):
		"""Send a USER command."""
		self.send_raw( u"USER %s 0 * :%s" % ( username, realname ) )

	def pong( self, target, target2 = u'' ):
		"""Send a PONG command."""
		self.send_raw( u"PONG %s%s" % ( target, target2 and ( u" " + target2 ) ) )

	def join( self, channel, key=u"" ):
		"""Send a JOIN command."""
		self.send_raw( u"JOIN %s%s" % ( channel, ( key and ( u" " + key ) ) ) )

	def privmsg( self, target, text ):
		"""Send a PRIVMSG command."""
		# Should limit len(text) here!
		self.send_raw( u"PRIVMSG %s :%s" % ( target, text ) )

	def part( self, channel, message=u"" ):
		"""Send a PART command."""
		self.send_raw( u"PART " + channel + (message and (u" " + message)) )

	def kick( self, channel, nick, comment="" ):
		"""Send a KICK command."""
		self.send_raw( u"KICK %s %s%s" % (channel, nick, (comment and (u" :" + comment))) )

	def topic( self, channel, new_topic=None ):
		"""Send a TOPIC command."""
		if new_topic is None:
			self.send_raw( u"TOPIC " + channel )
		else:
			self.send_raw( u"TOPIC %s :%s" % (channel, new_topic) )


#########################################################################################################

# Numeric table mostly stolen from the Perl IRC module (Net::IRC).
numeric_events = {
	"001": "welcome",
	"002": "yourhost",
	"003": "created",
	"004": "myinfo",
	"005": "featurelist",  # XXX
	"200": "tracelink",
	"201": "traceconnecting",
	"202": "tracehandshake",
	"203": "traceunknown",
	"204": "traceoperator",
	"205": "traceuser",
	"206": "traceserver",
	"207": "traceservice",
	"208": "tracenewtype",
	"209": "traceclass",
	"210": "tracereconnect",
	"211": "statslinkinfo",
	"212": "statscommands",
	"213": "statscline",
	"214": "statsnline",
	"215": "statsiline",
	"216": "statskline",
	"217": "statsqline",
	"218": "statsyline",
	"219": "endofstats",
	"221": "umodeis",
	"231": "serviceinfo",
	"232": "endofservices",
	"233": "service",
	"234": "servlist",
	"235": "servlistend",
	"241": "statslline",
	"242": "statsuptime",
	"243": "statsoline",
	"244": "statshline",
	"250": "luserconns",
	"251": "luserclient",
	"252": "luserop",
	"253": "luserunknown",
	"254": "luserchannels",
	"255": "luserme",
	"256": "adminme",
	"257": "adminloc1",
	"258": "adminloc2",
	"259": "adminemail",
	"261": "tracelog",
	"262": "endoftrace",
	"263": "tryagain",
	"265": "n_local",
	"266": "n_global",
	"300": "none",
	"301": "away",
	"302": "userhost",
	"303": "ison",
	"305": "unaway",
	"306": "nowaway",
	"311": "whoisuser",
	"312": "whoisserver",
	"313": "whoisoperator",
	"314": "whowasuser",
	"315": "endofwho",
	"316": "whoischanop",
	"317": "whoisidle",
	"318": "endofwhois",
	"319": "whoischannels",
	"321": "liststart",
	"322": "list",
	"323": "listend",
	"324": "channelmodeis",
	"329": "channelcreate",
	"331": "notopic",
	"332": "currenttopic",
	"333": "topicinfo",
	"341": "inviting",
	"342": "summoning",
	"346": "invitelist",
	"347": "endofinvitelist",
	"348": "exceptlist",
	"349": "endofexceptlist",
	"351": "version",
	"352": "whoreply",
	"353": "namreply",
	"361": "killdone",
	"362": "closing",
	"363": "closeend",
	"364": "links",
	"365": "endoflinks",
	"366": "endofnames",
	"367": "banlist",
	"368": "endofbanlist",
	"369": "endofwhowas",
	"371": "info",
	"372": "motd",
	"373": "infostart",
	"374": "endofinfo",
	"375": "motdstart",
	"376": "endofmotd",
	"377": "motd2",		# 1997-10-16 -- tkil
	"381": "youreoper",
	"382": "rehashing",
	"384": "myportis",
	"391": "time",
	"392": "usersstart",
	"393": "users",
	"394": "endofusers",
	"395": "nousers",
	"401": "nosuchnick",
	"402": "nosuchserver",
	"403": "nosuchchannel",
	"404": "cannotsendtochan",
	"405": "toomanychannels",
	"406": "wasnosuchnick",
	"407": "toomanytargets",
	"409": "noorigin",
	"411": "norecipient",
	"412": "notexttosend",
	"413": "notoplevel",
	"414": "wildtoplevel",
	"421": "unknowncommand",
	"422": "nomotd",
	"423": "noadmininfo",
	"424": "fileerror",
	"431": "nonicknamegiven",
	"432": "erroneusnickname", # Thiss iz how its speld in thee RFC.
	"433": "nicknameinuse",
	"436": "nickcollision",
	"437": "unavailresource",  # "Nick temporally unavailable"
	"441": "usernotinchannel",
	"442": "notonchannel",
	"443": "useronchannel",
	"444": "nologin",
	"445": "summondisabled",
	"446": "usersdisabled",
	"451": "notregistered",
	"461": "needmoreparams",
	"462": "alreadyregistered",
	"463": "nopermforhost",
	"464": "passwdmismatch",
	"465": "yourebannedcreep", # I love this one...
	"466": "youwillbebanned",
	"467": "keyset",
	"471": "channelisfull",
	"472": "unknownmode",
	"473": "inviteonlychan",
	"474": "bannedfromchan",
	"475": "badchannelkey",
	"476": "badchanmask",
	"477": "nochanmodes",  # "Channel doesn't support modes"
	"478": "banlistfull",
	"481": "noprivileges",
	"482": "chanoprivsneeded",
	"483": "cantkillserver",
	"484": "restricted",   # Connection is restricted
	"485": "uniqopprivsneeded",
	"491": "nooperhost",
	"492": "noservicehost",
	"501": "umodeunknownflag",
	"502": "usersdontmatch",
}

generated_events = [
	# Generated events
	"dcc_connect",
	"dcc_disconnect",
	"dccmsg",
	"disconnect",
	"ctcp",
	"ctcpreply",
]

protocol_events = [
	# IRC protocol events
	"error",
	"join",
	"kick",
	"mode",
	"part",
	"ping",
	"privmsg",
	"privnotice",
	"pubmsg",
	"pubnotice",
	"quit",
	"invite",
	"pong",
]

all_events = generated_events + protocol_events + numeric_events.values()

_LOW_LEVEL_QUOTE = "\020"
_CTCP_LEVEL_QUOTE = "\134"
_CTCP_DELIMITER = "\001"

_low_level_mapping = {
	"0": "\000",
	"n": "\n",
	"r": "\r",
	_LOW_LEVEL_QUOTE: _LOW_LEVEL_QUOTE
}

_low_level_regexp = re.compile(_LOW_LEVEL_QUOTE + "(.)")

def mask_matches(nick, mask):
	"""Check if a nick matches a mask.

	Returns true if the nick matches, otherwise false.
	"""
	nick = irc_lower(nick)
	mask = irc_lower(mask)
	mask = mask.replace("\\", "\\\\")
	for ch in ".$|[](){}+":
		mask = mask.replace(ch, "\\" + ch)
	mask = mask.replace("?", ".")
	mask = mask.replace("*", ".*")
	r = re.compile(mask, re.IGNORECASE)
	return r.match(nick)

_special = "-[]\\`^{}"
nick_characters = string.ascii_letters + string.digits + _special
_ircstring_translation = string.maketrans(string.ascii_uppercase + "[]\\^",
										  string.ascii_lowercase + "{}|~")

def irc_lower(s):
	"""Returns a lowercased string.

	The definition of lowercased comes from the IRC specification (RFC
	1459).
	"""
	return s.translate(_ircstring_translation)

def _ctcp_dequote(message):
	"""[Internal] Dequote a message according to CTCP specifications.

	The function returns a list where each element can be either a
	string (normal message) or a tuple of one or two strings (tagged
	messages).  If a tuple has only one element (ie is a singleton),
	that element is the tag; otherwise the tuple has two elements: the
	tag and the data.

	Arguments:

		message -- The message to be decoded.
	"""

	def _low_level_replace(match_obj):
		ch = match_obj.group(1)

		# If low_level_mapping doesn't have the character as key, we
		# should just return the character.
		return _low_level_mapping.get(ch, ch)

	if _LOW_LEVEL_QUOTE in message:
		# Yup, there was a quote.  Release the dequoter, man!
		message = _low_level_regexp.sub(_low_level_replace, message)

	if _CTCP_DELIMITER not in message:
		return [message]
	else:
		# Split it into parts.  (Does any IRC client actually *use*
		# CTCP stacking like this?)
		chunks = message.split(_CTCP_DELIMITER)

		messages = []
		i = 0
		while i < len(chunks)-1:
			# Add message if it's non-empty.
			if len(chunks[i]) > 0:
				messages.append(chunks[i])

			if i < len(chunks)-2:
				# Aye!  CTCP tagged data ahead!
				messages.append(tuple(chunks[i+1].split(" ", 1)))

			i = i + 2

		if len(chunks) % 2 == 0:
			# Hey, a lonely _CTCP_DELIMITER at the end!  This means
			# that the last chunk, including the delimiter, is a
			# normal message!  (This is according to the CTCP
			# specification.)
			messages.append(_CTCP_DELIMITER + chunks[-1])

		return messages

def is_channel(string):
	"""Check if a string is a channel name.

	Returns true if the argument is a channel name, otherwise false.
	"""
	return string and string[0] in "#&+!"

def ip_numstr_to_quad(num):
	"""Convert an IP number as an integer given in ASCII
	representation (e.g. '3232235521') to an IP address string
	(e.g. '192.168.0.1')."""
	n = long(num)
	p = map(str, map(int, [n >> 24 & 0xFF, n >> 16 & 0xFF,
						   n >> 8 & 0xFF, n & 0xFF]))
	return ".".join(p)

def ip_quad_to_numstr(quad):
	"""Convert an IP address string (e.g. '192.168.0.1') to an IP
	number as an integer given in ASCII representation
	(e.g. '3232235521')."""
	p = map(long, quad.split("."))
	s = str((p[0] << 24) | (p[1] << 16) | (p[2] << 8) | p[3])
	if s[-1] == "L":
		s = s[:-1]
	return s

def nm_to_n(s):
	"""Get the nick part of a nickmask.

	(The source of an Event is a nickmask.)
	"""
	return s.split("!")[0]

def nm_to_uh(s):
	"""Get the userhost part of a nickmask.

	(The source of an Event is a nickmask.)
	"""
	return s.split("!")[1]

def nm_to_h(s):
	"""Get the host part of a nickmask.

	(The source of an Event is a nickmask.)
	"""
	return s.split("@")[1]

def nm_to_u(s):
	"""Get the user part of a nickmask.

	(The source of an Event is a nickmask.)
	"""
	s = s.split("!")[1]
	return s.split("@")[0]

def parse_nick_modes(mode_string):
	"""Parse a nick mode string.

	The function returns a list of lists with three members: sign,
	mode and argument.  The sign is \"+\" or \"-\".  The argument is
	always None.

	Example:

	>>> irclib.parse_nick_modes(\"+ab-c\")
	[['+', 'a', None], ['+', 'b', None], ['-', 'c', None]]
	"""

	return _parse_modes(mode_string, "")

def parse_channel_modes(mode_string):
	"""Parse a channel mode string.

	The function returns a list of lists with three members: sign,
	mode and argument.  The sign is \"+\" or \"-\".  The argument is
	None if mode isn't one of \"b\", \"k\", \"l\", \"v\" or \"o\".

	Example:

	>>> irclib.parse_channel_modes(\"+ab-c foo\")
	[['+', 'a', None], ['+', 'b', 'foo'], ['-', 'c', None]]
	"""

	return _parse_modes(mode_string, "bklvo")

def _parse_modes(mode_string, unary_modes=""):
	"""[Internal]"""
	modes = []
	arg_count = 0

	# State variable.
	sign = ""

	a = mode_string.split()
	if len(a) == 0:
		return []
	else:
		mode_part, args = a[0], a[1:]

	if mode_part[0] not in "+-":
		return []
	for ch in mode_part:
		if ch in "+-":
			sign = ch
		elif ch == " ":
			collecting_arguments = 1
		elif ch in unary_modes:
			if len(args) >= arg_count + 1:
				modes.append([sign, ch, args[arg_count]])
				arg_count = arg_count + 1
			else:
				modes.append([sign, ch, None])
		else:
			modes.append([sign, ch, None])
	return modes

