from flask import Flask, jsonify, request
#import requests
import json
import sys
from loguru import logger
import time
from functools import wraps
class Book:
    def __init__(self, id, title, author, year, price, genres):
        self.id=id
        self.title=title
        self.author=author
        self.year=int(year)
        self.price=float(price)
        self.genres=genres

    def bookDict(self):
        return {
            "id": self.id,
            "title": self.title,
            "author": self.author,
            "price": self.price,
            "year": self.year,
            "genres": self.genres
        }




app=Flask(__name__)
bookCounter=0
requestCounter=0
store={}
storeList=[]
loggerLevels={"requestLogger": "INFO", "booksLogger": "INFO"}

def increment():
    global requestCounter
    requestCounter+=1
def Sfilter(name):
    def filter(record):
        return record["extra"].get("name") == name
    return filter



logger.remove(0)
requestLoggerID=logger.add(sys.stderr, level="INFO", format="{time:DD-MM-YYYY HH:mm:ss.sss} {level} {message}", filter=Sfilter("requestLogger"))
requestLogger=logger.bind(name='requestLogger')


booksLoggerID=logger.add('logs/books.log', level="INFO", format="{time:DD-MM-YYYY HH:mm:ss.sss} {level}: {message}",filter=Sfilter("booksLogger"))
booksLogger=logger.bind(name='booksLogger')

def log_request(endpoint):
    @wraps(endpoint)
    def wrapper(*args, **kwargs):
        global requestCounter
        increment()
        start_time = time.time()
        requestLogger.info(f"Incoming request | #{requestCounter} | resource: {request.path} | HTTP Verb {request.method}")

        response = endpoint(*args, **kwargs)

        end_time = time.time()
        duration = (end_time - start_time) * 1000  # Convert to milliseconds
        requestLogger.debug(f"request #{requestCounter} duration: {duration:.5}ms")

        return response
    return wrapper


@app.route('/')
@log_request
def index():
    return "hello world"

@app.route('/books/health', methods=['GET'])
@log_request
def health():
    return "OK", 200

@app.route('/book', methods=['POST'])
@log_request
def newBook():
    global bookCounter
    global requestCounter

    data=request.get_json()
    title=data['title']
    booksLogger.info(f"Creating new Book with Title [{title}] | request #{requestCounter}")
    if title.lower() in store:
        return jsonify({"errorMessage": f"Book with the title [{title}] already exists in the system"}), 409

    author=data['author']

    year=data['year']
    if year < 1940 or year > 2100:
        return jsonify({"errorMessage": f"Error: Can’t create new Book that its year [{year}] is not in the accepted range [1940 -> 2100]"}) , 409

    price=data['price']
    if price < 0:
        return jsonify({"errorMessage": "Error: Can’t create new Book with negative price"}), 409

    booksLogger.debug(f"Currently there are {bookCounter} Books in the system. New Book will be assigned with id {(bookCounter+1)} | request #{requestCounter}")
    id = bookCounter= bookCounter + 1
    genres=data['genres']

    addBook(id, title, author, year, price, genres)

    return jsonify({"result" : id}), 200

@app.route('/books/total', methods=['GET'])
@log_request
def returnTotal():
    global requestCounter
    author=request.args.get('author')
    priceBT = request.args.get('price-bigger-than', type=float)
    priceLT = request.args.get('price-less-than', type=float)
    yearBT = request.args.get('year-bigger-than', type=int)
    yearLN= request.args.get('year-less-than', type=int)
    genres = request.args.get('genres')
    res=filterBooks(author, priceLT, priceBT, yearBT, yearLN, genres)
    booksLogger.info(f"Total Books found for requested filters is {res} | request #{requestCounter}")


    return jsonify({"result" : res}), 200

def addBook(id, title, author, year, price, genres):
    newBook=Book(id, title, author, year, price, genres)
    store[title]=newBook
    storeList.append(newBook)

def filterBooks(author, priceLT, priceBT=-1, yearBT=1940, yearLN=2100, genres = []):
    res=0

    if genres is not None:
        genres = set(genres.split(','))


    for book in storeList:
        if (
            (author is None or author.lower() == book.author.lower()) and
            (priceLT is None or book.price < priceLT) and
            (priceBT is None or book.price>priceBT) and
            (yearBT is None or book.year>yearBT) and
            (yearLN is None or book.year<yearLN) and
            (genres is None or (len(set(genres).intersection(book.genres)))!=0)
            ):
            res+=1

    return int(res)

@app.route('/books', methods=['GET'])
@log_request
def bookData():
    global requestCounter
    """need to sort through list, doing
     that would allow me to create the
      jsonfiles already in the correct
       order"""
    jsonArray=[]

    storeList.sort(key=lambda x: x.title)
    author = request.args.get('author')
    priceBT = request.args.get('price-bigger-than', type = float)
    priceLT = request.args.get('price-less-than', type = float)
    yearBT = request.args.get('year-bigger-than', type = int)
    yearLN = request.args.get('year-less-than', type = int)
    genres = request.args.get('genres')

    if genres is not None:
        genres = set(genres.split(','))

    for book in storeList:
        if (
                (author is None or author.lower() == book.author.lower()) and
                (priceLT is None or book.price < priceLT) and
                (priceBT is None or book.price > priceBT) and
                (yearBT is None or book.year > yearBT) and
                (yearLN is None or book.year < yearLN) and
                (genres is None or (len(set(genres).intersection(book.genres))) != 0)
        ):
            jsonArray.append(book.bookDict())
            len=len(jsonArray)
            booksLogger.info(f"Total Books found for requested filters is {len} | request #{requestCounter}")


    return jsonify({"result": jsonArray}), 200


@app.route('/book', methods=['PUT'])
@log_request
def SingleBookUpdatePrice():
    global requestCounter
    oldPrice=0
    id=request.args.get('id', type=int)
    newPrice=request.args.get('price', type=float)

    if newPrice<1:
        return jsonify({"errorMessage": f"Error: no such Book with id {id}"}), 404

    for book in storeList:
        if id==book.id:
            oldPrice=book.price
            book.price=newPrice
            booksLogger.info(f"Update Book id [{id}] price to {newPrice} | request #{requestCounter}")
            booksLogger.debug(f"Book [{book.title}] price change: {oldPrice} --> {newPrice} | request #{requestCounter}")
            return jsonify({"result": int(oldPrice)}), 200

    return jsonify({"errorMessage": f"Error: price update for book [{id}] must be a positive integer"}), 409


@app.route('/book', methods=['GET'])
@log_request
def SingleBookData():
    global requestCounter
    id=request.args.get('id', type=int)
    for book in storeList:
        if id==book.id:
            booksLogger.debug(f"Fetching book id {id} details | request #{requestCounter}")
            res=book.bookDict()
            return jsonify({"result": f"{json.dumps(res, indent=4)}"}), 200

    return jsonify({"errorMessage": f"Error: no such Book with id {id}"}), 404


@app.route('/book', methods=['DELETE'])
@log_request
def deleteSingleBookData():
    global bookCounter
    global requestCounter
    id=request.args.get('id', type=int)
    for book in storeList:
        if id==book.id:
            storeList.remove(book)
            booksLogger.info(f"Removing book [{book.title}] | request #{requestCounter}")
            bookCounter-=1
            booksLogger.debug(f"After removing book [{book.title}] id: [{book.id}] there are {bookCounter} books in the system | request #{requestCounter}")
            return jsonify({"result": bookCounter}), 200

    return jsonify({"errorMessage": f"Error: no such Book with id {id}"}), 404

@app.route('/logs/level', methods=['GET'])
@log_request
def loggerLevel():
    level=request.args.get('logger-name')
    if(level!= 'booksLogger' and level!='requestLogger'):
        return jsonify({"errorMessage": f"Error: no such logger with name {level}"}), 404.
    return loggerLevels[level].upper() , 200


@app.route('/logs/level', methods=['PUT'])
@log_request
def WupdateLogLevel():
    name=request.args.get('logger-name')

    if (name != 'booksLogger' and name != 'requestLogger'):
        return jsonify({"errorMessage": f"Error: no such logger with name {name}"}), 404.

    newLevel=request.args.get('logger-level').upper()
    if  name=='booksLogger':
       logger.remove(booksLoggerID)
       logger.add('logs/books.log', level=newLevel, format="{time:DD-MM-YYYY HH:mm:ss.sss} {level} {message}",
                  filter=Sfilter("booksLogger"))
       booksLogger = logger.bind(name='booksLogger')
       return newLevel, 200

    if name=='requestLogger':
        logger.remove(requestLoggerID)
        logger.add(sys.stderr, level=newLevel, format="{time:DD-MM-YYYY HH:mm:ss.sss} {level} {message}",
                   filter=Sfilter("requestLogger"))
        requestLogger = logger.bind(name='requestLogger')
        return newLevel, 200

    return f"Error: No such logger with name {name}, try booksLogger of requestLogger", 404.




if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8574)


    """it seems that inner port can cause problems!"""
