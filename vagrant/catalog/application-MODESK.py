from flask import Flask, render_template, request, redirect, jsonify, url_for, flash
from sqlalchemy import create_engine, asc
from sqlalchemy.orm import sessionmaker
from database_setup import Base, Bike, BikePart, User
from flask import session as login_session
import random
import string
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2
import json
from flask import make_response
import requests

app = Flask(__name__)

CLIENT_ID = json.loads(
    open('client_secrets.json', 'r').read())['web']['client_id']
APPLICATION_NAME = "Bike Shop Application"


# Connect to Database and create database session
engine = create_engine('sqlite:///bike.db')
Base.metadata.bind = engine


# Create anti-forgery state token
@app.route('/login', methods=['GET', 'POST'])
def showLogin():
    if request.method == 'GET':
        state = ''.join(random.choice(string.ascii_uppercase + string.digits)
                        for x in xrange(32))
        login_session['state'] = state
        # return "The current session state is %s" % login_session['state']
        return render_template('login.html', STATE=state)
    if request.method == 'POST':
        login_session['username'] = request.form['user_name']
        login_session['password'] = request.form['password']
        user_id = checkUserCred(login_session['username'],
                                    login_session['password'])
        if not user_id:
            msg = "No account found. Please Signup."
            return redirect(url_for('showLogin', message=msg))
        else:
            login_session['user_id'] = user_id
            flash("Now logged in as %s" % login_session['username'])
            return redirect(url_for('showBikes'))

@app.route('/signup', methods=['GET', 'POST'])
def showSignup():
    if request.method == 'GET':
        return render_template('signup.html')
    if request.method == 'POST':
        login_session['username'] = request.form['user_name']
        login_session['email'] = request.form['email']
        login_session['password'] = request.form['password']
        user_id = createUser(login_session)
        login_session['user_id'] = user_id
        return redirect(url_for('showBikes', ))

@app.route('/fbconnect', methods=['POST'])
def fbconnect():
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    access_token = request.data
    print "access token received %s " % access_token


    app_id = json.loads(open('fb_client_secrets.json', 'r').read())[
        'web']['app_id']
    app_secret = json.loads(
        open('fb_client_secrets.json', 'r').read())['web']['app_secret']
    url = 'https://graph.facebook.com/oauth/access_token?grant_type=fb_exchange_token&client_id=%s&client_secret=%s&fb_exchange_token=%s' % (
        app_id, app_secret, access_token)
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]


    # Use token to get user info from API
    userinfo_url = "https://graph.facebook.com/v2.8/me"
    '''
        Due to the formatting for the result from the server token exchange we have to
        split the token first on commas and select the first index which gives us the key : value
        for the server access token then we split it on colons to pull out the actual token value
        and replace the remaining quotes with nothing so that it can be used directly in the graph
        api calls
    '''
    token = result.split(',')[0].split(':')[1].replace('"', '')

    url = 'https://graph.facebook.com/v2.8/me?access_token=%s&fields=name,id,email' % token
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]
    # print "url sent for API access:%s"% url
    # print "API JSON result: %s" % result
    data = json.loads(result)
    login_session['provider'] = 'facebook'
    login_session['username'] = data["name"]
    login_session['email'] = data["email"]
    login_session['facebook_id'] = data["id"]

    # The token must be stored in the login_session in order to properly logout
    login_session['access_token'] = token

    # Get user picture
    url = 'https://graph.facebook.com/v2.8/me/picture?access_token=%s&redirect=0&height=200&width=200' % token
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]
    data = json.loads(result)

    login_session['picture'] = data["data"]["url"]

    # see if user exists
    user_id = getUserID(login_session['email'])
    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']

    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 300px; height: 300px;border-radius: 150px;-webkit-border-radius: 150px;-moz-border-radius: 150px;"> '

    flash("Now logged in as %s" % login_session['username'])
    return output


@app.route('/fbdisconnect')
def fbdisconnect():
    facebook_id = login_session['facebook_id']
    # The access token must me included to successfully logout
    access_token = login_session['access_token']
    url = 'https://graph.facebook.com/%s/permissions?access_token=%s' % (facebook_id,access_token)
    h = httplib2.Http()
    result = h.request(url, 'DELETE')[1]
    return "you have been logged out"


@app.route('/gconnect', methods=['POST'])
def gconnect():
    # Validate state token
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # Obtain authorization code
    code = request.data

    try:
        # Upgrade the authorization code into a credentials object
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(
            json.dumps('Failed to upgrade the authorization code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Check that the access token is valid.
    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
           % access_token)
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])
    # If there was an error in the access token info, abort.
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is used for the intended user.
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(
            json.dumps("Token's user ID doesn't match given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is valid for this app.
    if result['issued_to'] != CLIENT_ID:
        response = make_response(
            json.dumps("Token's client ID does not match app's."), 401)
        print "Token's client ID does not match app's."
        response.headers['Content-Type'] = 'application/json'
        return response

    stored_access_token = login_session.get('access_token')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_access_token is not None and gplus_id == stored_gplus_id:
        response = make_response(json.dumps('Current user is already connected.'),
                                 200)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Store the access token in the session for later use.
    login_session['access_token'] = credentials.access_token
    login_session['gplus_id'] = gplus_id

    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()

    login_session['username'] = data['name']
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']
    # ADD PROVIDER TO LOGIN SESSION
    login_session['provider'] = 'google'

    # see if user exists, if it doesn't make a new one
    user_id = getUserID(data["email"])
    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']
    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 300px; height: 300px;border-radius: 150px;-webkit-border-radius: 150px;-moz-border-radius: 150px;"> '
    flash("you are now logged in as %s" % login_session['username'])
    print "done!"
    return output

# User Helper Functions


def createUser(login_session):
    DBSession = sessionmaker(bind=engine)
    session = DBSession()
    newUser = User(name=login_session['username'], email=login_session[
                   'email'], password=login_session['password'], picture=login_session['picture'])
    session.add(newUser)
    session.commit()
    user = session.query(User).filter_by(email=login_session['email']).one()
    return user.id


def getUserInfo(userID):
    DBSession = sessionmaker(bind=engine)
    session = DBSession()
    user = session.query(User).filter_by(id=userID).one()
    return user

def checkUserCred(name, password):
    DBSession = sessionmaker(bind=engine)
    session = DBSession()
    user = session.query(User).filter_by(name=name, password=password)
    if user:
        msg= "Login valid!"
        return msg
    else:
        msg = "Login invalid!"
        return msg


def getUserID(email):
    DBSession = sessionmaker(bind=engine)
    session = DBSession()
    try:
        user = session.query(User).filter_by(email=email).one()
        return user.id
    except:
        return None

# DISCONNECT - Revoke a current user's token and reset their login_session


@app.route('/gdisconnect')
def gdisconnect():
    # Only disconnect a connected user.
    access_token = login_session.get('access_token')
    if access_token is None:
        response = make_response(
            json.dumps('Current user not connected.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % access_token
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]
    if result['status'] == '200':
        response = make_response(json.dumps('Successfully disconnected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response
    else:
        response = make_response(json.dumps('Failed to revoke token for given user.', 400))
        response.headers['Content-Type'] = 'application/json'
        return response


# JSON APIs to view Bike Information
@app.route('/Bike/<int:Bike_id>/BikePart/JSON')
def BikeBikePartJSON(Bike_id):
    DBSession = sessionmaker(bind=engine)
    session = DBSession()
    Bike = session.query(Bike).filter_by(id=Bike_id).one()
    items = session.query(BikePart).filter_by(
        Bike_id=Bike_id).all()
    return jsonify(BikePart=[i.serialize for i in items])


@app.route('/Bike/<int:Bike_id>/BikePart/<int:BikePart_id>/JSON')
def BikePartJSON(Bike_id, BikePart_id):
    DBSession = sessionmaker(bind=engine)
    session = DBSession()
    BikePart_Item = session.query(BikePart).filter_by(id=BikePart_id).one()
    return jsonify(BikePart_Item=BikePart_Item.serialize)


@app.route('/Bike/JSON')
def BikesJSON():
    DBSession = sessionmaker(bind=engine)
    session = DBSession()
    Bikes = session.query(Bike).all()
    return jsonify(Bikes=[r.serialize for r in Bikes])


# Show all Bikes
@app.route('/')
@app.route('/Bike')
def showBikes():
    DBSession = sessionmaker(bind=engine)
    session = DBSession()
    Bikes = session.query(Bike).order_by(asc(Bike.name))
    if 'username' not in login_session:
        return render_template('publicBikes.html', Bikes=Bikes)
    else:
        return render_template('Bikes.html', Bikes=Bikes)

# Create a new Bike
@app.route('/Bike/new/', methods=['GET', 'POST'])
def newBike():
    if 'username' not in login_session:
        return redirect('/login')
    if request.method == 'POST':
        DBSession = sessionmaker(bind=engine)
        session = DBSession()
        newBike = Bike(
            name=request.form['name'], user_id=login_session['user_id'],
            description=request.form['description'],
            manufacturer=request.form['manufacturer'],
            price=request.form['price'])
        session.add(newBike)
        flash('New Bike %s Successfully Created' % newBike.name)
        session.commit()
        return redirect(url_for('showBikes'))
    else:
        return render_template('newBike.html')

# Edit a Bike
@app.route('/Bike/<int:Bike_id>/edit/', methods=['GET', 'POST'])
def editBike(Bike_id):
    DBSession = sessionmaker(bind=engine)
    session = DBSession()
    editedBike = session.query(
        Bike).filter_by(id=Bike_id).one()
    if 'username' not in login_session:
        return redirect('/login')
    if editedBike.user_id != login_session['user_id']:
        return "<script>function myFunction() {alert('You are not authorized to edit this Bike. Please create your own Bike in order to edit.');}</script><body onload='myFunction()'>"
    if request.method == 'POST':
        if request.form['name']:
            editedBike.name = request.form['name']
            flash('Bike Successfully Edited %s' % editedBike.name)
            return redirect(url_for('showBikes'))
    else:
        return render_template('editBike.html', Bike=editedBike)


# Delete a Bike
@app.route('/Bike/<int:Bike_id>/delete/', methods=['GET', 'POST'])
def deleteBike(Bike_id):
    DBSession = sessionmaker(bind=engine)
    session = DBSession()
    BikeToDelete = session.query(
        Bike).filter_by(id=Bike_id).one()
    if 'username' not in login_session:
        return redirect('/login')
    if BikeToDelete.user_id != login_session['user_id']:
        return "<script>function myFunction() {alert('You are not authorized to delete this Bike. Please create your own Bike in order to delete.');}</script><body onload='myFunction()'>"
    if request.method == 'POST':
        session.delete(BikeToDelete)
        flash('%s Successfully Deleted' % BikeToDelete.name)
        session.commit()
        return redirect(url_for('showBikes', Bike_id=Bike_id))
    else:
        return render_template('deleteBike.html', Bike=BikeToDelete)

# Show a Bike BikePart


@app.route('/Bike/<int:Bike_id>/')
@app.route('/Bike/<int:Bike_id>/BikePart/')
def showBikePart(Bike_id):
    DBSession = sessionmaker(bind=engine)
    session = DBSession()
    bike = session.query(Bike).filter_by(id=Bike_id).one()
    creator = getUserInfo(bike.user_id)
    items = session.query(BikePart).filter_by(
        user_id=creator.id).all()
    if 'username' not in login_session or creator.id != login_session['user_id']:
        return render_template('publicBikePart.html', items=items, Bike=bike, creator=creator)
    else:
        return render_template('BikePart.html', items=items, Bike=bike, creator=creator)


# Create a new BikePart item
@app.route('/Bike/<int:Bike_id>/BikePart/new/', methods=['GET', 'POST'])
def newBikePart(Bike_id):
    DBSession = sessionmaker(bind=engine)
    session = DBSession()
    if 'username' not in login_session:
        return redirect('/login')
    Bike = session.query(Bike).filter_by(id=Bike_id).one()
    if login_session['user_id'] != Bike.user_id:
        return "<script>function myFunction() {alert('You are not authorized to add BikePart items to this Bike. Please create your own Bike in order to add items.');}</script><body onload='myFunction()'>"
        if request.method == 'POST':
            newItem = BikePart(name=request.form['name'], description=request.form['description'], price=request.form[
                               'price'], course=request.form['course'], Bike_id=Bike_id, user_id=Bike.user_id)
            session.add(newItem)
            session.commit()
            flash('New BikePart %s Item Successfully Created' % (newItem.name))
            return redirect(url_for('showBikePart', Bike_id=Bike_id))
    else:
        return render_template('newBikePart.html', Bike_id=Bike_id)

# Edit a BikePart item


@app.route('/Bike/<int:Bike_id>/BikePart/<int:BikePart_id>/edit', methods=['GET', 'POST'])
def editBikePart(Bike_id, BikePart_id):
    DBSession = sessionmaker(bind=engine)
    session = DBSession()
    if 'username' not in login_session:
        return redirect('/login')
    editedItem = session.query(BikePart).filter_by(id=BikePart_id).one()
    Bike = session.query(Bike).filter_by(id=Bike_id).one()
    if login_session['user_id'] != Bike.user_id:
        return "<script>function myFunction() {alert('You are not authorized to edit BikePart items to this Bike. Please create your own Bike in order to edit items.');}</script><body onload='myFunction()'>"
    if request.method == 'POST':
        if request.form['name']:
            editedItem.name = request.form['name']
        if request.form['description']:
            editedItem.description = request.form['description']
        if request.form['price']:
            editedItem.price = request.form['price']
        if request.form['course']:
            editedItem.course = request.form['course']
        session.add(editedItem)
        session.commit()
        flash('BikePart Item Successfully Edited')
        return redirect(url_for('showBikePart', Bike_id=Bike_id))
    else:
        return render_template('editBikePart.html', Bike_id=Bike_id, BikePart_id=BikePart_id, item=editedItem)


# Delete a BikePart item
@app.route('/Bike/<int:Bike_id>/BikePart/<int:BikePart_id>/delete', methods=['GET', 'POST'])
def deleteBikePart(Bike_id, BikePart_id):
    DBSession = sessionmaker(bind=engine)
    session = DBSession()
    if 'username' not in login_session:
        return redirect('/login')
    Bike = session.query(Bike).filter_by(id=Bike_id).one()
    itemToDelete = session.query(BikePart).filter_by(id=BikePart_id).one()
    if login_session['user_id'] != Bike.user_id:
        return "<script>function myFunction() {alert('You are not authorized to delete BikePart items to this Bike. Please create your own Bike in order to delete items.');}</script><body onload='myFunction()'>"
    if request.method == 'POST':
        session.delete(itemToDelete)
        session.commit()
        flash('BikePart Item Successfully Deleted')
        return redirect(url_for('showBikePart', Bike_id=Bike_id))
    else:
        return render_template('deleteBikePart.html', item=itemToDelete)


# Disconnect based on provider
@app.route('/disconnect')
def disconnect():
    if 'provider' in login_session:
        if login_session['provider'] == 'google':
            gdisconnect()
            del login_session['gplus_id']
            del login_session['access_token']
        if login_session['provider'] == 'facebook':
            fbdisconnect()
            del login_session['facebook_id']
        del login_session['username']
        del login_session['email']
        del login_session['picture']
        del login_session['user_id']
        del login_session['provider']
        flash("You have successfully been logged out.")
        return redirect(url_for('showBikes'))
    else:
        flash("You were not logged in")
        return redirect(url_for('showBikes'))


if __name__ == '__main__':
    app.secret_key = 'super_secret_key'
    app.debug = True
    app.run(host='0.0.0.0', port=8000)
