from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import MetaData
from sqlalchemy.orm import validates, relationship, backref
from sqlalchemy_serializer import SerializerMixin

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///your_database.db'
db = SQLAlchemy(app)

metadata = MetaData(
    naming_convention={
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    }
)

class Restaurant(db.Model, SerializerMixin):
    __tablename__ = "restaurants"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    address = db.Column(db.String)

    # Define relationships
    pizzas = relationship(
        "Pizza",
        secondary="restaurant_pizzas",
        back_populates="restaurants",
        cascade="all, delete"
    )

    # Define serialization rules
    serialize_rules = ('-pizzas',)

    def __repr__(self):
        return f"<Restaurant {self.name}>"

class Pizza(db.Model, SerializerMixin):
    __tablename__ = "pizzas"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    ingredients = db.Column(db.String)

    # Define relationships
    restaurants = relationship(
        "Restaurant",
        secondary="restaurant_pizzas",
        back_populates="pizzas",
        cascade="all, delete"
    )

    # Define serialization rules
    serialize_rules = ('-restaurants',)

    def __repr__(self):
        return f"<Pizza {self.name}, {self.ingredients}>"

class RestaurantPizza(db.Model, SerializerMixin):
    __tablename__ = "restaurant_pizzas"

    id = db.Column(db.Integer, primary_key=True)
    price = db.Column(db.Integer, nullable=False)

    # Define relationships
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurants.id'))
    pizza_id = db.Column(db.Integer, db.ForeignKey('pizzas.id'))

    restaurant = relationship(
        "Restaurant",
        backref=backref("restaurant_pizzas", cascade="all, delete"),
        cascade="all, delete"
    )
    pizza = relationship(
        "Pizza",
        backref=backref("restaurant_pizzas", cascade="all, delete"),
        cascade="all, delete"
    )

    # Define validation
    @validates('price')
    def validate_price(self, key, price):
        if not (1 <= price <= 30):
            raise ValueError("Price must be between 1 and 30.")
        return price

    # Define serialization rules
    serialize_rules = ('-restaurant', '-pizza',)

    def __repr__(self):
        return f"<RestaurantPizza ${self.price}>"

@app.route('/restaurants', methods=['GET'])
def get_restaurants():
    restaurants = Restaurant.query.all()
    return jsonify([restaurant.to_dict(only=('id', 'name', 'address')) for restaurant in restaurants])

@app.route('/restaurants/<int:id>', methods=['GET'])
def get_restaurant(id):
    restaurant = Restaurant.query.get(id)
    if not restaurant:
        return jsonify({"error": "Restaurant not found"}), 404
    
    restaurant_pizzas = RestaurantPizza.query.filter_by(restaurant_id=id).all()
    return jsonify({
        **restaurant.to_dict(only=('id', 'name', 'address')),
        'restaurant_pizzas': [
            {
                'id': rp.id,
                'pizza': rp.pizza.to_dict(only=('id', 'name', 'ingredients')),
                'pizza_id': rp.pizza_id,
                'price': rp.price,
                'restaurant_id': rp.restaurant_id
            }
            for rp in restaurant_pizzas
        ]
    })

@app.route('/restaurants/<int:id>', methods=['DELETE'])
def delete_restaurant(id):
    restaurant = Restaurant.query.get(id)
    if not restaurant:
        return jsonify({"error": "Restaurant not found"}), 404
    
    # Handle cascading deletes
    RestaurantPizza.query.filter_by(restaurant_id=id).delete()
    db.session.delete(restaurant)
    db.session.commit()
    
    return '', 204

@app.route('/pizzas', methods=['GET'])
def get_pizzas():
    pizzas = Pizza.query.all()
    return jsonify([pizza.to_dict(only=('id', 'name', 'ingredients')) for pizza in pizzas])

@app.route('/restaurant_pizzas', methods=['POST'])
def create_restaurant_pizza():
    data = request.get_json()
    
    # Validate input
    if 'price' not in data or 'pizza_id' not in data or 'restaurant_id' not in data:
        return jsonify({"errors": ["Missing required fields"]}), 400
    
    try:
        restaurant_pizza = RestaurantPizza(
            price=data['price'],
            pizza_id=data['pizza_id'],
            restaurant_id=data['restaurant_id']
        )
        db.session.add(restaurant_pizza)
        db.session.commit()
        
        return jsonify({
            'id': restaurant_pizza.id,
            'pizza': restaurant_pizza.pizza.to_dict(only=('id', 'name', 'ingredients')),
            'pizza_id': restaurant_pizza.pizza_id,
            'price': restaurant_pizza.price,
            'restaurant': restaurant_pizza.restaurant.to_dict(only=('id', 'name', 'address')),
            'restaurant_id': restaurant_pizza.restaurant_id
        })
    except ValueError as e:
        return jsonify({"errors": [str(e)]}), 400

if __name__ == '__main__':
    app.run(debug=True)
