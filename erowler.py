# -*- coding: utf-8 -*-

'''
usage :
	
	python erowler.py http://maniacture.com/?tag=紗倉まな

'''

import requests
from bs4 import BeautifulSoup
from pprint import pprint
from urlparse import urlparse
import urllib
import urllib2
import sys, traceback
from pymongo import MongoClient
import re
import json

OUT_PUT = './thumbnails/'
NG_WORDS = [
	"police",
	"ranking",
	"dmm",
	"./",
	"#",
	"mixi",
	'twitter.com',
	"facebook",
	"google",
	"hatena" 
]
ALREADY = []
MAX_DEPTH = 5
DB_CONFIG = {
	"host" : "localhost",
	"port" : 27017,
	"db"   : "nudele"
}

Videos = None
lastUrl = None
session = None
g_snapshot = None

def getNextLink(url, host, depth=0):
	global g_snapshot

	if depth is not 0:
		ok = validateUrl(url)
		if not ok:
			return

	print url

	response = connectSite(url, host)

	try :
		soup = BeautifulSoup(response.read())
	except AttributeError:
		return

	searchVideo(url, soup)

	links = findNextLinks(soup)

	"""try:
		ago = g_snapshot["struct"][depth]
	except IndexError:
		ago = g_snapshot["struct"].append(0)
	if ago is not None:
		links = links[ago:-1]
	"""

	if depth < MAX_DEPTH:
		for i,link in enumerate(links):
			g_snapshot["struct"][depth] = i
			getNextLink(link, host, depth + 1)
	return


def connectDB():
	global Videos
	client = MongoClient(DB_CONFIG['host'], DB_CONFIG['port'])
	db = client[DB_CONFIG['db']]
	Videos = db['video']


def videoTitle(soup, elm, tag, individualed=True):
	if tag is "fc2" and hasattr(elm, "tl"):
		return elm["tl"]
	if not individualed:
		while elm is not None:
			for prev in elm.previous_siblings:
				if prev.name is None:
					continue
				match = re.match( r'^h[1-3]', prev.name )
				if match:
					title = prev.string
			for next in elm.next_siblings:
				if next.name is None:
					continue
				match = re.match( r'^h[1-3]', next.name )
				if match:
					title = next.string
			elm = elm.parent
			if elm is not None:
				match = re.match( r'^h[1-3]', elm.name )
				if match:
					title = match

	if title is None and soup.title is not None:
		title =  soup.title.get_text()
	elif len(soup.findAll(attrs={"name":"title"})) is not 0:
		title =  soup.findAll(attrs={"name":"title"})[0]['content']
	else:
		title = None

	if title is not None:
		counts = len(Videos.findAll({"title":re.compile('.*'+title+'.*')}))
		if counts >= 1:
			title = title+' '+str(counts)

	return title.split("｜")[0]


def videoDesc(soup):
	if len(soup.findAll(attrs={"name":"description"})) is not 0:
		desc =  soup.findAll(attrs={"name":"description"})[0]['content']
		desc = re.sub(r'<("[^"]*"|\'[^\']*\'|[^\'">])*>', '', desc)
		desc = re.sub(r'\s+','',desc)
		return desc
	else:
		return None


def videoKeyword(soup):
	if len(soup.findAll(attrs={"name":"keyword"})) is not 0:
		try:
			return soup.findAll(attrs={"name":"keyword"})[0]['content']
		except KeyError:
			return None
	return None



def saveVideo(src, soup, url, tag, elm, individualed=True):
	global Videos

	title = videoTitle(soup, elm, tag)

	if title is not None:
		print "title : " + title
	else:
		print "title is empty"
		return

	desc = videoDesc(soup)
	keyword = videoKeyword(soup)

	if desc is not None:
		print "desc : " + desc
	if keyword is not None:
		print "keyword : " + keyword
	print "src : " + src
	print "tag : " + tag
	print "in " + url
	print

	owner = urlparse(url)
	owner = host[0] + "://" + host[1]

	video = {
		"title" : title,
		"url"	: src,
		"desc"	: desc,
		"owner" : owner,
		"tag"	: tag,
		"parent"  : url,
		"keyword" : keyword
	}

	Videos.insert(video)


def findNextLinks(soup):
	links = []
	for link in soup.findAll('a'):
		if link.has_attr("href"):
			links.append(urllib.unquote(link['href']))
	nextLinks = list(set(links))
	return nextLinks


def searchVideo(url, soup):
	xvideos_sources = soup.findAll("iframe")
	fc2_sources = soup.findAll('script',{"url":True})

	#Is page individual?.
	individualed = True
	if len(xvideos_sources) + len(fc2_sources) > 2:
		individualed = False

	#xvideos
	for source in xvideos_sources:
		if source.has_attr("src") and "xvideos.com" in source['src']:
			if videoEnabled(source['src'], 'xvideos'):
				saveVideo(source["src"], soup, url, 'xvideos', source, individualed)
	#fc2
	for source in fc2_sources:
		if videoEnabled(source['url'], 'fc2'):
			saveVideo(source['url'], soup, url, 'fc2', source, individualed)
		


def connectSite(url, host):
	req = urllib2.Request(url)
	try:
		response = urllib2.urlopen(req)
	#server error
	except urllib2.HTTPError:
		return
	#If url is relaytive path, format it to correct format
	except ValueError:
		if len(url) > 1 and url[0] is not '/':
			url = '/' + url
		url = host + url
		req = urllib2.Request(url)
		try:
			response = urllib2.urlopen(req)
		#server error
		except urllib2.HTTPError:
			return
		#does not found url
		except urllib2.URLError:
			print "Does not found the : " + url
			return
		except UnicodeEncodeError:
			try:
				req = urllib2.Request(url.encode('utf-8'))
				response = urllib2.urlopen(req)
			except urllib2.HTTPError:
				return
	#does not found url
	except urllib2.URLError:
		print "Does not found the : " + url
		return
	except UnicodeDecodeError:
		req = urllib2.Request(url.encode('utf-8'))
		response = urllib2.urlopen(req)

	return response


'''
Validate a URL. If NG_WORDS include it, skip it, else NG_WORDS append it and just continue.
'''
def validateUrl(url):

	parsed = urlparse(url)
	path = parsed.path.encode('utf-8')
	params = parsed.query.encode('utf-8')

	if path in ALREADY:
		return
	elif path is not "/" and path is not "":
		ALREADY.append(path)

	if params in ALREADY:
		return
	elif params is not "":
		ALREADY.append(params)

	#check NG_WOR have including URL
	for word in NG_WORDS:
		try:
			if word in url or url is "/":
				print "Ignore : " + url
				return False

		except UnicodeDecodeError:
			try:
				if word in urllib.quote(url):
					print "Ignore : " + url
					return False
			except KeyError:
				pass

	return True

def videoEnabled(link, tag):
	if tag is 'xvideos':
		videoId = link.split('/')[-1]
		try:
			req = urllib2.Request('http://jp.xvideos.com/video'+videoId+'/')
			response = urllib2.urlopen(req)
		except urllib2.HTTPError:
			return False
		soup = BeautifulSoup(response.read())
		if soup.find('embed') is None:
			return False
		else:
			return True

	if tag is 'fc2':
		loginFc2()
		soup = BeautifulSoup(session.get(link).content)
		if soup.find_all('div', 'req_regist_member'):
			content =  session.get('https://secure.id.fc2.com/?done=video&switch_language=ja').content
			soup = BeautifulSoup(content)
		if soup.has_attr('cont_v2_hmenu04') and soup['cont_v2_hmenu04'].text is not '(Removed) ****************************':
			return True
		else:
			return False
		


def loginFc2():
	global session
	if session is None:
		session = requests.Session()
		session.get('http://video.fc2.com/')
		data = {'email': 'fukushi123@gmail.com', 'pass': 'koya820'}
		r_login = session.post('https://secure.id.fc2.com/index.php?mode=login&switch_language=en', data=data)
		print session.cookies['PHPSESSID']


def takeSnapshot():
	print "taked snapshot"
	g_snapshot["Already"] = ALREADY
	with open('_snapshot', 'w') as f:
		json.dump(g_snapshot, f)

def restore(url):
	global g_snapshot
	global ALREADY

	with open('_snapshot', 'r') as f:
		try:
			snapshot = json.load(f)
			g_snapshot = snapshot
			pprint(g_snapshot)
			ALREADY = g_snapshot.get('Already')
		except ValueError:
			g_snapshot = {
				"root" : url,
				"struct" : []
			}

if __name__ == '__main__':
	reload(sys)
	sys.setdefaultencoding("utf-8")

	argvs = sys.argv

	if len(argvs) == 2:
		url = argvs[1]
	elif len(argvs) == 3:
		url = argvs[1]
		MAX_DEPTH = int(argvs[2])
	else:
		print "引数へんじゃない？"
		quit()

	restore(url)

	p = urlparse(url)
	host = p[0] + "://" + p[1]

	connectDB()
	try:
		getNextLink(url, host)
	except:
		traceback.print_exc(file=sys.stdout)

		takeSnapshot()

	pprint(ALREADY)
