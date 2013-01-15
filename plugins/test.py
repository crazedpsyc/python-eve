
def event_privmsg(bot, user, channel, message):
    print bot, user, channel, message
    if message == 'HI':
        bot.msg(channel, "Hello %s!" % user.split('!')[0])
