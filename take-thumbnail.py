from pymongo import MongoClient
import requests
import re
import sys

g_save_path = "./thumbnails/"

DB_CONFIG = {
	"host" : "localhost",
	"port" : 27017,
	"db"   : "nudele"
}

def saveImage(url, _id):
	with open(g_save_path+_id,'wb') as f:
		raw = requests.get(url).content
		f.write(raw)

def connectDB():
	client = MongoClient(DB_CONFIG['host'], DB_CONFIG['port'])
	db = client[DB_CONFIG['db']]
	Videos = db['video']
	return Videos

def make_path(path):
	if not re.match(r"/$", path):
		path = path + '/'
	return path + 'thumbnails/'

def main():
	global g_save_path
	argv = sys.argv
	if len(argv) == 2:
		g_save_path = make_path(argv[1])

	Videos = connectDB()

	for video in Videos.find():
		if video['tag'] == "xvideos":
			videoId = video['url'].split('/')[-1]
			_id = str(video['_id'])
			print 'http://api.erodouga-rin.net/thumbnails?url=http://jp.xvideos.com/video'+videoId+'/'
			r = requests.get('http://api.erodouga-rin.net/thumbnails?url=http://jp.xvideos.com/video'+videoId+'/')
			try:
				thumbnails = r.json()['thumbnails']
				saveImage(thumbnails[0], _id)
			except KeyError:
				#when video was deleted
				print "removed ", video.get("_id")
				Videos.remove({"_id":str(video.get("_id"))})
				continue

if __name__ == '__main__':
	main()
