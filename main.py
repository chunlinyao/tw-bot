#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys, logging, traceback

sys.path.insert(0, 'lib')

import os, datetime, twitter
import wsgiref.handlers

from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp import xmpp_handlers
from google.appengine.api import memcache

VERSION="1"
USAGE="""
/help usage
/version 
/time
/date
/login
/post
/followers
/following
/dmsg
/follow
/unfollow
/timeline
/ftimeline
/logout
"""

def checklogin(method):
    def wrapper(self, *args, **kwargs):
        if not self.logged:
            message.reply("You are not connected on twitter, /login username password")
        else:
            return method(self, *args, **kwargs)
    return wrapper


def updatecache(method):
    def wrapper(self, *args, **kwargs):
        ret = method(self, *args, **kwargs)
        memcache.set(self.user, self)
        return ret
    return wrapper

class TwSession(object):
    """twitter session"""
    def __init__(self, user):
        self.logged = False
        self.user = user
        self.twuser = ""
        self.twpass = ""
        self.followers = []
        self.following = []

    @property
    def twapi(self):
        return twitter.Api(self.twuser, self.twpass)
        
    def handle(self, message=None):
        if message.command:
            handler_name = "%s_command" %(message.command,)
            handler = getattr(self, handler_name)
            if handler:
                handler(message)
                return True
        return False

    def t_command(self, message = None):
        return self.timeline_command(message)
    def p_command(self, message = None):
        return self.post_command(message)
    def ft_command(self, message = None):
        return self.ftimeline_command(message)

    @updatecache
    def login_command(self, message=None):
        """user login"""
        if len(message.arg.split()) != 2:
            message.reply("/login username password\n")
            return 
        if self.logged:
            message.reply("You are already logged on twitter./disconnect fist.")
            return 
        self.twuser,self.twpass = message.arg.split()
        try:
            self.followers = self.twapi.GetFollowers()
            self.logged = True
            message.reply(":)Connected. ")
        except:
            logging.exception(message.command)
            message.reply(":( Could not connect to your twitter")

    @checklogin
    def post_command(self, message=None):
        if len(message.arg)== 0:
            message.reply("require message body")
            return True
        msg = message.arg
        try:
            self.twapi.PostUpdate(msg)
            message.reply(":) Success")
        except:
            logging.exception(message.command)
            message.reply(":( Post Error")

    @checklogin
    def followers_command(self, message=None):
        try:
            self.followers = self.twapi.GetFollowers()
            rstr = "People who are following you:\n"
            for people in self.followers:
                rstr += people.name + "(" + people.screen_name + "), "
            message.reply(rstr)
        except:
            logging.exception(message.command)
            message.reply(":( Error")

    @checklogin
    def following_command(self, message=None):
        try:
            self.following = self.twapi.GetFriends()

            rstr = "People you are following:\n"
            for people in self.following:
                rstr += people.name + "(" + people.screen_name + "), "
            message.reply(rstr[:-2])
        except:
            logging.exception(message.command)
            message.reply(":( Error")

    @checklogin
    def dmsg_command(self, message=None):
        if len(message.arg.split()) < 2:
            message.reply("/dmsg friend message")
            return
        msg = " ".join(message.arg.split()[1:])
        friend = message.arg.split()[0]
        try:
            self.twapi.PostDirectMessage(friend, msg)
            message.reply(":) Message posted!")
        except:
            logging.exception(message.command)
            message.reply(":( Post error.")

    @checklogin
    def follow_command(self, message=None):
        if len(message.arg) < 1:
            message.reply("/follow usernaame")
        try:
            self.twapi.CreateFriendship(message.arg)
            message.reply(":) Now you are follow " + message.arg)
        except:
            logging.exception(message.command)
            message.reply(":( Error")


    @checklogin
    def unfollow_command(self, message=None):
        if len(message.arg) < 1:
            message.reply("/unfollow usernaame")
        try:
            self.twapi.DestroyFriendship(message.arg)
            message.reply(":) Now you are not follow " + message.arg)
        except:
            logging.exception(message.command)
            message.reply(":( Error")

    @checklogin
    def timeline_command(self, message=None):
        argc = len(message.arg.split())
        count = 20
        user = self.twuser

        if argc >=1:
            user = message.arg.split()[0]
            if argc >=2:
                try:
                    count = int(message.arg.split()[1])
                except:
                    message.reply(":( you need to pass a integer argument to count./timeline user count")
                    return

        rstr = "\n"
        try:
            tline = self.twapi.GetUserTimeline(user, count)
            for status in tline:
                rstr += (status.user.screen_name + ": " + status.text 
                + "\n----------------------------\n")
                message.reply(rstr)
        except:
            logging.exception(message.command)
            message.reply(":( Error")


    @checklogin
    def ftimeline_command(self, message=None):
        argc = len(message.arg.split())
        count = 20
        user = self.twuser

        if argc >=1:
            user = message.arg.split()[0]
            if argc >=2:
                try:
                    count = int(message.arg.split()[1])
                except:
                    message.reply(":( you need to pass a integer argument to count./timeline user count")
                    return

        rstr = "\n"
        try:
            tline = self.twapi.GetFriendsTimeline(user, count)
            for status in tline:
                rstr += (status.user.screen_name + ": " + status.text + 
                "\n----------------------------\n")
                message.reply(rstr)
        except:
            logging.exception(message.command)
            message.reply(":( Error")

    @checklogin
    @updatecache
    def disconnect_command(self, message=None):
        del(self.twapi)
        self.logged = False
        message.reply(":) Disconnected.")
try:
    users_list
except NameError:
    users_list = {}

class XmppHandler(xmpp_handlers.CommandHandler):
    """Handler class for all XMPP activity."""

    def text_message(self, message):
        self.help_command(message)

    def unhandled_command(self, message):
        user = message.sender
        session = self.getTwSession(user)
        if session.handle(message):
            return
        self.help_command(message)

    def help_command(self, message=None):
        """Handles /help requests, Show usage."""
        message.reply(USAGE)
    
    def version_command(self, message=None):
        message.reply("tw-bot Version: %s" % (VERSION,))

    def time_command(self, message=None):
        today = datetime.datetime.now()
        message.reply(today.strftime("%H:%M:%S"))

    def date_command(self, message=None):
        today = datetime.datetime.now()
        message.reply(today.ctime())

    def getTwSession(self, user):
        twsession = None
        if not users_list.has_key(user):
            #load from memcache
            twsession = memcache.get(user)
            if twsession is None:
                if not user == None:
                    twsession = TwSession(user)
                    memcache.set(user, twsession)
            users_list[user]=twsession
        else:
            twsession = users_list[user]
        return twsession



class Home(webapp.RequestHandler):
    def Render(self, template_file, template_values):
        path = os.path.join(os.path.dirname(__file__), 'templates', template_file)
        self.response.out.write(template.render(path, template_values))

    def get(self):
        self.Render("home.html", None)


def main():
    application = webapp.WSGIApplication([
        ('/',Home),
        ('/index.html',Home),
        ('/index.htm',Home),
        ('/_ah/xmpp/message/chat/', XmppHandler)
        ], debug=True)

    wsgiref.handlers.CGIHandler().run(application)


if __name__ == "__main__":
    main()

