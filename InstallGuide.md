# tw-bot项目介绍 #
> 自己看具有鲜明中国特色并带有敏感词的项目主页

# 准备工作 #
> 你需要拥有Google App Engine的开发账号（如何申请，自己去问google）。安装python（为兼容现在（2009.11）的GAppEng SDK，2.4<版本<3.0）和Google App Engine SDK for Python。
> 需要说明的是那个SDupload工具对这个项目不好使，不要再走弯路。
## Python自己下载安装 ##
## 安装Google App Engine SDK for Python ##
> [Google App Engine SDK](http://code.google.com/appengine/downloads.html)，安装完之后看看路径中有没有它，如没有，则用appcfg.py的时候还要用绝对路径名，如：C:\Program Files\Google\google\_appengine\appcfg.py
## 安装Mercurial ##
> 本项目没有提供下载，只能用该SCM工具下载代码
## 下载项目源代码 ##
> 看这里[Source Code](http://code.google.com/p/tw-bot/source/checkout)
# 搭建过程 #
  1. 登录你的Google App Engine的开发账号后创建一个新应用，名字自己起。起完名字后要修改文件app.yaml，main.py，把其中的“tw-bot”替换成你的应用名字
  1. 用appcfg.py上传代码，your\_application\_directoy是你存放修改好的tw-bot的地方。appcfg.py update your\_application\_directoy，上传完后就可以用浏览器试一下访问http://your_app_name.appspot.com
  1. 注册twitter的appliction，需要有twitter账号（有免翻墙注册方法，自己去google）。在twitter.com/oauth\_clients上申请（需翻墙）。需要注意，选择Application Type为Browser，填写Callback URL为http://your\_app\_name.appspot.com/oauth，注册后获得Consumer key和Consumer secret，把这两个字符串填入appkey.csv（按照该文件中的位置）并保存
  1. 上传数据文件，建立datastore（参见作者的blog，现抄录在末尾）
  1. 检查你的应用是否ready，登录[App Engine](https://appengine.google.com)，选择你的应用。查看一下Appkey表里有没有你上传的appkey.csv文件里的内容，Appkey表最好只有一条数据（Datastore->DataView）。运行时有无错误（Main->Dashboard->Errors或Main->Logs）
  1. 使用Gtalk、pidign或miranda等支持jabber的客户端登录你的Gtalk账号，invite your\_app\_name@appspot.com。等它上线后向它发指令绑定你的twitter账号。/oauth需翻墙，具有中国特色的/oauthchina需要twitter账号和密码（本软件不记录任何账号信息）
  1. OK，enjoy twitter

```
GAE现在有批量上传和下载数据的方法。最近试用了一下上传数据的方法。调用时要写一个配置文件，使用appcfg update_data命令上传。

修改app.yaml打开remote_api。在app.yaml中添加如下代码:

handlers:
- url: /remote_api
  script: $PYTHON_LIB/google/appengine/ext/remote_api/handler.py
  login: admin
需要上传的数据的Model定义如下model.py:

#!/usr/bin/env python
# -*- coding: utf-8 -*-

from google.appengine.ext import db
from google.appengine.api import memcache

class AppKey(db.Model):
    """Consumer key and secret."""

    consumer_key = db.StringProperty()
    consumer_secret = db.StringProperty()
给上面的Model写一个Loaderappkeyloader.py:

from google.appengine.tools import bulkloader
from model import AppKey

class AppKeyLoader(bulkloader.Loader):
  def __init__(self):
    bulkloader.Loader.__init__(self, 'AppKey',
                               [('consumer_key', str),
                                ('consumer_secret', str),
                               ])
loaders = [AppKeyLoader]
准备CSV文件appkey.csv

consumer_key,consumer_secret
执行命令

C:\work> set PYTHONPATH=.
C:\work> appcfg upload_data --config_file=appkeyloader.py --filename=appkey.csv 
--kind=AppKey --url=http://localhost:8080/remote_api .
```
注意事项：上传时把“--url=http://localhost:8080/remote_api”去掉

Tips:如果你想更快的更新twitter，可以把cron.yaml里面的时间改小，最小是1分钟，好象是google的限制

Gtalk相对其他twitter客户端的优点是使用ssl。twitter本身没有用ssl，很多第三方客户端也没有，但ssl对于我们这个伟大的国家是多么重要！