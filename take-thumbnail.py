from pymongo import MongoClient
import requests

OUT_PUT = './thumbnails/'

DB_CONFIG = {
	"host" : "localhost",
	"port" : 27017,
	"db"   : "nudele"
}

def saveImage(url, _id):
	with open(OUT_PUT+_id,'wb') as f:
		raw = requests.get(url).content
		f.write(raw)

def connectDB():
	client = MongoClient(DB_CONFIG['host'], DB_CONFIG['port'])
	db = client[DB_CONFIG['db']]
	Videos = db['video']
	return Videos

def main():
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
