import eve_blackmagic
import os
from twisted.internet import reactor

__all__ = ['start']

conf = {
        'plugins': [],
        'plugin_dir': os.path.join(os.getcwd(), 'plugins'),
        'networks': {},
        }

for setting in conf.keys():
    globals().update({
        setting: eval("lambda value: conf.update({setting: value})", {'setting': setting, 'conf': conf})
        })

    if type(conf[setting]) == dict and setting.endswith('s'):
        globals().update({
            'add_'+setting[:-1]: 
            eval("lambda name, **data: conf[setting].update({name: data})", {'setting': setting, 'conf': conf})
        })
        __all__.append('add_'+setting[:-1])

    __all__.append(setting)


def start():
    eve_blackmagic.set_config(conf)
    eve_blackmagic.start_bot()
    reactor.run()
