from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import select, CheckConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, Session
from flask_marshmallow import Marshmallow
from marshmallow import fields, validate, ValidationError

from typing import List
from collections import Counter
import datetime

from config import HOST, USER, PASSWORD, DATABASE

app = Flask(__name__)
app.json.sort_keys = False
app.config["SQLALCHEMY_DATABASE_URI"] = f"mysql+mysqlconnector://{USER}:{PASSWORD}@{HOST}/{DATABASE}"

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(app, model_class=Base)
ma = Marshmallow(app)

class Customer(Base):
    __tablename__ = "Customers"
    customer_id: Mapped[int] = mapped_column(autoincrement=True, primary_key=True)
    name: Mapped[str] = mapped_column(db.String(255))
    email: Mapped[str] = mapped_column(db.String(319))
    phone: Mapped[str] = mapped_column(db.String(15))
    customer_account: Mapped["CustomerAccount"] = relationship(back_populates="customer")
    orders: Mapped[List["Order"]] = relationship(back_populates="customer")

class CustomerAccount(Base):
    __tablename__ = "Customer_Accounts"
    username: Mapped[str] = mapped_column(db.String(255), unique=True, nullable=False)
    password: Mapped[str] = mapped_column(db.String(255), nullable=False)
    customer_id: Mapped[int] = mapped_column(db.ForeignKey("Customers.customer_id"), primary_key=True)
    customer: Mapped["Customer"] = relationship(back_populates="customer_account")

class OrderProduct(Base):
    __tablename__ = "Order_Product"
    order_id: Mapped[int] = mapped_column(db.ForeignKey("Orders.order_id"), primary_key=True)
    product_id: Mapped[int] = mapped_column(db.ForeignKey("Products.product_id"), primary_key=True)
    quantity: Mapped[int] = mapped_column(default=1)
    product: Mapped["Product"] = relationship()

class Order(Base):
    __tablename__ = "Orders"
    order_id: Mapped[int] = mapped_column(autoincrement=True, primary_key=True)
    date: Mapped[datetime.date] = mapped_column(db.Date, nullable=False)
    customer_id: Mapped[int] = mapped_column(db.ForeignKey("Customers.customer_id"))
    customer: Mapped["Customer"] = relationship(back_populates="orders")
    products: Mapped[List["OrderProduct"]] = relationship(cascade="all")

class Product(Base):
    __tablename__ = "Products"
    product_id: Mapped[int] = mapped_column(autoincrement=True, primary_key=True)
    name: Mapped[str] = mapped_column(db.String(255), nullable=False)
    price: Mapped[float] = mapped_column(db.Float, nullable=False)
    stock: Mapped[int] = mapped_column(CheckConstraint("stock >= 0"), default=1)

with app.app_context():
    db.create_all()


# ===================================== SCHEMATA =======================================

class CustomerSchema(ma.Schema):
    name = fields.String(required=True, validate=validate.Length(max=255))
    email = fields.String(required=True, validate=validate.Length(max=319))
    phone = fields.String(required=True, validate=validate.Length(max=15))

    class Meta:
        fields = "customer_id", "name", "email", "phone"

customer_schema = CustomerSchema()
customers_schema = CustomerSchema(many=True)

class CustomerAccountSchema(ma.Schema):
    customer_id = fields.Integer(required=True)
    username = fields.String(required=True, validate=validate.Length(max=255))
    password = fields.String(required=True, validate=validate.Length(max=255))

    class Meta:
        fields = "customer_id", "username", "password"

customer_account_schema = CustomerAccountSchema()
customer_accounts_schema = CustomerAccountSchema(many=True)

class ProductSchema(ma.Schema):
    product_id = fields.Integer(required=False)
    name = fields.String(required=True, validate=validate.Length(min=1, max=255))
    price = fields.Float(required=True, validate=validate.Range(min=0))
    stock = fields.Integer(default=1, validate=validate.Range(min=0))

    class Meta:
        fields = "product_id", "name", "price", "stock"

product_schema = ProductSchema()
products_schema = ProductSchema(many=True)

class ProductQuantitySchema(ma.Schema):
    product_id = fields.Integer(required=False)
    name = fields.String(required=True, validate=validate.Length(min=1, max=255))
    price = fields.Float(required=True, validate=validate.Range(min=0))
    quantity = fields.Integer(default=1, validate=validate.Range(min=0))

    class Meta:
        fields = "product_id", "name", "price", "quantity"

products_quantity_schema = ProductQuantitySchema(many=True)

class OrderSchema(ma.Schema):
    order_id = fields.Integer(required=False)
    customer_id = fields.Integer(required=True)
    date = fields.Date(required=True)
    product_ids = fields.List(fields.Integer())

    class Meta:
        fields = "order_id", "customer_id", "date", "product_ids"

order_schema = OrderSchema()
orders_schema = OrderSchema(many=True)

class CustomerDetailSchema(ma.Schema):
    customer = fields.Nested(CustomerSchema)
    account = fields.Nested(CustomerAccountSchema)
    orders = fields.List(fields.Nested(OrderSchema))

    class Meta:
        fields = "customer", "account", "orders"

customer_detail_schema = CustomerDetailSchema()

class OrderDetailSchema(ma.Schema):
    order = fields.Nested(OrderSchema)
    products = fields.List(fields.Nested(ProductQuantitySchema))
    total_quantity = fields.Integer(validate=validate.Range(min=0))
    total_price = fields.Float(validate=validate.Range(min=0))

    class Meta:
        fields = "order", "total_price", "total_quantity", "products"

order_detail_schema = OrderDetailSchema()


# ===================================== /customers =====================================

@app.route("/customers", methods=["GET"])
def get_customers():
    if name := request.args.get("name"): # Walrus operator!
        with Session(db.engine) as session:
            query = select(Customer).filter(Customer.name.like(f"%{name}%"))
            customers = session.scalars(query).all()
        return customers_schema.jsonify(customers), 200
    else:
        with Session(db.engine) as session:
            query = select(Customer)
            customers = session.scalars(query).all()
        return customers_schema.jsonify(customers), 200

@app.route("/customers/<int:customer_id>", methods=["GET"])
def get_customer(customer_id):
    with Session(db.engine) as session:
        customer = session.get(Customer, customer_id)
        if customer is None:
            return jsonify({"error": "Customer not found..."}), 404
        customer_detail = {
            "customer": customer,
            "account": customer.customer_account,
            "orders": customer.orders
        }
        return customer_detail_schema.jsonify(customer_detail), 200

@app.route("/customers", methods=["POST"])
def add_customer():
    if request.args.get("many") == "true":
        try:
            customers_data = customers_schema.load(request.json)
        except ValidationError as err:
            return jsonify(err.messages), 400
        with Session(db.engine) as session, session.begin():
            session.add_all(Customer(**cust) for cust in customers_data)
        return jsonify({"message": "New customers added successfully!"}), 201
    else:
        try:
            customer_data = customer_schema.load(request.json)
        except ValidationError as err:
            return jsonify(err.messages), 400
        with Session(db.engine) as session, session.begin():
            session.add(Customer(**customer_data))
        return jsonify({"message": "New customer added successfully!"}), 201

@app.route("/customers/<int:customer_id>", methods=["PUT"])
def updated_customer(customer_id):
    with Session(db.engine) as session, session.begin():
        customer = session.get(Customer, customer_id)
        if customer is None:
            return jsonify({"error": "Customer not found..."}), 404
        try:
            customer_data = customer_schema.load(request.json, partial=True)
        except ValidationError as err:
            return jsonify(err.messages), 400
        for field, value in customer_data.items():
            setattr(customer, field, value)
    return jsonify({"message": "Customer details successfully updated"}), 200

@app.route("/customers/<int:customer_id>", methods=["DELETE"])
def delete_customer(customer_id):
    with Session(db.engine) as session, session.begin():
        customer = session.get(Customer, customer_id)
        if customer is None:
            return jsonify({"error": "Customer not found..."}), 404
        session.delete(customer)
    return jsonify({"message": "Customer removed successfully!"})


# ================================= /customer_accounts =================================

@app.route("/customer_accounts", methods=["GET"])
def get_customer_accounts():
    with Session(db.engine) as session:
        query = select(CustomerAccount)
        accounts = session.scalars(query).all()
        return customer_accounts_schema.jsonify(accounts), 200

@app.route("/customer_accounts", methods=["POST"])
def add_customer_account():
    try:
        customer_account_data = customer_account_schema.load(request.json)
    except ValidationError as err:
        return jsonify(err.messages), 400
    with Session(db.engine) as session, session.begin():
        customer_id = customer_account_data["customer_id"]
        customer = session.get(Customer, customer_id)
        if customer is None:
            return jsonify({"error": "Customer must exist before adding account..."}), 404
        account = session.get(CustomerAccount, customer_id)
        if account:
            return jsonify({"error": "Only one account may exist per customer..."}), 400
        username = customer_account_data["username"]
        query = select(CustomerAccount).filter_by(username=username)
        duplicate = session.scalars(query).all()
        if duplicate:
            return jsonify({"error": "Usernames must be unique..."}), 400
        session.add(CustomerAccount(**customer_account_data))
    return jsonify({"message": "New customer account successfully added!"}), 201

@app.route("/customer_accounts/<int:customer_id>", methods=["PUT"])
def update_customer_acount(customer_id):
    with Session(db.engine) as session, session.begin():
        account = session.get(CustomerAccount, customer_id)
        if account is None:
            return jsonify({"message": "Account not found..."}), 404
        try:
            account_data = customer_account_schema.load(request.json, partial=True)
        except ValidationError as err:
            return jsonify(err.messages), 400
        for field, value in account_data.items():
            setattr(account, field, value)
    return jsonify({"Message": "Account was successfully updated!"}), 200
    
@app.route("/customer_accounts/<int:customer_id>", methods=["DELETE"])
def delete_customer_account(customer_id):
    with Session(db.engine) as session, session.begin():
        account = session.get(CustomerAccount, customer_id)
        if account is None:
            return jsonify({"error": "Customer account not found..."}), 404
        session.delete(account)
    return jsonify({"message": "Customer account removed successfully!"})


# ================================== /products =========================================

@app.route("/products", methods=["GET"])
def get_products():
    if name := request.args.get("name"): # Walrus operator!
        with Session(db.engine) as session:
            query = select(Product).filter(Product.name.like(f"%{name}%"))
            products = session.scalars(query).all()
        return products_schema.jsonify(products), 200
    else:
        with Session(db.engine) as session:
            query = select(Product)
            products = session.scalars(query).all()
        return products_schema.jsonify(products)

@app.route("/products", methods=["POST"])
def add_product():
    if request.args.get("many") == "true":
        try:
            products_data = products_schema.load(request.json)
        except ValidationError as err:
            return jsonify(err.messages), 400
        with Session(db.engine) as session, session.begin():
            session.add_all(Product(**prod) for prod in products_data)
        return jsonify({"message": "New products successfully added"}), 201
    else:
        try:
            product_data = product_schema.load(request.json)
        except ValidationError as err:
            return jsonify(err.messages), 400
        with Session(db.engine) as session, session.begin():
            session.add(Product(**product_data))
        return jsonify({"message": "New product successfully added!"}), 201

@app.route("/products/<int:product_id>", methods=["PUT"])
def update_product(product_id):
    with Session(db.engine) as session, session.begin():
        if restock := request.args.get("restock"):
            if not restock.isdigit() or int(restock) <= 0:
                return jsonify({"error": "Restock by positive integer only..."}), 400
            product = session.get(Product, product_id)
            if product is None:
                return jsonify({"error": "Product not found..."}), 404
            product.stock += int(restock)
        else:
            product = session.get(Product, product_id)
            if product is None:
                return jsonify({"error": "Product not found..."}), 404
            try:
                product_data = product_schema.load(request.json, partial=True)
            except ValidationError as err:
                return jsonify(err.messages), 400
            for field, value in product_data.items():
                setattr(product, field, value)
    return jsonify({"message": "Product details successfully updated!"}), 200

@app.route("/products/<int:product_id>", methods=["DELETE"])
def delete_product(product_id):
    with Session(db.engine) as session, session.begin():
        product = session.get(Product, product_id)
        if product is None:
            return jsonify({"error": "Product not found..."}), 404
        query = select(OrderProduct).filter_by(product_id=product_id)
        orders = session.scalars(query).all()
        if orders:
            err = "Cannot delete product with associated orders"
            return jsonify({"error": err}), 400
        session.delete(product)
    return jsonify({"message": "Product successfully deleted!"}), 200


# ===================================== /orders ========================================

@app.route("/orders", methods=["GET"])
def get_orders():
    with Session(db.engine) as session:
        query = select(Order)
        orders = session.scalars(query).all()
    return orders_schema.jsonify(orders)

@app.route("/orders/<int:order_id>", methods=["GET"])
def get_order_details(order_id):
    with Session(db.engine) as session:
        order = session.get(Order, order_id)
        if order is None:
            return jsonify({"message": "Order Not Found"}), 404
        total_price = 0
        total_quantity = 0
        products = []
        for orderproduct in order.products:
            total_quantity += orderproduct.quantity
            total_price += orderproduct.product.price * orderproduct.quantity
            product = {
                "product_id": orderproduct.product.product_id,
                "name": orderproduct.product.name,
                "price": orderproduct.product.price,
                "quantity": orderproduct.quantity
            }
            products.append(product)
        order_detail_data = {
            "order": order,
            "products": products,
            "total_price": total_price,
            "total_quantity": total_quantity
        }
        return order_detail_schema.jsonify(order_detail_data), 200

@app.route("/orders", methods=["POST"])
def add_order():
    try:
        order_data = order_schema.load(request.json)
    except ValidationError as err:
        return jsonify(err.messages), 400
    with Session(db.engine) as session, session.begin():
        customer_id = order_data['customer_id']
        customer = session.get(Customer, customer_id)
        if customer is None:
            err = f"Customer number {customer_id} does not exist..."
            return jsonify({"error": err}), 404
        product_ids = order_data.pop("product_ids")
        order = Order(**order_data)
        session.add(order)
        quantities = Counter(product_ids)
        for product_id in set(product_ids):
            product = session.get(Product, product_id)
            if product is None:
                session.rollback()
                err = f"Product number {product_id} does not exist..."
                return jsonify({"error": err}), 404
            quantity = quantities[product_id]
            if product.stock < quantity:
                session.rollback()
                err = f"Insufficient supply of Product {product_id} to process this order..."
                return jsonify({"error": err}), 400
            product.stock -= quantity
            order.products.append(OrderProduct(product=product, quantity=quantity))
    return jsonify({"message": "New order successfully added!"}), 201

@app.route("/orders/<int:order_id>", methods=["PUT"])
def update_order(order_id):
    with Session(db.engine) as session, session.begin():
        order = session.get(Order, order_id)
        if order is None:
            return jsonify({"message": "Order Not Found"}), 404
        try:
            order_data = order_schema.load(request.json, partial=True)
        except ValidationError as err:
            return jsonify(err.messages), 400
        if "product_ids" in order_data:
            product_ids = order_data.pop("product_ids")
            for orderproduct in order.products:
                orderproduct.product.stock += orderproduct.quantity
                session.delete(orderproduct)
            quantities = Counter(product_ids)
            for product_id in set(product_ids):
                product = session.get(Product, product_id)
                if product is None:
                    session.rollback()
                    err = f"Product number {product_id} does not exist..."
                    return jsonify({"error": err}), 404
                quantity = quantities[product_id]
                if product.stock < quantity:
                    session.rollback()
                    err = f"Insufficient supply of Product {product_id} to process this order..."
                    return jsonify({"error": err}), 400
                product.stock -= quantity
                order.products.append(OrderProduct(product=product, quantity=quantity))
        for field, value in order_data.items():
            setattr(order, field, value)
    return jsonify({"Message": "Order was successfully updated!"}), 200

@app.route("/orders/<int:order_id>", methods=["DELETE"])
def delete_order(order_id):
    with Session(db.engine) as session, session.begin():
        order = session.get(Order, order_id)
        if order is None:
            return jsonify({"error": "Order not found"}), 404
        for orderproduct in order.products:
            orderproduct.product.stock += orderproduct.quantity
        session.delete(order)
    return jsonify({"message": "Order removed successfully!"}), 200


# ========================================= / ==========================================

@app.route("/")
def home():
    return "Let's gooooooooooooooo!"

if __name__ == "__main__":
    app.run(debug=True)