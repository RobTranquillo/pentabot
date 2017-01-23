# Pentabot

## Requirements:

- python-jabberbot
- python-xmpp
- python-feedparser
- python-requests
- python-dnspython

## Example credentials

```
# .pentabot.login
[pentaBotSecret]
username=<jabberid>
password=<password>
resource=<ressourcename>
debug=True
```

a stylish xmpp-based bot serving pentamedia with your data and pentamedia data for you.

First of all, it shall be able to receive news for our monthly pentaradio show (supposed format: "!add <url> <your text> <#yourtag>").

Later features commands like "+last #[radio|cast|music]" could serve you with the latest links available. Try "+help last" for more info.

Comments (for registered users) could be added as well.

Also stats could be offered: "!stats $showname"

But first of all: News adding. Because via pentasubmitter, it's a pain in the arse.
Hopefully this will be done by the end of the weekend.

The bot will be (hopefully) available soon, just make friends with pentabot@hq.c3d2.de

For comments (either mail or xmpp): koeart <at - remove this> zwoelfelf <dot - this too> net.
