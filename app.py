from flask import (Flask, render_template, flash,
                   url_for, redirect, request, make_response, g)
from flask_bcrypt import check_password_hash
from flask_login import LoginManager, login_user
import Tables, forms, googlemaps, json, urllib.parse

# create a new google maps object, new client key
app = Flask(__name__)
app.secret_key = 'kj1hk2j2h3k1j2h3k12jh3l1kj23912839128739oaaooaoaoaoo-p'
gmaps = googlemaps.Client(key='AIzaSyBKLplL94Oeye2T5lkfIOupftKkrWA7qEo')

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

@login_manager.user_loader
def load_user(userid):
    try:
        return Tables.User.get(Tables.User.id == userid)
    except Tables.DoesNotExist:
        return None

def drivetime(origin, destination):
    """Takes an in origin and destination, calculates the drive time
    strips and returns the required info from the json output"""
    drive_time = (gmaps.distance_matrix(origin, destination, mode="driving"))
    return drive_time["rows"][0]["elements"][0]["duration"]["text"]


def directions(origin, destination):
    """takes in an origin and destination, strips the needed info from
    the json output and returns the directions. Will return none if unable to
     calculate a route"""
    try:
        directions = (gmaps.distance_matrix(origin, destination, mode="driving"))
        directions = str(directions["rows"][0]["elements"][0]["distance"]["text"])
        directions = ''.join(i for i in directions if i not in 'km,')
        return int(directions)
    except KeyError:
        return None


def fuelcost(fuel_type):
    """A price for fuel is returned based on the users fuel selection"""
    if fuel_type == "Petrol(91)":
        return 1.35
    elif fuel_type == "Petrol(98)":
        return 1.58
    elif fuel_type == "LPG":
        return .58
    else:
        return 1.50


def fueloptions():
    """ list of petrol options the user can choose from. HTML
    template iterates through to generate the selection options
    for the user"""
    return ['Petrol(91)', 'Petrol(98)', 'LPG', 'Diesel']


def economyoptions():
    """dictionary of fuel economy options the user can choose from.
    Key value's key is used to calculate the fuel cost"""
    return {'5': "Excellent (5L/100km)", '8': "Fair (8L/100km)",
            '11': "Poor (11L/100km)", '14': "Bad 14L/100km"}


def calcfuelcost(total_distance, litres_per_100kms, fuel_cost):
    """takes in the total distance, litres per 100km and the cost of fuel
    returns how many litres are needed to complete the trip and the
    cost of the fuel."""
    litres_needed = int(total_distance) * (int(litres_per_100kms) / 100)
    fuelcost = int(litres_needed) * float(fuel_cost)
    return litres_needed, fuelcost


def geocodeinput(origin, destination):
    """takes in the users selected origin and destination,
    returns the latitutde and longitude of the origin and destination.
    Function is needed to generate map markers"""
    origin = gmaps.geocode(origin)
    origin_lat = float(origin[0]["geometry"]["location"]["lat"])
    origin_lng = float(origin[0]["geometry"]["location"]["lng"])

    destination = gmaps.geocode(destination)
    destination_lat = float(destination[0]["geometry"]["location"]["lat"])
    destination_lng = float(destination[0]["geometry"]["location"]["lng"])

    return origin_lat, origin_lng, destination_lat, destination_lng


def getsaved():
    """requests the users fuel type and fuel economy from a cookie"""
    try:
        fuel_type = request.cookies.get('fuel_type')
        economy = request.cookies.get('economy')
        cookie_test = json.loads(request.cookies.get('testing'))
    except TypeError:
        fuel_type = {}
        economy = {}
    return fuel_type, economy

@app.before_request
def before_request():
    """Connect to the database before each request"""
    g.db = Tables.DATABASE
    g.db.connect()

@app.route('/register', methods=('GET', 'POST'))
def register():
    form = forms.RegisterForm()
    if form.validate_on_submit():
        flash("You have successfully registered", "success")
        Tables.User.create_user(
            username=form.username.data,
            email=form.email.data,
            password=form.password.data
        )
        return redirect(url_for('index'))
    return render_template('register.html', form=form)

@app.route('/savedtrips')
def savedtrips():
    trip1 = Tables.SavedTrips.create(origin = "Perth", destination = "Sydney")
    trip1.save()
    for item in Tables.SavedTrips.select():
        print(item)
    return render_template('savedtrips.html', trip = trip1)

@app.route('/login', methods=('GET','POST'))
def login():
    form = forms.LoginForm()
    if form.validate_on_submit():
        try:
            user = Tables.User.get(Tables.User.email == form.email.data)
        except Tables.DoesNotExist:
            flash("Your email or password doesn't match!", "error")
        else:
            if check_password_hash(user.password, form.password.data):
                login_user(user)
                flash("You've been logged in!", "success")
                return redirect(url_for('index'))
            else:
                flash("Your email or password doesn't match!", "error")
    return render_template("login.html", form=form)

@app.after_request
def before_request(response):
    """Close the database connection after each request"""
    g.db.close()
    return response

@app.route("/")
def index():
    """checks to see if a fuel or economy cookie has been set.
    renders the basic template and passes those options in."""
    fuel_options = fueloptions()
    economy_options = economyoptions()
    return render_template("index.html",
                           fuel_options=fuel_options,
                           economy_options=economy_options)


@app.route("/route")
def route(origin_lat=None, origin_lng=None,
          dest_lat=None, dest_lng=None, error=None):
    """takes in GPS coordinates of the origin and destination and
    any errors that occur. Renders the template passing in the
    parameters needed to generate the route."""
    fuel_type, economy = getsaved()
    origin_lat = request.args.get('origin_lat', origin_lat)
    origin_lng = request.args.get('origin_lng', origin_lng)
    dest_lat = request.args.get('dest_lat', dest_lat)
    dest_lng = request.args.get('dest_lng', dest_lng)
    error = request.args.get('error', error)
    fuel_options = fueloptions()
    economy_options = economyoptions()
    return render_template("index.html", origin_lat=origin_lat,
                           origin_lng=origin_lng, dest_lat=dest_lat,
                           dest_lng=dest_lng, fuel_type=fuel_type,
                           economy=economy, fuel_options=fuel_options,
                           economy_options=economy_options, error=error)


@app.route("/save", methods=['POST'])
def save():
    """requests the origin and destination, generates
    the directions, drive time. Requests the cartype, fueltype,
    calculates the fuel_cost, sets cookies for the fuel type and
    fuel economy and passes those calculations through to the
    rendered template.
     """
    origin = request.form["origin"]
    destination = request.form["destination"]
    total_distance = directions(origin, destination)
    if not total_distance:
        error = "Could not find a valid route"
        return redirect(url_for('route', error=error))

    drive_time = drivetime(origin, destination)

    car_type = request.form["economy"]
    fuel_type = request.form["fuel"]

    fuel_cost = fuelcost(fuel_type)
    litres, fuel = calcfuelcost(total_distance, car_type, fuel_cost)

    origin_lat, origin_lng, dest_lat, dest_lng \
        = (geocodeinput(origin, destination))

    cookie_response = make_response(redirect(url_for('route', origin_lat=origin_lat,
                                                     origin_lng=origin_lng, dest_lat=dest_lat,
                                                     dest_lng=dest_lng)))

    cookie_dict = {'fueltype': fuel_type, 'fueleconomy': car_type}
    cookie_response.set_cookie('fuel_type', fuel_type)
    cookie_response.set_cookie('economy', car_type)
    cookie_response.set_cookie('testing', json.dumps(cookie_dict))

    flash("{} kilometers travelled".format(total_distance))
    flash("{} litres used".format(round(litres)))
    flash("{} dollars worth of fuel".format(round(fuel)))
    flash("{} total drive time".format(drive_time))
    return cookie_response

if __name__ == '__main__':
	app.run(debug=True, use_reloader=True)
