# Python3-Scraping
A python module for scraping details from crowdcube and kickstarter

This script fetches crowdsourcing project details from Crowdcube Website using BeauifulSoup4 and from Kickstarter by parsing the private API.
The details fetched are title, summary, percentage of fund achieved, link to project, amount_raised and days remaining for the project.

This data is persisted in MongoDB. A performance evaluation on Mongodb aggregation framework vs Python computaion is done based on this data. 
You can easily identify from running this script that for heavy data mongodb aggregation framework is the best fit.

This module is based on python 3.3.1.
Please see the requirements.txt file and install the packages
```
pip install -r requirements.txt
```

Please make sure mongod  is running in your local machine. Or provide the mongodb host details to mongoclient in the script file.

```
#change this to reflect your mongodb instance
mongo_client = MongoClient()
```

After successfull installation of requirements you can just run the script like below
```
python crowdfinance.py 

```
