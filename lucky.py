"""
lucky.py

This file is used to manage the project and scrape data from the Illinois State Lottery Website. With the -sd flag the data is saved in MongoDB. Without the -s the file won't actually scrape anything. Example: python lucky.py -t -s -sd.

"""
import datetime, requests, json, sys, argparse, doctest, pymongo
from application import numbers_collection, db
GAMES = {
        'Mega Millions':'MM',
        'Lotto':'LO',
        'Pick 3':'PICK3',
        'My3':'MY3',
        'Powerball':'PB',
        'Lucky Day Lotto':'LL',
        'Pick 4':'PICK4'
        }
BASE_URL = "http://www.illinoislottery.com/lottery/data/history/winners/" # root of all the lottery data

def exception(name, **attributes):
    """
    >>> ExampleException = exception('ExampleException', x=20)
    >>> raise ExampleException('This example raises an exception') 
    Traceback (most recent call last):
      File "/Library/Frameworks/Python.framework/Versions/2.7/lib/python2.7/doctest.py", line 1289, in __run
        compileflags, 1) in test.globs
      File "<doctest __main__.exception[1]>", line 1, in <module>
        raise ExampleException('This example raises an exception')
    ExampleException: 'This example raises an exception'
    >>> print ExampleException.x
    20
    """

    # TODO document 
    exception = type(name, (Exception, ), attributes)
    def _string_function(self):
        return repr(self.value)

    def _initialize(self, value, **attributes):
        self.value = value
        for key, value in attributes.iteritems():
            setattr(self, key, value)
    exception.__str__ = _string_function
    exception.__init__ = _initialize

    return exception

DocumentException = exception('DocumentException')

def get_or_create(json_data, collection):
    """
    >>> json_data = 'muajaja'
    >>> raise DocumentException('No data was found nor inserted into the database with collection: %s' % json_data)
    Traceback (most recent call last):
      File "/Library/Frameworks/Python.framework/Versions/2.7/lib/python2.7/doctest.py", line 1289, in __run
        compileflags, 1) in test.globs
      File "<doctest __main__.get_or_create[1]>", line 1, in <module>
        raise DocumentException('No data was found nor inserted into the database with collection: %s' % json_data)
    DocumentException: 'No data was found nor inserted into the database with collection: muajaja'
    """
    # TODO: heavy testing, and document
    if not isinstance(collection, pymongo.collection.Collection):
        raise TypeError("%s isn't a MongoDB collection" % collection)
    if not isinstance(json_data, dict):
        raise TypeError("%s must be a dictionary that conforms to the json specification." % json_data)

    document = collection.find_one(json_data) # the record from the database
    
    if document is None:
        # if the record wasn't found then we create one 
        document = collection.insert(json_data)
    
    if not document:
        #  If we don't have a racord at the end then a bad problem occured
        raise DocumentException('No data was found nor inserted into the database with collection: %s' % json_data)
    
    return document

def format_date(date):
    # TODO test
    if not isinstance(date, datetime.date) and not isinstance(date, datetime.datetime):
        raise TypeError("date_data must be a datetime.date or datetime.datetime object")
    return date.strftime('%m-%d-%Y')

def fetch_json_data(url):
    return json.loads(requests.get(url).content)
    
def slashes_to_datetime(text):
    # TODO test
    if not isinstance(text, str) and not isinstance(text, unicode): raise TypeError('text argument must be a string.')
    date_segemtns = text.split('/')
    year = int(date_segemtns[2])
    month = int(date_segemtns[0])
    day = int(date_segemtns[1])
    return datetime.datetime(year, month, day)

class LuckyNumber(object):
    """
    Represent a lottery winning number.
    See the official data at http://www.illinoislottery.com/en-us/Winning/Winning_Number_Search/winning-number-search-game.html.

    """
    def __init__(self, data_dict):
        """
        Takes a dictionary with col1, col2, col3 and parses it.

        """

        # Example data_dict: 
        # {u'col4': None, u'col5': None, u'col2': u'Powerball', u'col3': [u'02-08-22-35-37[06]', u' '], u'col1': u'07/13/2013'}
        self.game_type = data_dict['col2']
        self.winning_numbers = data_dict['col3'][0]
        self.date = slashes_to_datetime(data_dict['col1'])
    
    def __str__(self):
        """Returns a string representation of the object. It's in csv format for some convenience"""
        return "%s, %s, %s" % (self.game_type, self.date, self.winning_numbers)
    
    def toJSON(self):
        """Returns a JSON representation of the object."""
        # TODO find a way to make this a general method
        return ({'gametype': self.game_type, 'number': self.winning_numbers, 'date': self.date})


def main_scrape(noisy=False, save_to_db=False):
    """
    A function who's soul purpose is to automate the scraping proccess.

    GAMES is dict of the different games the Illinois state lotter offers data on.
    The keys are arbitary human friendly name.
    GAMES[prety_name] = url_name
    The values are the names the website uses in the url scheme.
    The following doctest double checks that all url endpoints are available.

    >>> url = "http://www.illinoislottery.com/lottery/data/history/winners/%s/01-01-2012/01-1-2013.json"
    >>> for game in GAMES:
    ...     data = requests.get(url % GAMES[game])
    ...     data.status_code == 200 # Check that urls are working, however any value for the game text would be valid
    ...     len(json.loads(data.content)) > 1 # Since any game name would be valid, make sure some data is returned
    True
    True
    True
    True
    True
    True
    True
    True
    True
    True
    True
    True
    True
    True
    """
    start = datetime.date(1980, 1, 1) # date to start scraping from
    stop = datetime.date.today() # date to end the scraping at
    
    DATE_SEGMENT_URL = "/%s/%s" % (format_date(start), format_date(stop)) # this will traslate to something like #TODO
    """
    At the iterations the urls will look like this:
    http://www.illinoislottery.com/lottery/data/history/winners/<game>/<start_date>/<stop_date>
    example:
    http://www.illinoislottery.com/lottery/data/history/winners/PB/01-01-1980/07-17-2013
    http://www.illinoislottery.com/lottery/data/history/winners/LL/01-01-1980/07-17-2013
    http://www.illinoislottery.com/lottery/data/history/winners/MY3/01-01-1980/07-17-2013
    http://www.illinoislottery.com/lottery/data/history/winners/LO/01-01-1980/07-17-2013
    http://www.illinoislottery.com/lottery/data/history/winners/MM/01-01-1980/07-17-2013
    http://www.illinoislottery.com/lottery/data/history/winners/PICK4/01-01-1980/07-17-2013
    http://www.illinoislottery.com/lottery/data/history/winners/PICK3/01-01-1980/07-17-2013
    """

    for game in GAMES:
        data_url = "%s%s%s" % (BASE_URL, GAMES[game] ,DATE_SEGMENT_URL ) # TODO
        winning_numbers_json_data = fetch_json_data(data_url)
        for winning_number_record in winning_numbers_json_data:
           record = LuckyNumber(winning_number_record)

           if save_to_db: get_or_create(record.toJSON(), numbers_collection)
           
           if noisy: print record

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-t','--test', help="Run the doctests", action="store_true")
    parser.add_argument('-s', '--scrape', help="Scrape the lottery website", action="store_true")
    parser.add_argument('-p', '--print_data', help="Print the scraped data in a csv format so that you can do python lucky.py -s -p > data.csv", action="store_true")
    parser.add_argument('-sd', '--save_data', help="Save the scraped data to the MongoDB database", action="store_true")
    parser.add_argument('-ddb', '--delete_db', help="Save the scraped data to the MongoDB database", action="store_true")
    args = parser.parse_args()
    if args.test:
        doctest.testmod()
    if args.scrape:
        main_scrape(noisy=args.print_data, save_to_db=args.save_data)
    if args.delete_db:
        db.drop_collection(numbers_collection)
