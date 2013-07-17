from flask import Flask, render_template
import datetime
from pymongo.mongo_client import MongoClient

application = Flask(__name__)
application.config.from_object('config')

client = MongoClient()
db = client['lucky_numbers']
numbers_collection = db['winning_numbers']

@application.route('/')
def home():
    return render_template('index.html')

if __name__ == '__main__':
    application.run()
