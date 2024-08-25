from flask import Flask, request, jsonify, make_response
from flask_migrate import Migrate
from flask_restful import Api, Resource
import os
from models import db, Restaurant, RestaurantPizza, Pizza

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATABASE = os.environ.get("DB_URI", f"sqlite:///{os.path.join(BASE_DIR, 'app.db')}")

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.json.compact = False

db.init_app(app)
migrate = Migrate(app, db)
api = Api(app)

class Restaurants(Resource):
    def get(self):
        restaurants = Restaurant.query.all()
        return [restaurant.to_dict(only=("id", "name", "address")) for restaurant in restaurants], 200

api.add_resource(Restaurants, "/restaurants")

class RestaurantById(Resource):
    def get(self, id):
        session = db.session
        restaurant = session.get(Restaurant, id)
        if restaurant:
            return restaurant.to_dict(only=("id", "name", "address", "restaurant_pizzas.pizza", "restaurant_pizzas.price")), 200
        return {"error": "Restaurant not found"}, 404

    def delete(self, id):
        session = db.session
        restaurant = session.get(Restaurant, id)
        if restaurant:
            session.delete(restaurant)
            session.commit()
            return {}, 204
        return {"error": "Restaurant not found"}, 404

api.add_resource(RestaurantById, "/restaurants/<int:id>")

class Pizzas(Resource):
    def get(self):
        pizzas = Pizza.query.all()
        return [pizza.to_dict(only=("id", "name", "ingredients")) for pizza in pizzas], 200

api.add_resource(Pizzas, "/pizzas")

class RestaurantPizzas(Resource):
    def post(self):
        data = request.get_json()

        price = data.get("price")
        pizza_id = data.get("pizza_id")
        restaurant_id = data.get("restaurant_id")

        session = db.session
        pizza = session.get(Pizza, pizza_id)
        restaurant = session.get(Restaurant, restaurant_id)
        if not pizza or not restaurant:
            return {"errors": ["Pizza or Restaurant not found"]}, 404

        if price is None or price < 1 or price > 30:
            return {"errors": ["validation errors"]}, 400

        new_restaurant_pizza = RestaurantPizza(
            price=price,
            pizza_id=pizza_id,
            restaurant_id=restaurant_id
        )

        session.add(new_restaurant_pizza)
        session.commit()

        response_data = {
            "id": new_restaurant_pizza.id,
            "price": new_restaurant_pizza.price,
            "pizza_id": new_restaurant_pizza.pizza_id,
            "restaurant_id": new_restaurant_pizza.restaurant_id,
            "pizza": {"id": pizza.id, "name": pizza.name},
            "restaurant": {"id": restaurant.id, "name": restaurant.name}
        }
        return make_response(
            jsonify(response_data),
            201,
        )

api.add_resource(RestaurantPizzas, "/restaurant_pizzas")

@app.route("/")
def index():
    return "<h1>Code challenge</h1>"


if __name__ == "__main__":
    app.run(port=5555, debug=True)







