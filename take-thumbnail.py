from pymongo import MongoClient
import requests
import re
import sys
from pprint import pprint
from bs4 import BeautifulSoup

DB_CONFIG = {
	"host" : "localhost",
	"port" : 27017,
	"db"   : "nudele"
}

g_save_path = "./thumbnails/"
session = None
Videos = None

def saveImage(url, _id):
	with open(g_save_path+_id,'wb') as f:
		raw = requests.get(url).content
		f.write(raw)

def connectDB():
	client = MongoClient(DB_CONFIG['host'], DB_CONFIG['port'])
	db = client[DB_CONFIG['db']]
	Videos = db['video']
	return Videos

def make_saving_path(path):
	if not re.match(r"/$", path):
		path = path + '/'
	return path + 'thumbnails/'

def fc2(video):
	global Videos
	_id = str(video['_id'])
	video_url = video["url"]
	request = session.get(video_url)
	soup = BeautifulSoup(request.text)
	title_tag = soup.find("h2",{"class":["cont_v2_hmenu04", "clearfix"]})
	if title_tag is not None and title_tag.string is not None and not '(Removed)' in title_tag.string:
		r = re.compile("changeThumbnail\('(.+\.jpg)',")
		m = r.search(request.text)
		image_url = m.group(1)
		saveImage(image_url, _id)
		print "saved : "+video_url
	else:
		removeVideo(video)

def xvideos(video):
	global Videos
	videoId = video['url'].split('/')[-1]
	_id = str(video['_id'])
	r = requests.get('http://api.erodouga-rin.net/thumbnails?url=http://jp.xvideos.com/video'+videoId+'/')
	try:
		thumbnails = r.json()['thumbnails']
		saveImage(thumbnails[0], _id)
		print "saved : "+video["url"]
	except KeyError:
		removeVideo(video)

def removeVideo(video):
	global Videos
	Videos.remove(video)
	print "removed ", video["url"]

def loginToFc2():
	global session
	if session is None:
		session = requests.session()
		login_data = {'email': 'fukushi123@gmail.com', 'pass': 'koya820'}
		session.post('https://secure.id.fc2.com/index.php?mode=login&switch_language=en', login_data)
		pprint(session)

def main():
	global g_save_path
	global Videos
	argv = sys.argv
	if len(argv) == 2:
		g_save_path = make_saving_path(argv[1])

	Videos = connectDB()

	loginToFc2()

	for video in Videos.find():
		if video['tag'] == "xvideos":
			xvideos(video)
		if video['tag'] == "fc2":
			fc2(video)

if __name__ == '__main__':
	main()