#!/usr/bin/env python
'''Main eve class, constructs basic IRC stuff with twisted
Should NOT contain logic for anything after the bot starts'''
from twisted.words.protocols import irc 
from twisted.internet import reactor, protocol, ssl
#import application
from twisted.application import internet, service
from twisted.python import log
# system imports
import os
import time

global CONFIG
CONFIG = {}

def set_config(c):
    global CONFIG
    CONFIG = c

class Log(object):
    lines = 0
    filename = ''
    startdate = 0

    def __init__(self, filename):
        filename = 'logs/' + filename
        self.startdate = time.localtime()[0:3]
        if os.path.exists(filename):
            os.system('rm '+filename) # FIXME: this kind of sucks -- maybe check the length first?
        self.filename = filename

    def msg(self, nick, line, action=False, special='*'):
        t=list(time.localtime()[0:3])
        t[2] -= 1
        if t > self.startdate:
            os.system('rm '+self.filename)

        if len(line) > 400 or len(nick) > 30: 
            raise ValueError('Too much data, Dying.')
        else:
            f = open(self.filename, 'a')
            if not action: 
                f.write('[%s] <%s> %s\n' % (
                    time.strftime('%x %H:%M:%S'),
                    nick,
                    line,
                ))
            else: 
                f.write('[%s] %s %s %s\n' % (
                    time.strftime('%x %H:%M:%S'),
                    special,
                    nick,
                    line,
                ))
            f.flush()
            f.close()

class eveBot(irc.IRCClient):
    """The bot class inheriting from twisted.words.irc.IRCClient"""
    # global definitions
    logger = log
    config = CONFIG
    nickname = 'eve|' + str(os.getpid())
    reactor = reactor
    factory = None
    channels = {}
    irclogs = {}

    def is_admin(self, user):
        '''Check if a nick matches any of the admins''' # TODO
        return False

    def apply_config(self): 
        '''apply conf for live-update'''
        for key in self.config.keys():
            # check for set_* for each option
            if hasattr(self, 'set_'+key): 
                method = getattr(self, 'set_'+key)
                method(self.config[key])

            # special case for networks. only apply settings to the current net
            for key in self.config['networks'].keys():
                if hasattr(self, 'set_'+key): 
                    method = getattr(self, 'set_'+key)
                    method(self.config['networks'][key])
            
    def set_nick(self, nick):
        '''Helper for setting eve's nickname'''
        self.setNick(nick)
        self.nickname = nick
    def set_channels(self, channels):
        '''Live-update function which joins all channels in conf'''
        for chan in channels: self.join(chan)
    def set_plugins(self, plugins):
        '''Re-load all plugins in conf'''
        self.factory.load_plugins()

    def join(self, channel):
        irc.IRCClient.join(self, channel)
        hasnet = self.irclogs.get(self.factory.netname)
        if not hasnet:
            self.irclogs[self.factory.netname] = {}
        self.irclogs[self.factory.netname].update({
            channel: Log(channel)})
        self.channels[self.factory.netname] = self.channels.get(self.factory.netname,[]) + [channel]

    def part(self, channel, reason='baibai'):
        irc.IRCClient.part(self, channel, reason=reason)
        self.channels[self.factory.netname].pop(self.channels[self.factory.netname].index(channel))

    def connectionMade(self):
        '''Called when eve is connected to something'''
        self.set_nick(self.factory.netconfig['nicks'][0])
        irc.IRCClient.connectionMade(self)
        self.logger.msg("[connected at %s]" %
                        time.asctime(time.localtime(time.time())))

        ## database stuff
        #need to make what database you are connecting to configurable
        #self.db = database2

    def connectionLost(self, reason):
        '''Called when eve disconnects from something'''
        irc.IRCClient.connectionLost(self, reason)
        #self.config.write()
        self.logger.msg("[disconnected at %s]" %
                        time.asctime(time.localtime(time.time())))
        #self.db.update('infodb')

    # callbacks for events
    def signedOn(self):
        """Called when bot has succesfully signed on to server."""
        self.nickname = self.factory.netconfig['nicks'][0]
        for channel in self.factory.netconfig['channels']:
            self.join(channel)
        self.msg('nickserv', 'identify ' + self.factory.netconfig['password'])
        self.mode(
                self.nickname,
                True,
                'B',
                user=self.nickname
                )

    def privmsg(self, user, channel, msg):
        """This will get called when the bot receives a message."""
        if not self.irclogs[self.factory.netname].has_key(channel): 
            self.irclogs[self.factory.netname][channel] = Log(channel)

        self.irclogs[self.factory.netname][channel].msg(user.split('!')[0], msg)
            
    def action(self, user, channel, msg):
        """This will get called when the bot sees someone do an action."""
        if not self.irclogs[self.factory.netname].has_key(channel): 
            self.irclogs[self.factory.netname][channel] = Log(channel)

        self.irclogs[self.factory.netname][channel].msg(user.split('!')[0], msg,
                action=True)
        user = user.split('!', 1)[0]

    def irc_JOIN(self, prefix, params):
        '''Called when eve sees someone join a channel'''
        user = prefix
        channel = params[0]
        if not self.irclogs[self.factory.netname].has_key(channel): 
            self.irclogs[self.factory.netname][channel] = Log(channel)

        self.irclogs[self.factory.netname][channel].msg(user.split('!')[0],
                'has joined',
                action=True, special='>')

    def irc_PART(self, prefix, params):
        '''Called when eve sees someone join a channel'''
        user = prefix
        channel = params[0]
        reason = params[1] if params[1] else ''
        if not self.irclogs[self.factory.netname].has_key(channel): 
            self.irclogs[self.factory.netname][channel] = Log(channel)
        self.irclogs[self.factory.netname][channel].msg(user.split('!')[0],
                'has left (%s)' % reason,
                action=True, special='<')

    def irc_QUIT(self, prefix, params):
        '''Called when eve sees someone join a channel'''
        user = prefix
        channel = params[0]
        reason = params[1] if params[1] else 'nada'
        if not self.irclogs[self.factory.netname].has_key(channel): 
            self.irclogs[self.factory.netname][channel] = Log(channel)
        self.irclogs[self.factory.netname][channel].msg(user.split('!')[0],
                'has left (%s)' % reason,
                action=True, special='<')

    def irc_unknown(self, where, what, data):
        '''Called for messages twisted doesn't know how to handle'''
        print where, what, data
        
    def irc_KICK(self, prefix, params):
        '''Called when eve sees someone kicked from a channel (including
        himself)'''
        user = prefix
        channel = params[0]
        reason = params[2] if params[2] else 'nada'
        if not self.irclogs[self.factory.netname].has_key(channel): 
            self.irclogs[self.factory.netname][channel] = Log(channel)

        self.irclogs[self.factory.netname][channel].msg(user.split('!')[0], 
                'has kicked %s (%s)' % (params[1],reason),
                action=True, special='<')
        if params[1] == self.nickname: 
            self.channels[self.factory.netname].pop(self.channels[self.factory.netname].index(params[0]))
            self.join(params[0])
        
    def ctcpQuery_VERSION(self, user, channel, data):
        '''Called when eve recieves a CTCP VERSION request'''
        self.ctcpMakeReply(user, [('VERSION', "Imma Eve!",)])
        
class eveFactory(protocol.ClientFactory):
    """A factory for eveBots.
    A new protocol instance will be created each time we connect to the server.
    """
    # the class of the protocol to build when new connection is made
    protocol = eveBot
    instance = None
    netname = ''

    def __init__(self, net, conf):
        self.netname = net
        self.netconfig = conf

    def clientConnectionLost(self, connector, reason):
        """If we get disconnected, reconnect to server."""
        connector.connect()

    def clientConnectionFailed(self, connector, reason):
        '''Called on inital connection errors'''
        log.err("connection failed: " + reason.getErrorMessage())
        reactor.stop() 

    def buildProtocol(self, addr):
        '''wrap protocol.ClientFactory.buildProtocol to set self.instance
        (so the bot can be accessed by factory.instance)'''
        self.instance = protocol.ClientFactory.buildProtocol(self, addr)
        self.add_event_handlers()
        return self.instance

    def add_event_handlers(self):
        for key in self.event_handlers.keys():
            print key
            first = [getattr(self.instance, key)] or []
            setattr(
                    self.instance,
                    key,
                    lambda *args, **kwargs: self.call_all(first + self.event_handlers[key], args, kwargs)
                    )

    def call_all(self, funcs, args, kwargs):
        print "call_all", funcs, args, kwargs
        for func in funcs: 
            if type(func).__name__!='function':
                func(*args, **kwargs)
            else:
                func(self.instance, *args, **kwargs)


class MultiService(service.MultiService):
    '''Wrapper to load plugins once and only once, across all connections'''
    event_handlers = {}
    plugins = {}

    def __init__(self):
        service.MultiService.__init__(self)
        self.load_plugins()

    def list_plugins(self):
        '''Create a list of available plugins'''
        plugs = []
        for name in os.listdir(CONFIG['plugin_dir']):
            if name.startswith('_') or not name.endswith('.py'): 
                continue
            plugs.append(name.split('.py', 1)[0])
        return plugs

    def load_plugins(self):
        '''Load all plugins in config'''
        log.msg("Starting to load plugins")
        for name in CONFIG['plugins']:
            try:
                success = self.load_plugin(name)
                if not success:
                    raise NameError(
                        "Could not load plugin %s (No such plugin)" % name
                        )
            except BaseException as e: 
                raise Exception("Unknown error while loading %s: %s" % (name, repr(e)))

    def load_plugin(self, name):
        '''Import and add plugin by name'''
        print 'loading', name, '...'
        if name in self.list_plugins():
            plug_globals = {}
            execfile( os.path.join(CONFIG['plugin_dir'], name+'.py'),
                    plug_globals )

            for var in plug_globals.keys():
                if var.startswith('event_'):
                    event = var.split('event_',1)[1]
                    self.event_handlers.update({
                            event: 
                            self.event_handlers.get(event,[]) + [plug_globals[var]]
                            })

            return True
        else: return False

    def add_plugin(self, info):
        '''Add a plugin to the internal stack and initialize it'''
        if info.has_key('init'): 
            init = info['init']
            init(self)
        self.plugins.update({info['name']: info})

    def add_event_handlers(self):
        for conn in self.services:
            conn.args[2].event_handlers = self.event_handlers

def get_application():
    '''Starts the bot and returns a twisted application suitable for use in a .tac'''
    return start_bot(True)

def start_bot(app=False):
    '''Start the bot!'''
    # create factory protocol and application
    serv = MultiService()

    factories = []
    if not len(CONFIG['networks'].keys()):
        raise ValueError("You have not configured any networks to connect to!")
    for net in CONFIG['networks'].keys():
        network = CONFIG['networks'][net]
        factory = eveFactory(net, network)
        factories.append(factory)
        factory.service = serv
        factory.plugins = serv.plugins

        if network['ssl']: 
            internet.SSLClient(
                    network['server'],
                    network['port'],
                    factory, 
                    ssl.ClientContextFactory()
                    ).setServiceParent(serv)
        else: 
            internet.TCPClient(
                    network['server'],
                    network['port'],
                    factory
                    ).setServiceParent(serv)

    ## Init webserver
    application = service.Application("Eve Bot")
    serv.setServiceParent(application)
    serv.add_event_handlers()

    return application if app else serv.startService()

# vim: filetype=python:expandtab:shiftwidth=4:textwidth=80
