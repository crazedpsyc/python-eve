from eve import *

plugins([
    'test',
])

add_network(
    'Freenode',
    server='irc.freenode.net',
    channels=['#duckduckgo'],
    nicks=['Eve|test'],
    password='nickserv_password',
    port=6697,
    ssl=True,
)

start()
