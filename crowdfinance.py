import requests
from bs4 import BeautifulSoup
import json
import re
from pymongo import MongoClient
import time
import datetime

mongo_client = MongoClient()
db = mongo_client.mydb

CROWDCUBE_PARSE_DICT = [
	{'key': 'title', 'selector': 'h1', 'type': 'string'},
	{'key': 'amount_raised', 'selector': 'div.cc-card__stats div.cc-inlineStats__group > .cc-inlineStats__value', 'type': 'float'},
	{'key': 'percentage', 'selector': 'div.cc-card__stats > div.cc-card__progress > div.cc-progressBar > span:nth-of-type(1)', 'type': 'int'},
	{'key': 'link', 'selector': 'a:nth-of-type(1)', 'type': 'string', 'attr':'href'},
	{'key': 'daysleft', 'selector': 'div.cc-card__daysLeft', 'type': 'int'},
	{'key': 'summary', 'selector': 'div.cc-card__body > p', 'type': 'string'}
]

CROWDCUBE_CARD_ = "section.cc-card"
CROWDCUBE_URL = "https://www.crowdcube.com/investments?"
KICKSTARTER_URL = "https://www.kickstarter.com/discover/advanced?google_chrome_workaround&category_id={0}\
&woe_id=0&sort=magic&seed=2481827&page={1}"

REQUEST_HEADERS = {
	'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:28.0) Gecko/20100101 Firefox/28.0',
	'Accept': 'application/json, text/javascript, */*; q=0.01',
	'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
	'X-Requested-With': 'XMLHttpRequest'
}

USD_TO_GBP_RATE = 0.82 # As on 10th March

'''
	Assumptions
	Crowcube data is on pound and so keeping our base currency as pound for storage.
	Kickstarter has multicurrency data and api has currency conversion rate based on USD

'''

class BaseClass:

	def __init__(self):
		self._projects = []

	@property
	def projects(self):
		return self._projects

	def python_aggregate(self):
		sum = 0
		projects = list(db.projects.find())
		for project in projects:
			if project['daysleft'] >= 10:
				sum += project['amount_raised']
		return sum

	def mongodb_aggregate(self):
		pipeline = [
    				{"$match": {'daysleft' : {'$gte' : 10}}}, # Filter days more than 10
				   	{ '$group': { '_id': '$null', 'sum': { '$sum': '$amount_raised' } } }]
		sum = list(db.projects.aggregate(pipeline))[0]['sum']
		return sum

	def document_count(self):
		count = db.projects.count()
		return count

	def clear_db(self):
		count = db.projects.remove()


class CrowdCube(BaseClass):
	_source = "crowdcube"

	def __init__(self):
		super().__init__()


	def _extract_details(self, card):
		temp = {}
		for obj in CROWDCUBE_PARSE_DICT:
			item = card.select(obj['selector'])
			if len(item) > 0:
				content = item[0].getText(strip=True) if 'attr' not in obj else item[0][obj['attr']].strip()
				temp[obj['key']] =  content if obj['type'] == 'string' else float(re.search(r'\d+', content.replace(',', '')).group())
			else:
				temp[obj['key']] = ""
		temp['source'] = self._source
		return temp

	def scrape_site(self):
		result = requests.get(CROWDCUBE_URL)

		content = result.content
		soup = BeautifulSoup(content, "html.parser")
		for card in soup.select(CROWDCUBE_CARD_):
			self._projects.append(self._extract_details(card))

		# Load Dynamically Added Cards (Scrolling Pagination Cards)
		cursorNext = soup.select_one('div#cc-opportunities__paginate')["data-nextcursor"]

		while cursorNext is not None:
			cursorNext = CROWDCUBE_URL + "cursor=" + cursorNext + "&ajax=true"
			result = requests.get(cursorNext, headers=REQUEST_HEADERS)
			content = result.content.decode('utf-8')
			content = json.loads(content)
			soup = BeautifulSoup(content["content"], "html.parser")
			cursorNext = content["cursorNext"]

			for card in soup.select(CROWDCUBE_CARD_):
				self._projects.append(self._extract_details(card))
		db.projects.insert(self.projects)

	


class KickStarter(BaseClass):

	_source = "kickstarter"

	def __init__(self):
		super().__init__()

	def scrape_api(self, category_id=None):
		category_id = category_id if category_id is not None else 1
		page = 1
		while len(self.projects) < 100:
			result = requests.get(KICKSTARTER_URL.format(category_id, page), headers=REQUEST_HEADERS)
			content = result.content.decode('utf-8')
			content = json.loads(content)
			for project in content['projects']:
				temp = {}
				temp['title'] = project['name']
				temp['amount_raised'] = float(project['usd_pledged']) * USD_TO_GBP_RATE
				temp['percentage'] = (project['pledged'] / project['goal']) * 100
				temp['link'] = project['urls']['web']['project']
				deadline = datetime.datetime(1970,1,1,0,0) + datetime.timedelta(seconds=project['deadline'] - 1)
				current_date = datetime.datetime.now()
				temp['daysleft'] = (deadline-current_date).days
				temp['summary'] = project['blurb']
				temp['source'] = self._source
				self.projects.append(temp)
			page += 1
		db.projects.insert(self.projects)






if __name__ == '__main__':

	crowdcube = CrowdCube()
	print("Clearing Database")
	crowdcube.clear_db()
	print("Scraping started from CrowdCube, Please wait...")
	crowdcube.scrape_site()
	print("Scraping completed from CrowdCube, ")

	print("\n\033[92m %s documents exist in database now\033[0m" % (crowdcube.document_count()))

	print("-- Computaion from Python --")
	start_time = time.time()
	print("Total amount raised: %.2f" % (crowdcube.python_aggregate()))
	print("\033[94m*** %.5f seconds elapsed ***\033[0m" % (time.time() - start_time))

	print("\n-- Computaion from Mongodb --")
	start_time = time.time()
	print("Total amount raised: %.2f" % (crowdcube.mongodb_aggregate()))
	print("\033[94m*** %.5f seconds elapsed ***\033[0m" % (time.time() - start_time))

	print('='*50)
	kickstarter = KickStarter()
	print("Accessing private API from Kickstarter, Please wait...")
	kickstarter.scrape_api()
	print("API processing from Kickstarter completed")

	print("\n\033[92m %s documents exist in database now\033[0m" % (kickstarter.document_count()))

	print("-- Computaion from Python ( All Platform ) --")
	start_time = time.time()
	print("Total amount raised: %.2f" % (kickstarter.python_aggregate()))
	print("\033[94m*** %.5f seconds elapsed ***\033[0m" % (time.time() - start_time))

	print("\n-- Computaion from Mongodb ( All Platform ) --")
	start_time = time.time()
	print("Total amount raised: %.2f" % (kickstarter.mongodb_aggregate()))
	print("\033[94m*** %.5f seconds elapsed ***\033[0m" % (time.time() - start_time))

