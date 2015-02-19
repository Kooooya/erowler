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
import sys
from pymongo import MongoClient
import re
import os
import uuid

OUT_PUT = './thumbnails/'
NG_WORDS = [  #"ad",
			  "police",
			  "ranking",
			  "dmm",
			  "./",
			  "#",
			  "mixi",
			  'twitter.com',
			  "facebook",
			  "google",
			  "hatena" ]
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

def getNextLink(url, host, depth=0):

	ok = validateUrl(url)
	if not ok:
		return
	
	response = connectSite(url, host)

	try :
		soup = BeautifulSoup(response.read())
	except AttributeError:
		return

	searchVideo(url, soup)

	links = findNextLinks(soup)

	if depth < MAX_DEPTH:
		for link in links:
			getNextLink(link, host, depth + 1)
	return


def connectDB():
	global Videos
	client = MongoClient(DB_CONFIG['host'], DB_CONFIG['port'])
	db = client[DB_CONFIG['db']]
	Videos = db['video']


def videoTitle(soup, elm, tag, individual=True):

	if tag is "fc2" and elm["tl"] is not None:
		return elm["tl"]

	if not individual:
		while elm is not None:
			for prev in elm.previous_siblings:
				if prev.name is None:
					continue
				match = re.match( r'^h[1-3]', prev.name )
				if match:
					return prev.string

			for next in elm.next_siblings:
				if next.name is None:
					continue
				match = re.match( r'^h[1-3]', next.name )
				if match:
					return next.string

			elm = elm.parent
			if elm is not None:
				match = re.match( r'^h[1-3]', elm.name )
				if match:
					print elm.name

	if soup.title is not None:
		return soup.title.get_text()
	elif len(soup.findAll(attrs={"name":"title"})) is not 0:
		return soup.findAll(attrs={"name":"title"})[0]['content']
	else:
		return None


def videoDesc(soup):
	if len(soup.findAll(attrs={"name":"description"})) is not 0:
		return soup.findAll(attrs={"name":"description"})[0]['content']
	else:
		return None


def videoKeyword(soup):
	if len(soup.findAll(attrs={"name":"keyword"})) is not 0:
		try:
			return soup.findAll(attrs={"name":"keyword"})[0]['content']
		except KeyError:
			return None
	return None



def saveVideo(src, soup, url, tag, elm, individual=True):
	global Videos

	title = videoTitle(soup, elm, tag).split("｜")[0]
	desc = videoDesc(soup)
	keyword = videoKeyword(soup)
	thumbnail = takeThumbnail(src, tag)

	host = urlparse(url)
	host = host[0] + "://" + host[1]

	if title is None:
		print "Does not found title in " + url
	else:
		print "title : " + title
	if desc is not None:
		print "desc : " + desc
	if keyword is not None:
		print "keyword : " + keyword
	print "thumb : " + thumbnail
	print "src : " + src
	print "tag : " + tag
	print "in " + url
	print

	video = {
		"thumb" : thumbnail,
		"title" : title,
		"url"	: src,
		"desc"	: desc,
		"owner" : host,
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
	individual = True
	if len(xvideos_sources) + len(fc2_sources) > 2:
		individual = False

	#xvideos
	for source in xvideos_sources:
		if source.has_attr("src") and "xvideos.com" in source['src']:
			if videoEnabled(source['src'], 'xvideos'):
				saveVideo(source["src"], soup, url, 'xvideos', source, individual)
	#fc2
	for source in fc2_sources:
		if videoEnabled(source['url'], 'fc2'):
			saveVideo(source['url'], soup, url, 'fc2', source, individual)
		


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

	p = urlparse(url)
	path = p[2]
	if path in ALREADY:
		return

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

	if path is not "/" and path is not "":
		ALREADY.append(path)

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
			print content
			soup = BeautifulSoup(content)
		if soup.has_attr('cont_v2_hmenu04') and soup['cont_v2_hmenu04'].text is not '(Removed) ****************************':
			return True
		else:
			print link
			return False
		


def loginFc2():
	global session
	if session is None:
		session = requests.Session()
		session.get('http://video.fc2.com/')
		data = {'email': 'fukushi123@gmail.com', 'pass': 'koya820'}
		r_login = session.post('https://secure.id.fc2.com/index.php?mode=login&switch_language=en', data=data)
		print session.cookies['PHPSESSID']


def takeThumbnail(url, tag):
	if tag is 'xvideos':
		videoId = url.split('/')[-1]
		r = requests.get('http://api.erodouga-rin.net/thumbnails?url=http://jp.xvideos.com/video'+videoId+'/')
		thumbnails = r.json()['thumbnails']
		u = saveImage(thumbnails[0])
		return u
		#elif tag is 'fc2':


def saveImage(url):
	u = str(uuid.uuid1())
	with open(OUT_PUT+u,'wb') as f:
		raw = requests.get(url).content
		f.write(raw)
	return u



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

	p = urlparse(url)
	host = p[0] + "://" + p[1]

	connectDB()
	getNextLink(url, host)

	pprint(ALREADY)
