#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys, logging, traceback

sys.path.insert(0, 'lib')

import os, datetime, tweepy
import wsgiref.handlers

from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp import RequestHandler,xmpp_handlers,template
from google.appengine.api import memcache
from google.appengine.api.xmpp import *
from model import * 

VERSION="1"


CONSUMER_KEY=AppKey.getAppKey().consumer_key
CONSUMER_SECRET=AppKey.getAppKey().consumer_secret

def checklogin(method):
    def wrapper(self, *args, **kwargs):
        if not self.logged:
            kwargs['message'].reply("You are not connected on twitter, try /oauth")
        else:
            return method(self, *args, **kwargs)
    wrapper.__doc__ = method.__doc__
    return wrapper


def updatecache(method):
    def wrapper(self, *args, **kwargs):
        ret = method(self, *args, **kwargs)
        memcache.set(self.user, self)
        return ret
    wrapper.__doc__ = method.__doc__
    return wrapper

class TwSession(object):
    """twitter session"""
    def __init__(self, user):
        self.logged = False
        self.user = user
        self.followers = []
        self.following = []
        self.oauthtoken = OAuthToken.getOAuthToken(user)
        self.auth = tweepy.OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)
        logging.info(self.user)
        logging.info(self.oauthtoken.__dict__)
        if self.oauthtoken.access_token:
            self.auth.set_access_token(self.oauthtoken.access_token,self.oauthtoken.access_token_secret)
            self.logged = True
            self.twuser = self.twapi.me().screen_name
        

    @property
    def twapi(self):
        return tweepy.API(self.auth) if self.logged else tweepy.api
        
    def handle(self, message=None):
        if message.command:
            handler_name = "%s_command" %(message.command,)
            if hasattr(self, handler_name):
                handler = getattr(self, handler_name)
                if handler:
                    handler(message=message)
                    return True
        message.reply("no such command.")
        return False

    def oauth_command(self, message = None):
        """
        */oauth*
        use oauth to login """
        try:
            login_url = self.auth.get_authorization_url()
            self.oauthtoken.update_request_token(self.auth.request_token.key,self.auth.request_token.secret)
        except tweepy.TweepError:
            message.reply("Error! Failed to get request token.")
            return
        message.reply("Use this url to login.")
        message.reply(login_url)
        return 

    def t_command(self, message = None):
        """
        */t*
        alias of /timeline """
        return self.timeline_command(message = message)
    def p_command(self, message = None):
        """
        */p*
        alias of /post """
        return self.post_command(message = message)
    def ft_command(self, message = None):
        """
        */ft*
        alias of /ftimeline """
        return self.ftimeline_command(message = message)

    @checklogin
    def post_command(self, message=None):
        """
        */post message* 
        post to twitter """
        if len(message.arg)== 0:
            message.reply("require message body")
            return True
        msg = message.arg
        try:
            self.twapi.update_status(msg)
            message.reply(":) Success")
        except:
            logging.exception(message.command)
            message.reply(":( Post Error")

    @checklogin
    def followers_command(self, message=None):
        """
        */followers*
        show who are following you.  """
        try:
            self.followers = self.twapi.followers()
            rstr = "People who are following you:\n"
            for people in self.followers:
                rstr += people.name + "(" + people.screen_name + "), "
            message.reply(rstr)
        except:
            logging.exception(message.command)
            message.reply(":( Error")

    @checklogin
    def following_command(self, message=None):
        """
        */following*
        show people you are following.  """
        try:
            self.following = self.twapi.friends()

            rstr = "People you are following:\n"
            for people in self.following:
                rstr += people.name + "(" + people.screen_name + "), "
            message.reply(rstr[:-2])
        except:
            logging.exception(message.command)
            message.reply(":( Error")

    @checklogin
    def dmsg_command(self, message=None):
        """
        */dmsg friend message*
        send direct message.  """
        if len(message.arg.split()) < 2:
            message.reply("/dmsg friend message")
            return
        msg = " ".join(message.arg.split()[1:])
        friend = message.arg.split()[0]
        try:
            self.twapi.send_direct_message(friend, msg)
            message.reply(":) Message posted!")
        except:
            logging.exception(message.command)
            message.reply(":( Post error.")

    @checklogin
    def follow_command(self, message=None):
        """
        */follow username* 
        follow someone.  """
        if len(message.arg) < 1:
            message.reply("/follow username")
        try:
            self.twapi.create_friendship(message.arg)
            message.reply(":) Now you are follow " + message.arg)
        except:
            logging.exception(message.command)
            message.reply(":( Error")


    @checklogin
    def unfollow_command(self, message=None):
        """
        */unfollow username* 
        unfollow someone.  """
        if len(message.arg) < 1:
            message.reply("/unfollow username")
        try:
            self.twapi.destroy_friendship(message.arg)
            message.reply(":) Now you are not follow " + message.arg)
        except:
            logging.exception(message.command)
            message.reply(":( Error")

    @checklogin
    def timeline_command(self, message=None):
        """
        */timeline [user] [count]*
        show timeline.  """
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
            tline = self.twapi.user_timeline(user, count=count)
            for status in tline:
                rstr += (status.user.screen_name + ": " + status.text 
                + "\n----------------------------\n")
            message.reply(rstr)
        except:
            logging.exception(message.command)
            message.reply(":( Error")


    @checklogin
    def ftimeline_command(self, message=None):
        """
        */ftimeline [count]*
        show friends timeline.  """
        argc = len(message.arg.split())
        count = 20

        if argc >=1:
                try:
                    count = int(message.arg.split()[0])
                except:
                    message.reply(":( you need to pass a integer argument to count./timeline user count")
                    return

        rstr = "\n"
        try:
            tline = self.twapi.friends_timeline(count=count)
            for status in tline:
                rstr += (status.user.screen_name + ": " + status.text + 
                "\n----------------------------\n")
            message.reply(rstr)
        except:
            logging.exception(message.command)
            message.reply(":( Error")

try:
    users_list
except NameError:
    users_list = {}

class XmppHandler(xmpp_handlers.CommandHandler):
    """Handler class for all XMPP activity."""

    def text_message(self, message=None):
        self.help_command(message=message)

    def unhandled_command(self, message):
        user = message.sender
        if user.find("/") > -1:
            user = user[:user.find("/")]
        session = self.getTwSession(user)
        if session.handle(message=message):
            return
        self.help_command(message=message)

    def help_command(self, message=None):
        """
        */help*
        show usage.  """
        rstr = "\n"
        for k,v in XmppHandler.__dict__.items():
            if k.endswith("command") and k != "unhandled_command":
                rstr+= v.__doc__
                rstr+= "\n"
        for k,v in TwSession.__dict__.items():
            if k.endswith("command") and k != "unhandled_command":
                rstr+= v.__doc__
                rstr+= "\n"
        message.reply(rstr)
    
    def version_command(self, message=None):
        """
        */version*
        show version number.  """
        message.reply("tw-bot Version: %s" % (VERSION,))

    def time_command(self, message=None):
        """
        */time*
        show server time.  """
        today = datetime.datetime.now()
        message.reply(today.strftime("%H:%M:%S"))

    def date_command(self, message=None):
        """
        */date*
        show server date.  """
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

class OAuthHandler(RequestHandler):
    def Render(self, template_file, **template_values):
        path = os.path.join(os.path.dirname(__file__), 'templates', template_file)
        self.response.out.write(template.render(path, template_values))
 
    def get(self):
        oauth_token = self.request.get("oauth_token", None)
        oauth_verifier = self.request.get("oauth_verifier", None)
        if oauth_token is None:
            # Invalid request!
            self.Render("error.html", msg='Missing required parameters!')
            return
 
        # Lookup the request token
        request_token = OAuthToken.findby_request_token(oauth_token)
        if request_token is None:
            # We do not seem to have this request token, show an error.
            self.Render("error.html", msg='Missing required parameters!')
            return
 
        # Rebuild the auth handler
        auth = tweepy.OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)
        auth.set_request_token(request_token.request_token, request_token.request_token_secret)
 
        # Fetch the access token
        try:
            auth.get_access_token(oauth_verifier)
        except tweepy.TweepError, e:
            # Failed to get access token
            self.Render("error.html", msg=e)
            return
 
        request_token.update_access_token(auth.access_token.key, auth.access_token.secret)
        memcache.delete(request_token.jid)
        send_message(request_token.jid, ":) Success")
        self.Render("success.html")

class ClearCache(RequestHandler):
    def get(self):
        from google.appengine.api import memcache
        memcache.flush_all()
        print "Memcache flushed." 
        return

def application():
    application = webapp.WSGIApplication([
        ('/',Home),
        ('/index.html',Home),
        ('/index.htm',Home),
        ('/_ah/xmpp/message/chat/', XmppHandler),
        ('/oauth', OAuthHandler),
        ('/clearcache', ClearCache),
        ], debug=True)
    return application

def main():
    wsgiref.handlers.CGIHandler().run(application())


if __name__ == "__main__":
    main()

