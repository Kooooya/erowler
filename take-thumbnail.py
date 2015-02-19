from pymongo import MongoClient
import requests
import os
import uuid

OUT_PUT = './thumbnails/'

DB_CONFIG = {
	"host" : "localhost",
	"port" : 27017,
	"db"   : "nudele"
}

def saveImage(url):
	u = str(uuid.uuid1())
	with open(OUT_PUT+u,'wb') as f:
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
		videoId = video['url'].split('/')[-1]
		print 'http://api.erodouga-rin.net/thumbnails?url=http://jp.xvideos.com/video'+videoId+'/'
		r = requests.get('http://api.erodouga-rin.net/thumbnails?url=http://jp.xvideos.com/video'+videoId+'/')
		thumbnails = r.json()['thumbnails']
		saveImage(thumbnails[0])


if __name__ == '__main__':
	main()