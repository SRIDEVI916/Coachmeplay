from flask import Blueprint, request, jsonify
from datetime import datetime

shop_bp = Blueprint('shop', __name__)

@shop_bp.route('/products', methods=['GET'])
def get_products():
    """Get all products with optional filters"""
    from app import mysql
    
    category = request.args.get('category')
    search = request.args.get('search')
    
    cursor = mysql.connection.cursor()
    
    query = "SELECT * FROM products WHERE 1=1"
    params = []
    
    if category:
        query += " AND category = %s"
        params.append(category)
    
    if search:
        query += " AND (product_name LIKE %s OR description LIKE %s)"
        search_term = f"%{search}%"
        params.extend([search_term, search_term])
    
    query += " ORDER BY is_featured DESC, created_date DESC"
    
    cursor.execute(query, tuple(params) if params else None)
    products = cursor.fetchall()
    cursor.close()
    
    return jsonify({'products': products}), 200

@shop_bp.route('/products/<int:product_id>', methods=['GET'])
def get_product_detail(product_id):
    """Get product details"""
    from app import mysql
    
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM products WHERE product_id = %s", (product_id,))
    product = cursor.fetchone()
    cursor.close()
    
    if product:
        return jsonify({'product': product}), 200
    return jsonify({'error': 'Product not found'}), 404

@shop_bp.route('/cart/add', methods=['POST'])
def add_to_cart():
    """Add item to cart"""
    from app import mysql
    data = request.json
    
    cursor = mysql.connection.cursor()
    
    try:
        # Check if item already in cart
        cursor.execute("""
            SELECT cart_id, quantity FROM cart_items 
            WHERE user_id = %s AND product_id = %s
        """, (data['user_id'], data['product_id']))
        
        existing = cursor.fetchone()
        
        if existing:
            # Update quantity
            new_quantity = existing['quantity'] + data.get('quantity', 1)
            cursor.execute("""
                UPDATE cart_items SET quantity = %s 
                WHERE cart_id = %s
            """, (new_quantity, existing['cart_id']))
        else:
            # Add new item
            cursor.execute("""
                INSERT INTO cart_items (user_id, product_id, quantity)
                VALUES (%s, %s, %s)
            """, (data['user_id'], data['product_id'], data.get('quantity', 1)))
        
        mysql.connection.commit()
        cursor.close()
        
        return jsonify({'message': 'Added to cart'}), 201
    
    except Exception as e:
        mysql.connection.rollback()
        cursor.close()
        return jsonify({'error': str(e)}), 500

@shop_bp.route('/cart/<int:user_id>', methods=['GET'])
def get_cart(user_id):
    """Get user's cart"""
    from app import mysql
    
    cursor = mysql.connection.cursor()
    cursor.execute("""
        SELECT c.cart_id, c.quantity, c.added_at,
               p.product_id, p.product_name, p.price, p.image_url, p.stock_quantity
        FROM cart_items c
        JOIN products p ON c.product_id = p.product_id
        WHERE c.user_id = %s
        ORDER BY c.added_at DESC
    """, (user_id,))
    
    items = cursor.fetchall()
    cursor.close()
    
    total = sum(item['price'] * item['quantity'] for item in items)
    
    return jsonify({'cart': items, 'total': float(total)}), 200

@shop_bp.route('/cart/<int:cart_id>', methods=['DELETE'])
def remove_from_cart(cart_id):
    """Remove item from cart"""
    from app import mysql
    
    cursor = mysql.connection.cursor()
    cursor.execute("DELETE FROM cart_items WHERE cart_id = %s", (cart_id,))
    mysql.connection.commit()
    cursor.close()
    
    return jsonify({'message': 'Item removed'}), 200

@shop_bp.route('/cart/update', methods=['PUT'])
def update_cart_quantity():
    """Update cart item quantity"""
    from app import mysql
    data = request.json
    
    cursor = mysql.connection.cursor()
    cursor.execute("""
        UPDATE cart_items SET quantity = %s 
        WHERE cart_id = %s
    """, (data['quantity'], data['cart_id']))
    
    mysql.connection.commit()
    cursor.close()
    
    return jsonify({'message': 'Cart updated'}), 200

@shop_bp.route('/orders/create', methods=['POST'])
def create_order():
    """Create order from cart"""
    from app import mysql
    import traceback
    
    data = request.json
    print(f"Received order data: {data}")
    
    cursor = mysql.connection.cursor()
    
    try:
        # Get cart items first
        cursor.execute("""
            SELECT c.product_id, c.quantity, p.price, p.stock_quantity
            FROM cart_items c
            JOIN products p ON c.product_id = p.product_id
            WHERE c.user_id = %s
        """, (data['user_id'],))
        
        cart_items = cursor.fetchall()
        print(f"Cart items: {cart_items}")
        
        if not cart_items:
            cursor.close()
            return jsonify({'error': 'Cart is empty'}), 400
        
        # Check stock availability
        for item in cart_items:
            if item['stock_quantity'] < item['quantity']:
                cursor.close()
                return jsonify({'error': f'Not enough stock for product ID {item["product_id"]}'}), 400
        
        # Create order
        print("Inserting order...")
        cursor.execute("""
            INSERT INTO orders (user_id, total_amount, shipping_address, payment_method, status)
            VALUES (%s, %s, %s, %s, 'pending')
        """, (data['user_id'], data['total_amount'], data['shipping_address'], data['payment_method']))
        
        order_id = cursor.lastrowid
        print(f"Order created with ID: {order_id}")
        
        # Add order items and update stock - FIXED: use unit_price instead of price
        for item in cart_items:
            print(f"Adding order item: {item}")
            cursor.execute("""
                INSERT INTO order_items (order_id, product_id, quantity, unit_price)
                VALUES (%s, %s, %s, %s)
            """, (order_id, item['product_id'], item['quantity'], item['price']))
            
            # Update stock
            cursor.execute("""
                UPDATE products 
                SET stock_quantity = stock_quantity - %s 
                WHERE product_id = %s
            """, (item['quantity'], item['product_id']))
        
        # Clear cart
        cursor.execute("DELETE FROM cart_items WHERE user_id = %s", (data['user_id'],))
        
        mysql.connection.commit()
        cursor.close()
        
        return jsonify({'message': 'Order placed successfully', 'order_id': order_id}), 201
    
    except Exception as e:
        mysql.connection.rollback()
        cursor.close()
        error_msg = str(e)
        error_trace = traceback.format_exc()
        print(f"Order creation error: {error_msg}")
        print(f"Full traceback: {error_trace}")
        return jsonify({'error': error_msg}), 500

@shop_bp.route('/orders/<int:user_id>', methods=['GET'])
def get_user_orders(user_id):
    """Get user's orders"""
    from app import mysql
    
    cursor = mysql.connection.cursor()
    cursor.execute("""
        SELECT * FROM orders 
        WHERE user_id = %s 
        ORDER BY order_date DESC
    """, (user_id,))
    
    orders = cursor.fetchall()
    
    for order in orders:
        cursor.execute("""
            SELECT oi.*, p.product_name, p.image_url
            FROM order_items oi
            JOIN products p ON oi.product_id = p.product_id
            WHERE oi.order_id = %s
        """, (order['order_id'],))
        order['items'] = cursor.fetchall()
    
    cursor.close()
    
    return jsonify({'orders': orders}), 200

# ========== RENTAL ROUTES ==========

@shop_bp.route('/rentals/create', methods=['POST'])
def create_rental():
    """Create a rental booking"""
    from app import mysql
    import traceback
    from datetime import datetime, timedelta
    
    data = request.json
    print(f"Rental data: {data}")
    
    cursor = mysql.connection.cursor()
    
    try:
        # Check product availability
        cursor.execute("""
            SELECT available_for_rent, rental_price_daily, rental_price_weekly
            FROM products 
            WHERE product_id = %s AND is_rentable = TRUE
        """, (data['product_id'],))
        
        product = cursor.fetchone()
        
        if not product:
            cursor.close()
            return jsonify({'error': 'Product not available for rent'}), 400
        
        if product['available_for_rent'] < 1:
            cursor.close()
            return jsonify({'error': 'No items available for rent'}), 400
        
        # Calculate rental amount
        duration = data['rental_duration_days']
        rental_type = data['rental_type']
        
        if rental_type == 'daily':
            total_amount = float(product['rental_price_daily']) * duration
        else:  # weekly
            weeks = duration / 7
            total_amount = float(product['rental_price_weekly']) * weeks
        
        # Calculate dates
        start_date = datetime.strptime(data['rental_start_date'], '%Y-%m-%d')
        end_date = start_date + timedelta(days=duration)
        
        # Create rental
        cursor.execute("""
            INSERT INTO rentals 
            (user_id, product_id, rental_start_date, rental_end_date, 
             rental_duration_days, rental_type, total_amount, deposit_amount, 
             delivery_address, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'active')
        """, (
            data['user_id'],
            data['product_id'],
            start_date.date(),
            end_date.date(),
            duration,
            rental_type,
            total_amount,
            data.get('deposit_amount', 0),
            data['delivery_address']
        ))
        
        rental_id = cursor.lastrowid
        
        # Update available count
        cursor.execute("""
            UPDATE products 
            SET available_for_rent = available_for_rent - 1
            WHERE product_id = %s
        """, (data['product_id'],))
        
        mysql.connection.commit()
        cursor.close()
        
        return jsonify({
            'message': 'Rental booked successfully',
            'rental_id': rental_id,
            'total_amount': total_amount
        }), 201
    
    except Exception as e:
        mysql.connection.rollback()
        cursor.close()
        print(f"Rental error: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@shop_bp.route('/rentals/<int:user_id>', methods=['GET'])
def get_user_rentals(user_id):
    """Get user's rental history"""
    from app import mysql
    
    cursor = mysql.connection.cursor()
    cursor.execute("""
        SELECT r.*, p.product_name, p.image_url
        FROM rentals r
        JOIN products p ON r.product_id = p.product_id
        WHERE r.user_id = %s
        ORDER BY r.created_at DESC
    """, (user_id,))
    
    rentals = cursor.fetchall()
    cursor.close()
    
    return jsonify({'rentals': rentals}), 200

@shop_bp.route('/rentals/<int:rental_id>/return', methods=['PUT'])
def return_rental(rental_id):
    """Mark rental as returned"""
    from app import mysql
    
    cursor = mysql.connection.cursor()
    
    try:
        # Get rental details
        cursor.execute("""
            SELECT product_id FROM rentals WHERE rental_id = %s
        """, (rental_id,))
        
        rental = cursor.fetchone()
        
        if not rental:
            cursor.close()
            return jsonify({'error': 'Rental not found'}), 404
        
        # Update rental status
        cursor.execute("""
            UPDATE rentals 
            SET status = 'completed'
            WHERE rental_id = %s
        """, (rental_id,))
        
        # Return item to available pool
        cursor.execute("""
            UPDATE products 
            SET available_for_rent = available_for_rent + 1
            WHERE product_id = %s
        """, (rental['product_id'],))
        
        mysql.connection.commit()
        cursor.close()
        
        return jsonify({'message': 'Rental returned successfully'}), 200
    
    except Exception as e:
        mysql.connection.rollback()
        cursor.close()
        return jsonify({'error': str(e)}), 500

