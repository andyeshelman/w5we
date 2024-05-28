# eStore Functionality

## Customers

### GET

`/customers`  
Displays all customers

`/customers?name=<string>`  
Displays only those customers whose name contains the given string

`/customers/<int:customer_id>`  
Displays details of the customer with the given id,
including account details and logged orders

### POST

`/customers`  
```
{
    "name": string,
    "email": string,
    "phone": string
}
```

`/customers?many=true`  
Accepts an array of objects formatted as above
and adds them all

### PUT

`/customers/<int:customer_id>`  
Accepts any subset of customer fields and updates the
customer with the given id

### DELETE

`/customers/<int:customer_id>`  
Deletes customer with given id

## Accounts

### GET

`/customer_accounts`  
Displays all customer accounts

### POST

`/customers_accounts`  
```
{
    "customer_id": integer,
    "username": string,
    "password": string
}
```

### PUT

`/customer_accounts/<int:customer_id>`  
Accepts any subset of customer account fields and updates

### DELETE

`/customer_accounts/<int:customer_id>`  
Deletes customer account with given id

## Products

### GET

`/products`  
Displays all products

`/products?name=<string>`  
Displays only those products whose name contains the given string

### POST

`/products`  
```
{
    "name": string,
    "price": float,
    "stock": integer
}
```

`/products?many=true`  
Accepts an array of products formatted as above
and adds them all

### PUT

`/products/<int:product_id>`  
Accepts any subset of product fields and updates the
customer with the given id

`/products/<int:product_id>?restock=<int>`  
Adds restock value to the stock of the given product

### DELETE

`/products/<int:product_id>`  
Deletes product with given id

## Orders

### GET

`/orders`  
Displays all orders

`/orders/<int:order_id>`  
Displays details of the order with the given id,
including total price, total number of items
and all associated products

### POST

`/orders`  
```
{
    "customer_id": integer,
    "date": YYYY-MM-DD,
    "products": array of product ids
}
```
The number of occurances of a product in the array
is the quantity ordered

### PUT

`/orders/<int:order_id>`  
Accepts any subset of order fields and updates the
order with the given id

### DELETE

`/orders/<int:order_id>`  
Deletes order with given id