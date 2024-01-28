from flask import Flask, request, jsonify
import sqlite3
from fuzzywuzzy import fuzz
from math import radians, sin, cos, sqrt, atan2

app = Flask(__name__)

# Configure SQLite database
DATABASE = 'addresses.db'

# Create tables for addresses and customers
def create_tables():
    with sqlite3.connect(DATABASE) as connection:
        cursor = connection.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS customers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_name TEXT NOT NULL
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS addresses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                street TEXT NOT NULL,
                city TEXT NOT NULL,
                state TEXT NOT NULL,
                zip_code TEXT NOT NULL,
                customer_id INTEGER,
                popularity INTEGER,
                latitude REAL,
                longitude REAL,
                FOREIGN KEY (customer_id) REFERENCES customers(id)
            )
        ''')
        connection.commit()

create_tables()

# Function to calculate the Haversine distance between two coordinates
def haversine(lat1, lon1, lat2, lon2):
    R = 6371  # Radius of the Earth in kilometers
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    distance = R * c
    return distance

# API endpoint to add a new customer
@app.route('/add_customer', methods=['POST'])
def add_customer():
    data = request.get_json()

    customer_name = data.get('customer_name')

    with sqlite3.connect(DATABASE) as connection:
        cursor = connection.cursor()
        cursor.execute('''
            INSERT INTO customers (customer_name)
            VALUES (?)
        ''', (customer_name,))
        connection.commit()

    return jsonify({'message': 'Customer added successfully'}), 201

# API endpoint to add a new address for a customer
@app.route('/add_address', methods=['POST'])
def add_address():
    data = request.get_json()

    street = data.get('street')
    city = data.get('city')
    state = data.get('state')
    zip_code = data.get('zip_code')
    customer_id = data.get('customer_id')
    popularity = data.get('popularity', 0)  # Default to 0 if not provided
    latitude = data.get('latitude')
    longitude = data.get('longitude')

    with sqlite3.connect(DATABASE) as connection:
        cursor = connection.cursor()
        cursor.execute('''
            INSERT INTO addresses (street, city, state, zip_code, customer_id, popularity, latitude, longitude)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (street, city, state, zip_code, customer_id, popularity, latitude, longitude))
        connection.commit()

    return jsonify({'message': 'Address added successfully'}), 201

# API endpoint to get addresses for a specific customer
@app.route('/get_addresses_by_customer', methods=['GET'])
def get_addresses_by_customer():
    customer_id = request.args.get('customer_id')

    with sqlite3.connect(DATABASE) as connection:
        cursor = connection.cursor()
        cursor.execute('''
            SELECT * FROM addresses
            WHERE customer_id = ?
        ''', (customer_id,))

        results = cursor.fetchall()

    if results:
        addresses = [{'id': row[0], 'street': row[1], 'city': row[2], 'state': row[3], 'zip_code': row[4], 'popularity': row[6], 'latitude': row[7], 'longitude': row[8]} for row in results]
        return jsonify({'addresses': addresses})
    else:
        return jsonify({'message': 'No addresses found for the specified customer'}), 404

# API endpoint to get addresses by popularity
@app.route('/get_addresses_by_popularity', methods=['GET'])
def get_addresses_by_popularity():
    popularity = request.args.get('popularity')

    with sqlite3.connect(DATABASE) as connection:
        cursor = connection.cursor()
        cursor.execute('''
            SELECT * FROM addresses
            WHERE popularity = ?
        ''', (popularity,))

        results = cursor.fetchall()

    if results:
        addresses = [{'id': row[0], 'street': row[1], 'city': row[2], 'state': row[3], 'zip_code': row[4], 'popularity': row[6], 'latitude': row[7], 'longitude': row[8]} for row in results]
        return jsonify({'addresses': addresses})
    else:
        return jsonify({'message': 'No addresses found with the specified popularity'}), 404

# API endpoint for fuzzy search based on text input within a radius
@app.route('/fuzzy_search_within_radius', methods=['GET'])
def fuzzy_search_within_radius():
    search_text = request.args.get('search_text')
    latitude = float(request.args.get('latitude'))
    longitude = float(request.args.get('longitude'))
    radius = float(request.args.get('radius'))

    with sqlite3.connect(DATABASE) as connection:
        cursor = connection.cursor()
        cursor.execute('''
            SELECT * FROM addresses
        ''')

        results = cursor.fetchall()

    if results:
        # Perform fuzzy matching and filter by radius
        addresses = [{'id': row[0], 'street': row[1], 'city': row[2], 'state': row[3], 'zip_code': row[4], 'popularity': row[6], 'latitude': row[7], 'longitude': row[8]} for row in results]
        matched_addresses = []

        for address in addresses:
            ratio = fuzz.token_set_ratio(search_text, f"{address['state']} {address['city']} {address['street']}")
            if ratio > 50:  # You can adjust the threshold as needed
                distance = haversine(latitude, longitude, address['latitude'], address['longitude'])
                if distance <= radius:
                    matched_addresses.append(address)

        # Sort the matched addresses by popularity in descending order
        sorted_addresses = sorted(matched_addresses, key=lambda x: x['popularity'], reverse=True)

        # Return the top 100 most popular addresses within the radius
        top_100_addresses = sorted_addresses[:100]
        return jsonify({'top_100_addresses': top_100_addresses})
    else:
        return jsonify({'message': 'No addresses found'}), 404

# API endpoint to get the top 100 most popular addresses
@app.route('/get_top_popular_addresses', methods=['GET'])
def get_top_popular_addresses():
    with sqlite3.connect(DATABASE) as connection:
        cursor = connection.cursor()
        cursor.execute('''
            SELECT * FROM addresses
            ORDER BY popularity DESC
            LIMIT 100
        ''')

        results = cursor.fetchall()

    if results:
        addresses = [{'id': row[0], 'street': row[1], 'city': row[2], 'state': row[3], 'zip_code': row[4], 'popularity': row[6], 'latitude': row[7], 'longitude': row[8]} for row in results]
        return jsonify({'addresses': addresses})
    else:
        return jsonify({'message': 'No addresses found'}), 404

if __name__ == '__main__':
    app.run(debug=True)
