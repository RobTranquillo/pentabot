# -*- coding: utf-8 -*-

from jabberbot import botcmd
import feedparser
import datetime
import time
import urllib
import os, sys
import json
import requests
import logging

import socket
import subprocess
import fcntl
import errno

from decorators import ignore_msg_from_self
from pentabot import feed_help, config
from gen_topic import get_topic
from gen_kickreason import get_kickreason

### ### ###

IS_PYTHON2 = sys.version_info < (3, 0)

if IS_PYTHON2:
    QUIT_CMD = '{"command": ["quit"]}\n'
    MEDIA_TITLE = '{"command": ["get_property_string", "media-title"]}\n'
else:
    QUIT_CMD = b'{"command": ["quit"]}\n'
    MEDIA_TITLE = b'{"command": ["get_property_string", "media-title"]}\n'

class Mpv:
    def __init__(self, host):
        self.host = host
        self.socket_path = "/tmp/mpv-" + host
        self.child = None
    def play(self, uri):
        self.stop()
        cmd = ["mpv",
                "--ao", "pulse:"+self.host,
                "--no-config",
                "--input-unix-socket="+self.socket_path,
                "--", uri]
        self.child = subprocess.Popen(cmd)
    def connect(self):
        client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        client.connect(self.socket_path)
        return client
    def flush_socket(self, sock):
        try:
            fcntl.fcntl(sock, fcntl.F_SETFL, os.O_NONBLOCK)
            sock.recv(4096)
            fcntl.fcntl(sock, fcntl.F_SETFL, 0)
        except socket.error as e:
            if e != errno.EAGAIN or e != errno.EWOULDBLOCK:
                return "Connection failed while retrieving current song: %s" % e
    def media_title(self):
        if os.path.exists(self.socket_path):
            try:
                client = self.connect()
                self.flush_socket(client) # flush events
                client.send(MEDIA_TITLE)
                f = client.makefile("r")
                line = f.readline()
            except socket.error as e:
                return "Connection failed while retrieving current song: %s" % e
            try:
                response = json.loads(line)
                title = response.get("data", "N/A")
                return "current song: %s" % title
            except ValueError as e:
                return "failed to parse response of mpv: %s" % e
        else:
            return "no mpv running"
    def stop(self):
        if self.child != None:
            self.child.kill()
            self.child.wait()
            self.child = None
        if os.path.exists(self.socket_path):
            try:
                client = self.connect()
                client.send(QUIT_CMD)
                client.close()
            except socket.error as e:
                return "already stopped or error while sending quit: %s" % e
            finally:
                try:
                    os.remove(self.socket_path)
                except OSError:
                    pass
        else:
            return "no mpv running"

mpv_cider = Mpv("cider.hq.c3d2.de")



@botcmd
@ignore_msg_from_self
def news(self, mess, args):
  """
  insert/read pentanews for the upcoming pentaradio show
  """
  scriptpath = os.path.dirname( os.path.realpath(__file__) )
  newsDatabase = scriptpath + "/pentanewsdb/"

  def getNews(month):
    if month == 0:
      return False
    newsfile = newsDatabase + month + '.news'
    if not os.path.isfile(newsfile):
      return "month not found\n"
    f = open(newsfile, 'r')
    news = f.read()
    return news

  def putNews(news):
    thismonth = datetime.date.today().strftime('%Y-%m')
    newsfile = newsDatabase + thismonth + '.news'
    try:
      f = open(newsfile, 'a')
      f.write(news)
      f.close()
      return "news are written"
    except (OSError, IOError) as e:
      return "Upps: " + e


  args = args.split(" ")
  if args[0].upper() == 'HELP':
    return "Usage: write '+news GET' or '+news' to get the news of the actual month. Write '+news GET 2017-03' to get a specific month. Or write '+news PUT https://hotsh.it thats hot shit!!' to add a news to the database"

  if args[0].upper() == 'GET' or args[0] == '':
    if len(args) > 1:
      month = args[1]
      if len(args[1]) == 7:
        return( getNews(month) )
      else:
        return 'choose a month with a string link: GET 2017-01'
    else:
        thismonth = datetime.date.today().strftime('%Y-%m')
        return "news of the month: \n" + getNews(thismonth)

  if args[0].upper() == 'PUT':
    if len(args) > 1:
      charlimit = 2048
      news = str( " ".join( args[1:][0:charlimit] ))
      news = news.strip("\n") + "\n"
      news = datetime.date.today().strftime('%d.%m.%Y') + ": " + news
      if len(news) > 4:
        return putNews(news)

### ### ###

@botcmd
@ignore_msg_from_self
def cider_play(self, mess, args):
    return mpv_cider.play(args.strip())

@botcmd
@ignore_msg_from_self
def cider_stop(self, mess, args):
    return mpv_cider.stop()

@botcmd
@ignore_msg_from_self
def cider_playlist(self, message, args):
    """
    show current bot mpv playlist
    """
    return mpv_cider.media_title()

### ### ###

@botcmd
@ignore_msg_from_self
def playlist(self, mess, args):
    """
    show current bot mpv playlist
    """
    playlist = ''
    try:
        playlist += os.popen('/home/pentabot/shell/mpv_current.sh').read()
        playlist += os.popen('/bin/cat /tmp/mpv_current.log').read()
    except:
        playlist += 'something goes wrong'
    return ('Current HQ Pentabot Playlist:\n' + playlist)

### ### ###

def format_help(fun):
    fun.__doc__ = fun.__doc__.format(**feed_help) #** dict entpacken, * listen entpacken
    return fun

def _stroflatlog_de(latitude, longitude):
    """
    helper for latitude longitude to german
    """
    southnorth = ("nördlicher","südlicher")[int(latitude < 0)]
    snshort = ("N", "S")[int(latitude < 0)]
    eastwest = ("östlicher","westlicher")[int(longitude < 0 )]
    ewshort = ("E", "W")[int(longitude<0)]
    return "%f %s Breite und %f %s Länge { %f°%s %f°%s }" % (abs(latitude), southnorth, abs(longitude), eastwest, abs(latitude), snshort, abs(longitude), ewshort)

@botcmd
@ignore_msg_from_self
def thetime(self, mess, args):
    """
    Zeige die aktuelle Server Zeit
    """
    return str(datetime.datetime.now())

@botcmd
@ignore_msg_from_self
def gentopic(self,mess,args):
    """
    Generiert einen Vorschlag für ein Gesprächsthema
    """
    return 'Wie wärs mit „%s“'%get_topic()


@botcmd
@ignore_msg_from_self
def rot13(self, mess, args):
    """
    Gibt <string> in rot13
    """
    return args.encode('rot13')


@botcmd
@ignore_msg_from_self
def whoami(self, mess, args):
    """
    Zeigt dir dein Username
    """
    if mess.getType() == "groupchat":
        return str(mess.getFrom()).split("/")[1]
    else:
        return mess.getFrom().getStripped()

### ### ###

@botcmd
@ignore_msg_from_self
def serverinfo(self, mess, args):
    """
    Zeige Informationen ueber den Server
    """
    serverinfo = ''
    try:
        serverinfo += os.popen('/bin/uname -a').read()
        serverinfo += os.popen('/usr/bin/uptime').read()
        serverinfo += os.popen('ps -eo pid,comm,lstart,etime,time,args | grep pentabot | egrep -v "ps|grep|ssh|sendmail"').read()
    except:
        serverinfo += 'Sorry Dude'
    return ('Info: (auf flatbert)\n' + serverinfo)

@botcmd
@ignore_msg_from_self
def ping6cider(self, mess, args):
    """
    Zeige Informationen ueber den Server - cider.hq.c3d2.de
    """
    ping6cider = ''
    try:
        ping6cider += os.popen('/sbin/ping6 -c4 cider.hq.c3d2.de  | /usr/bin/tail -2').read()
    except:
        ping6cider += 'Sorry Dude'
    return ('Info:\n' + ping6cider)

@botcmd
@ignore_msg_from_self
def ping6flatbert(self, mess, args):
    """
    Zeige Informationen ueber den Server - flatbert.hq.c3d2.de
    """
    ping6flatbert = ''
    try:
        ping6flatbert += os.popen('/sbin/ping6 -c4 flatbert.hq.c3d2.de  | /usr/bin/tail -2').read()
    except:
        ping6flatbert += 'Sorry Dude'
    return ('Info:\n' + ping6flatbert)

@botcmd
@ignore_msg_from_self
def ping6flatberthost(self, mess, args):
    """
    Zeige Informationen ueber den Server - flatberthost.hq.c3d2.de
    """
    ping6flatberthost = ''
    try:
        ping6flatberthost += os.popen('/sbin/ping6 -c4 flatberthost.hq.c3d2.de  | /usr/bin/tail -2').read()
    except:
        ping6flatberthost += 'Sorry Dude'
    return ('Info:\n' + ping6flatberthost)

@botcmd
@ignore_msg_from_self
def ping6beere(self, mess, args):
    """
    Zeige Informationen ueber den Server - beere.hq.c3d2.de
    """
    ping6beere = ''
    try:
        ping6beere += os.popen('/sbin/ping6 -c4 beere.hq.c3d2.de  | /usr/bin/tail -2').read()
    except:
        ping6beere += 'Sorry Dude'
    return ('Info:\n' + ping6beere)

@botcmd
@ignore_msg_from_self
def ping6ledbeere(self, mess, args):
    """
    Zeige Informationen ueber den Server - ledbeere.hq.c3d2.de
    """
    ping6ledbeere = ''
    try:
        ping6ledbeere += os.popen('/sbin/ping6 -c4 ledbeere.hq.c3d2.de  | /usr/bin/tail -2').read()
    except:
        ping6ledbeere += 'Sorry Dude'
    return ('Info:\n' + ping6ledbeere)

@botcmd
@ignore_msg_from_self
def ping6chaosbay(self, mess, args):
    """
    Zeige Informationen ueber den Server - chaosbay.hq.c3d2.de
    """
    ping6chaosbay = ''
    try:
        ping6chaosbay += os.popen('/sbin/ping6 -c4 chaosbay.hq.c3d2.de  | /usr/bin/tail -2').read()
    except:
        ping6chaosbay += 'Sorry Dude'
    return ('Info:\n' + ping6chaosbay)

@botcmd
@ignore_msg_from_self
def ping6knot(self, mess, args):
    """
    Zeige Informationen ueber den Server - knot.hq.c3d2.de
    """
    ping6knot = ''
    try:
        ping6knot += os.popen('/sbin/ping6 -c4 knot.hq.c3d2.de  | /usr/bin/tail -2').read()
    except:
        ping6knot += 'Sorry Dude'
    return ('Info:\n' + ping6knot)

@botcmd
@ignore_msg_from_self
def flatbert(self, mess, args):
    """
    Server Test
    """
    flatbert = ''
    try:
        flatbert += os.popen('/home/freebot/pentabot/shell/hq-check-flatbert.sh').read()
    except:
        flatbert += 'Sorry Dude'
    return ('Info:\n' + flatbert)

### ### ###

@botcmd
@ignore_msg_from_self
def test_spaceapi(self, mess, args):
    """
    SpaceAPI WebServer Test
    """
    test_spaceapi = ''
    try:
        test_spaceapi += os.popen("/usr/bin/curl -m3 -I http://www.hq.c3d2.de/spaceapi.json 2>&1 | grep 'HTTP/'").read()
    except:
        test_spaceapi += 'Sorry Dude'
    return ('Info:\n' + test_spaceapi)


### ### ### ### ### ### ### ### ###

@botcmd
@ignore_msg_from_self
def check_wetu(self, mess, args):
    """
    Wetu Server Test
    """
    check_wetu = ''
    try:
        check_wetu += os.popen('/home/pentabot/shell/check_wetu.sh').read()
        check_wetu += os.popen('/bin/cat /tmp/pentabot_check_wetu2.log').read()
    except:
        check_wetu += 'Sorry Dude'
    return ('' + check_wetu)


### ### ###

@botcmd
@ignore_msg_from_self
def randompassword(self, mess, args):
    """
    Ein Passwoertchen fuer die Welt
    """
    randompassword = ''
    try:
        randompassword += os.popen('/usr/bin/openssl rand -base64 20 | /usr/bin/cut -c1-20').read()
    except:
        randompassword += 'Sorry Dude'
    return ('Ein Passwoertchen fuer die Welt: mit OpenSSL Random Password Generator:\n' + randompassword)

@botcmd
@ignore_msg_from_self
def zufall100(self, mess, args):
    """
    Zufall in 100
    """
    zufall100 = ''
    try:
        zufall100 += os.popen('/home/freebot/pentabot/shell/zufall_100.sh').read()
    except:
        zufall100 += 'Sorry Dude'
    return ('Zufall 1-100 sagt:\n' + zufall100)

### ### ###

@botcmd
@ignore_msg_from_self
def dn42(self, mess, args):
    """
    dn42 address space
    """
    return 'http://172.22.99.76:8000/index.html'

### ### ###

@botcmd
@ignore_msg_from_self
def gedichte(self, mess, args):
    """
    gedichte Cookie for you

    A Cookie you can trust and accept.
    Just run gedichte
    """
    gedichte = ''
    try:
        #gedichte += os.popen('/basejail/usr/games/fortune /usr/share/games/fortune/gedichte').read()
        gedichte += os.popen('/usr/share/zsh/functions/Completion/Unix/_fortune /usr/share/games/fortune/gedichte').read()
    except:
        gedichte += 'Your gedichte unforseeable'
    return ('Your Cookie reads:\n' + gedichte)

@botcmd
@ignore_msg_from_self
def weihnachtsgedichte(self, mess, args):
    """
    weihnachtsgedichte Cookie for you

    A Cookie you can trust and accept.
    Just run weihnachtsgedichte
    """
    weihnachtsgedichte = ''
    try:
        weihnachtsgedichte += os.popen('/basejail/usr/games/fortune /usr/share/games/fortune/weihnachtsgedichte').read()
    except:
        weihnachtsgedichte += 'Your weihnachtsgedichte unforseeable'
    return ('Your Cookie reads:\n' + weihnachtsgedichte)

@botcmd
@ignore_msg_from_self
def fortune(self, mess, args):
    """
    Fortune Cookie for you

    A Cookie you can trust and accept.
    Just run fortune
    """
    fortune = ''
    try:
        fortune += os.popen('/basejail/usr/games/fortune /usr/share/games/fortune/000').read()
    except:
        fortune += 'Your fortune unforseeable'
    return ('Your Cookie reads:\n' + fortune)

@botcmd
@ignore_msg_from_self
def cowgedichte(self, mess, args):
    """
    cowGedichte Cookie for you

    A Cookie you can trust and accept.
    Just run cowgedichte
    """
    cowgedichte = ''
    try:
        cowgedichte += os.popen('/basejail/usr/games/fortune /usr/share/games/fortune/gedichte | /usr/local/bin/cowsay').read()
    except:
        cowgedichte += 'Your cowgedichte unforseeable'
    return ('Your Cookie reads:\n' + cowgedichte)

@botcmd
@ignore_msg_from_self
def cowfortune(self, mess, args):
    """
    cowFortune Cookie for you

    A Cookie you can trust and accept.
    Just run cowfortune
    """
    cowfortune = ''
    try:
        cowfortune += os.popen('/usr/games/fortune /usr/share/games/fortune/fortune | /usr/local/bin/cowsay').read()
    except:
        cowfortune += 'Your cowfortune unforseeable'
    return ('Your Cookie reads:\n' + cowfortune)

### ### ###

@botcmd
@ignore_msg_from_self
def ddate(self, mess, args):
    """
    Perpetual date converter from gregorian to poee calendar
    """
    args = args.strip().split(' ')
    ddate = ''
    if len(args) <= 1 :
        ddate += os.popen('/usr/local/bin/ddate').read()
    elif len(args) == 3 and all(arg.isdigit() for arg in args):
        ddate += os.popen('/usr/local/bin/ddate ' + args[0] + ' ' + args[1] + ' ' + args[2]).read()
    else:
        ddate = 'You are not using correctly!\n Just enter ddate or append day month year'
    return ddate

### ### ###

@format_help
@botcmd
@ignore_msg_from_self
def last(self, mess, args):
    """
    Zeigt neuste Meldungen verschiedener Portale an.
    Benutzung: +last <Quelle> [Anzahl]
    Quellen:  {lastrss}
    """
    args = args.strip().split(' ')
    if args[0] in dict(config.items('RSS')).keys():
        message = "\n"
        if len(args) == 1:
            args.append('1')
        if int(args[1]) > int(config.get('RSS', "maxfeeds")):
            args[1] = config.get('RSS', "maxfeeds")
        for loop in range(int(args[1])):
            f = feedparser.parse(config.get('RSS', args[0])).get('entries')[loop]
            message += 'Titel: ' + f.get('title') + '\n' + 'URL: ' + f.get('link') + '\n'
    else:
        message = 'Bitte rufe \"help last\" fuer moegliche Optionen auf!'
    return message

### ### ###

@format_help
@botcmd
@ignore_msg_from_self
def mensa(self, mess, args):
    """
    Gibt die aktuellen Leckereien wieder
    Moegliche Eingaben:
    {lastrssmensa}
    """
    args = args.strip().split(' ')
    if args[0] in dict(config.items('RSSMENSA')).keys():
        message = "\n"
        if len(args) == 1:
            args.append('1')
        if int(args[1]) > int(config.get('RSSMENSA', "maxfeedsmensa")):
            args[1] = config.get('RSSMENSA', "maxfeedsmensa")
        for loop in range(int(args[1])):
            f = feedparser.parse(config.get('RSSMENSA', args[0])).get('entries')[loop]
            message += 'Titel: ' + f.get('title') + '\n' + 'URL: ' + f.get('link') + '\n'
            f = feedparser.parse(config.get('RSSMENSA', args[0])).get('entries')[1]
            message += 'Titel: ' + f.get('title') + '\n' + 'URL: ' + f.get('link') + '\n'
            f = feedparser.parse(config.get('RSSMENSA', args[0])).get('entries')[2]
            message += 'Titel: ' + f.get('title') + '\n' + 'URL: ' + f.get('link') + '\n'
    else:
        message = 'Bitte rufe \"help mensa\" fuer moegliche Optionen auf!'
    return message

### ### ###

@format_help
@botcmd
@ignore_msg_from_self
def github(self, mess, args):
    """
    Gibt die aktuellen GitHub Aktivitäten wieder
    Moegliche Eingaben:
    {lastrssgithub}
    """
    args = args.strip().split(' ')
    if args[0] in dict(config.items('RSSGITHUB')).keys():
        message = "\n"
        if len(args) == 1:
            args.append('1')
        if int(args[1]) > int(config.get('RSSGITHUB', "maxfeedsgithub")):
            args[1] = config.get('RSSGITHUB', "maxfeedsgithub")
        for loop in range(int(args[1])):
            f = feedparser.parse(config.get('RSSGITHUB', args[0])).get('entries')[loop]
            message += 'Titel: ' + f.get('title') + '\n' + f.get('updated') + '\n' + 'URL: ' + f.get('link') + '\n'
    else:
        message = 'Bitte rufe \"help github\" fuer moegliche Optionen auf!'
    return message

### ### ###

@botcmd
@ignore_msg_from_self
def elbe(self, mess, args):
    """
    aktueller elbpegel
    """
    message = ""
    url = config.get("elbe", "url")
    params = dict(
        includeTimeseries='false',
        includeCurrentMeasurement='true',
        waters='ELBE'
        )

    data = requests.get(url=url)
    content = json.loads(data.content)
    pegel = content.get('value')

    message += 'Pegelstand: %d cm' % pegel
    return message

### ### ###

@botcmd
@ignore_msg_from_self
def abfahrt(self, mess, args):
    """
    DVB Abfahrtsmonitor
    Benutze: abfahrt <Haltestellenname>
    """
    args = args.strip().split(' ')
    if len(args) < 1:
        abfahrt = "Benutze: abfahrt <Haltestellenname>"
    else:
        abfahrt = ""
        if len(args) == 1:
            laufzeit = config.get("abfahrt", "laufzeit")
            haltestelle = args[0]
            if len(haltestelle) < 3:
              haltestelle = config.get("abfahrt", "default_station")
        else:
            if args[-1].isdigit():
                laufzeit = args[-1]
                haltestelle = " ".join(args[0:-1])
            else:
                laufzeit = config.get("abfahrt", "laufzeit")
                haltestelle = " ".join(args[0:])

        values = {"ort": "Dresden",
                    "hst": haltestelle,
                    "vz": laufzeit,
                    "timestamp": int(time.time())}

        # fix unicode issues of urlencode
        encoded_values = {}
        for key, value in values.iteritems():
            encoded_values[key] = unicode(value).encode('utf-8')
        url_values = urllib.urlencode(encoded_values)

        full_url = config.get("abfahrt", "abf_url") + "?" + url_values
        data = requests.get(url=full_url)

        if json.loads(data.content):
            abfahrt += "\nHaltestelle: " + haltestelle + full_url
            abfahrt += "\n%6s %-19s %7s\n" % ("Linie", "Richtung", "Abfahrt")

            for line in json.loads(data.content):
                abfahrt += "%6s %-19s %7s\n" % (line[0], line[1], line[2])

        else:
            hst_url = config.get("abfahrt", "hst_url") + "?" + url_values
            data = requests.get(url=hst_url)

            if json.loads(data.content)[1]:
                abfahrt += "Such dir eine aus:\n"
                i = 0

                for line in json.loads(data.content)[1]:
                    i = i + 1
                    if i <= 10:
                        abfahrt += "* %s\n" % line[0]
                    else:
                        abfahrt += "und viele mehr..."
                        break

    return abfahrt

### ### ###

def hqStatus(flag):
  if(flag == "off" or flag == "on"):
      f = open("hq-state.switch","w")
      f.seek(0)
      f.write(flag)
      f.close()

  if(flag == 'get'):
    f = open('hq-state.switch','r')
    f.seek(0)
    message = "current HQ status: " + f.read(10)
    f.close()
    return message



@botcmd
@ignore_msg_from_self
def hq(self, mess, args):
    """
    Information die ueber http://www.hq.c3d2.de/spaceapi.json auszulesen sind
    """

    url = config.get("hq", "url")
    data = requests.get(url=url)
    content = json.loads(data.content)

    message = ""
    contact_help_msg = "        all         Zeigt dir alle Daten\n"
    contact_help_msg += "        phone       Zeigt dir die Festnetz Nummer unter der wir erreichbar sind\n"
    contact_help_msg += "        twitter     Zeigt dir das Voegelchen unter dem wir schreiben oder erreichbar sind\n"
    contact_help_msg += "        jabber      Zeigt dir die den MUC unter der wir erreichbar sind\n"
    contact_help_msg += "        irc         Zeigt dir wie du uns im IRC erreichen kannst\n"
    contact_help_msg += "        ml          Zeigt dir auf welcher Mailingliste du uns erreichen kannst\n"
    feeds_help_msg = "        blog         Zeigt dir die C3D2-Mews-Feed-URL an\n"
    feeds_help_msg += "        wiki          Zeigt dir die C3D2-Wiki-Feed-URL an\n"
    feeds_help_msg += "        calendar   Zeigt dir die C3D2-Kalender-Feed-URL an\n"
#    sensors_help_msg = "       pi         Zeigt die Temperatur von " + content.get("sensors").get("temperature")[0].get("name") + "\n"
    help_msg = "Benutze: hq <option> (<option>)\n"
    help_msg += "Optionen:\n"
#    help_msg += "    status          Zeigt dir den Status (offen/zu) vom HQ\n"
    help_msg += "    status          Zeigt den Status des HQ an (+hq status | +hq status on | +hq status off)\n"
    help_msg += "    coords          Zeigt dir die Koordinaten des HQ\n"
    help_msg += "    sensors         Zeigt die Werte der Sensoren im HQ\n"
#    help_msg += sensors_help_msg
    help_msg += "    contact         Zeigt dir Kontakt Daten zum HQ\n"
    help_msg += contact_help_msg
    help_msg += "    web             Zeigt dir den Link zu unserer Webseite\n"
    help_msg += "    feeds           Zeigt dir die Newsfeeds des C3D2\n"
    help_msg += feeds_help_msg

    args = args.strip().split(' ')

    if not args[0]:
        message = help_msg

#    elif args[0] == "status_TEMP_DEAKTIVERT_BIS_SCHALTER_WIEDER_GEHT":
#                     die auskommentiert help msg wieder reinnehmen
##        message += content.get("state").get("message")
##        message += "   " + "UTC/GMT+1" + "   "  + str(datetime.datetime.now())
##        message += content.get("state").get("message") + "            " + "LASTCHANGE" + "   "  +str(content.get("state").get("lastchange"))
#        message += content.get("state").get("message") + "            " + "LASTCHANGE" + "   "  +datetime.datetime.fromtimestamp(int(content.get("state").get("lastchange"))).strftime('%Y-%m-%d %H:%M:%S')
    elif args[0] == "status":
       if len(args) == 2:
          if args[1] == "on":
            hqStatus("on")
          if args[1] == "off":
            hqStatus("off")
       message += hqStatus("get")

    elif args[0] == "coords":
        message += "Das HQ findest du auf %s "%(_stroflatlog_de(content.get("location").get("lat") , content.get("location").get("lon")))
        message += "oder hier: https://www.openstreetmap.org/way/372193022"
    elif args[0] == "web":
        message += "Der Chaos Computer Club Dresden (C3D2) ist im Web erreichbar unter " + content.get("url") + " ."
    elif args[0] == "sensors":
        if len(args) == 1:
            message += "Du kannst waehlen zwischen:\n"
            message += sensors_help_msg
        elif args[1] == "pi":
            message += content.get("sensors").get("temperature")[0].get("location") + " (" + content.get("sensors").get("temperature")[0].get("name") + "): " + str(content.get("sensors").get("temperature")[0].get("value")) + content.get("sensors").get("temperature")[0].get("unit")
        else:
            message += "Probier es noch mal mit einer der folgenden Optionen: [aktuell nur] pi"
    elif args[0] == "contact":
        if len(args) == 1:
            message = "Du kannst waehlen zwischen:\n"
            message += contact_help_msg
        elif args[1] == "all":
            message += "Du kannst uns unter dieser Festnetznummer erreichen: +" + content.get("contact").get("phone") + " .\n"
            message += "Wir sind auf Twitter unter: https://twitter.com/" + content.get("contact").get("twitter") + " zu finden.\n"
            message += "Im IRC findest du uns hier: " + content.get("contact").get("irc") + "\n"
            message += "Im Jabber vom C3D2 findest du uns im Raum " + content.get("contact").get("jabber") + " .\n"
            message += "Falls du uns auf der Mailingliste folgen willst meld dich einfach hier an: " + content.get("contact").get("ml") + "\n"
        elif args[1] == "phone":
            message += "Du kannst uns unter dieser Festnetznummer erreichen: +" + content.get("contact").get("phone") + " ."
        elif args[1] == "twitter":
            message += "Wir sind auf Twitter unter: https://twitter.com/" + content.get("contact").get("twitter") + " zu finden."
        elif args[1] == "irc":
            message += "Im IRC findest du uns hier: " + content.get("contact").get("irc")
        elif args[1] == "jabber":
            message += "Im Jabber vom C3D2 findest du uns im Raum " + content.get("contact").get("jabber") + " ."
        elif args[1] == "ml":
            message += "Falls du uns auf der Mailingliste folgen willst meld dich einfach hier an: " + content.get("contact").get("ml")
        else:
            message += "Probier es noch mal mit einer der folgenden Optionen: all, phone, twitter, jabber, irc oder ml."
    elif args[0] == "feeds":
        if len(args) == 1:
            message += "Du kannst waehlen zwischen:\n"
            message += feeds_help_msg
        elif args[1] == "blog":
            message += "Den Atom-Feed zu den C3D2 News findest du hier: " + content.get("feeds").get("blog").get("url")
        elif args[1] == "wiki":
            message += "Den Atom-Feed zum C3D2-Wiki News findest du hier: " + content.get("feeds").get("wiki").get("url")
        elif args[1] == "calendar":
            message += "Den iCal-Feed vom C3D2 findest du hier: " + content.get("feeds").get("calendar").get("url")

        else:
            message += "Probier es noch mal mit einer der folgenden Optionen: blog, wiki oder calendar."
    else:
        message += "Probier es noch mal mit einer der folgenden Optionen: status, sensors, coords, contact, web oder feeds."
    return message

@botcmd
@ignore_msg_from_self
def cloudstorage(self, mess, args):
    """
    :D
    """
    cloudstorage = ''
    try:
        cloudstorage += os.popen("/home/pentabot/shell/df.sh").read()

    except:
        cloudstorage += 'Sorry Dude'
    return ('Ihnen steht noch folgender Speicherplatz in der Uga Uga NSA Cloud zur Verfuegung\n' + cloudstorage)

@botcmd
@ignore_msg_from_self
def pentabot(self, mess, args):
    """
    :D
    """
    pentabot = ''
    try:
        pentabot += os.popen('echo "Früher hatte ich Elan. Heute habe ich Wlan. Ist auch okay!"').read()
    except:
        pentabot += 'Sorry Dude'
    return ('Info:\n' + pentabot)


# EOF
