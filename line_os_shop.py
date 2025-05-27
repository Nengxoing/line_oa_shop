from flask import Flask, render_template, request, redirect, url_for, session, flash,send_from_directory,make_response,jsonify,after_this_request
from ecom import app
#getcursor
from dbconn import *
#getcursor6
# from dbconn_ods import *
# from dbconn_biotime import *
import datetime

from datetime import datetime, date,timedelta
import os
import pytz
from pickle import TRUE
import urllib.request
from werkzeug.utils import secure_filename
import random
import string
import requests 
import json
# from chatbot_linelink import *

import sqlite3
from decimal import Decimal

# *********************************** Sqlite start ***********************************
# Register adapter (Decimal → str)
sqlite3.register_adapter(Decimal, lambda d: str(d))

# Register converter (str → Decimal)
sqlite3.register_converter("DECIMAL", lambda s: Decimal(s.decode()))

def drop_table_receive_selected_items():
    conn = sqlite3.connect("line_oa_shop.db")
    cur = conn.cursor()

    cur.execute("DROP TABLE IF EXISTS addToCard")

    conn.commit()
    conn.close() 
drop_table_receive_selected_items()

def create_table_receive_selected_items():
    conn = sqlite3.connect("line_oa_shop.db")
    cur = conn.cursor()
    
    cur.execute("""
        CREATE TABLE IF NOT EXISTS addToCard (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            market_code TEXT,
            market_name TEXT,
            qty TEXT,
            sale_price TEXT,
            amount TEXT,
            regular_price TEXT,
            image TEXT,
            emp_code TEXT,
            unit_code TEXT,
            average_cost TEXT
        )
    """)
 
    conn.commit() 
    conn.close()  
create_table_receive_selected_items()
# *********************************** Sqlite end ***********************************

@app.route("/line_oa_shop")
def line_oa_shop():

    # emp_code = session.get("custcode")
    emp_code = '2078153732'
    print("\nemp_code:", emp_code)

    if emp_code is None:
        return redirect("/login")

    if emp_code is None:
        return redirect("/login")

    with getcursor() as cur:
        cur.execute("""
            SELECT 
                code,
                name_market,
                unit_cost AS unit,
                item_brand,
                ROUND(COALESCE(c.sale_price1, 0) * 1.15) AS regular_price,
                COALESCE(c.sale_price1, 0) AS sale_price,
                COALESCE(average_cost, 0) AS average_cost,
                url_image
            FROM 
                ic_inventory a
            LEFT JOIN 
                product_image b 
                ON b.ic_code = a.code 
                AND line_number = 1 
            LEFT JOIN 
                ic_inventory_price c 
                ON c.ic_code = a.code 
                AND currency_code = '02' 
                AND cust_group_1 = '101' 
                AND cust_group_2 = '10101' 
                AND to_date > CURRENT_DATE 
                AND from_qty = 1 
            WHERE 
                name_market != ''
            ORDER BY 
                name_market
        """)
        products_data = cur.fetchall()

        cur.execute("SELECT DISTINCT item_brand FROM ic_inventory WHERE name_market != '' ORDER BY item_brand")
        item_brand = cur.fetchall()
        # print("\nitem_brand:", item_brand)

    return render_template("line_oa/line_os_shop/line_os_shop.html", products_data=products_data, item_brand=item_brand)

@app.route("/filter_products")
def filter_products():
    small_price = request.args.get("smallPrice", default="0").replace(",", "").strip()
    big_price = request.args.get("bigPrice", default="9999999").replace(",", "").strip()
    brand = request.args.get("brand", type=str, default="")

    print("\nsmall_price:", small_price)
    print("\nbig_price:", big_price)
    print("\nbrand:", brand)

    # แปลงให้เป็น int ถ้าเป็นตัวเลข
    small_price = int(small_price) if small_price.isdigit() else 0
    big_price = int(big_price) if big_price.isdigit() else 9999999

    with getcursor() as cur:
        query = """
            SELECT 
                code,
                name_market,
                unit_cost AS unit ,
                item_brand,
                COALESCE(c.sale_price1, 0) AS regular_price,
                COALESCE(c.sale_price1, 0) AS sale_price,
                COALESCE(average_cost, 0) AS average_cost,
                url_image
            FROM 
                ic_inventory a
            LEFT JOIN 
                product_image b 
                ON b.ic_code = a.code 
                AND line_number = 1 
            LEFT JOIN 
                ic_inventory_price c 
                ON c.ic_code = a.code 
                AND currency_code = '02' 
                AND cust_group_1 = '101' 
                AND cust_group_2 = '10101' 
                AND to_date > CURRENT_DATE 
                AND from_qty = 1 
            WHERE 
                name_market != ''
                AND COALESCE(c.sale_price1, 0) >= %s
                AND COALESCE(c.sale_price1, 0) <= %s
        """
        params = [small_price, big_price]

        if brand:
            query += " AND item_brand = %s"
            params.append(brand)

        query += " ORDER BY sale_price ASC"

        cur.execute(query, params)
        rows = cur.fetchall()
        
        # ลองพิมพ์ข้อมูลที่ได้จาก rows
        print("\nrows:", rows)

        # ผลลัพธ์ที่ได้จาก fetchall() จะเป็น RealDictRow แล้ว
        result = [dict(row) for row in rows]  # ไม่ต้องใช้ zip อีกแล้ว

        print("\nresult:", result)

    return jsonify(products=result)

@app.route("/addToCard", methods=["POST"])
def addToCard():

    # emp_code = session.get("custcode")
    emp_code = '2078153732'
    print("\nemp_code:", emp_code)

    if emp_code is None:
        return redirect("/login")

    data = request.get_json()
    print("🛒 Received Data:", data)

    market_code = data.get("code")
    market_name = data.get("name")
    sale_price = data.get("sale_price")
    image = data.get("image")  # รับ path ของรูป
    qty = data.get("qty")

    amount = int(qty) * int(sale_price)
    print("\namount:", amount)

    # แยกชื่อไฟล์จาก path
    image_name = os.path.basename(image)  # จะได้แค่ชื่อไฟล์ เช่น '110301-0003_1.jpg'

    with getcursor() as cur:
        cur.execute("SELECT average_cost FROM ic_inventory WHERE code = %s", (market_code,))
        row = cur.fetchone()
        average_cost = row['average_cost']
        print("\naverage_cost:", average_cost)

        cur.execute("""
            SELECT 
                code,
                name_market,
                unit_cost AS unit ,
                item_brand,
                COALESCE(c.sale_price1, 0) AS regular_price,
                COALESCE(c.sale_price1, 0) AS sale_price,
                COALESCE(average_cost, 0) AS average_cost,
                url_image
            FROM 
                ic_inventory a
            LEFT JOIN 
                product_image b 
                ON b.ic_code = a.code 
                AND line_number = 1 
            LEFT JOIN 
                ic_inventory_price c 
                ON c.ic_code = a.code 
                AND currency_code = '02' 
                AND cust_group_1 = '101' 
                AND cust_group_2 = '10101' 
                AND to_date > CURRENT_DATE 
                AND from_qty = 1 
            WHERE
                code = %s
        """, (market_code,))
        row = cur.fetchone()
        unit_code = row['unit']
        print("\nunit_code:", unit_code)

    conn = sqlite3.connect("line_oa_shop.db")
    cur = conn.cursor()

    try:
        cur.execute("SELECT qty FROM addToCard WHERE emp_code = ? AND market_code = ?", (emp_code, market_code))
        existing = cur.fetchone()

        if existing:

            new_qty = existing[0]
            qty_2 = int(new_qty) + int(qty)
            amount_2 = int(qty_2) * int(sale_price)
            print("\namount_2:", amount_2)

            cur.execute(""" 
                UPDATE addToCard SET qty = qty + ?, amount = ?
                WHERE emp_code = ? AND market_code = ?
            """, (qty, amount_2, emp_code, market_code))
        else:
            cur.execute("""
                INSERT INTO addToCard (
                    market_code,
                    market_name, 
                    sale_price, 
                    amount,
                    image,
                    emp_code,
                    qty,
                    unit_code,
                    average_cost
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (market_code, market_name, sale_price, amount, image_name, emp_code, qty, unit_code, average_cost))

        conn.commit()
        response = {"status": "success", "message": "Item added to cart", "data": data}

    except Exception as e:
        conn.rollback()
        response = {"status": "error", "message": str(e)}

    finally:
        conn.close()

    return jsonify(response)

@app.route("/getAddToCard", methods=["GET"])
def getAddToCard():
    
    # emp_code = session.get("custcode")
    emp_code = '2078153732'
    print("\nemp_code:", emp_code)

    if emp_code is None:
        return redirect("/login")
    
    conn = sqlite3.connect("line_oa_shop.db")
    cur = conn.cursor()

    cur.execute("SELECT market_code, market_name, sale_price, image, qty FROM addToCard WHERE emp_code = ?", (emp_code,))

    cart_items = cur.fetchall()

    conn.close()

    cart_data = []
    for item in cart_items:
        cart_data.append({
            "market_code": item[0],
            "name": item[1],
            "sale_price": item[2],
            "image": item[3],
            "qty": item[4]
        })
    
    # print("\ncart_data:", cart_data)

    return jsonify({"status": "success", "cart": cart_data})

@app.route("/deleteCard", methods=["POST"])
def deleteCard():
    
    # emp_code = session.get("custcode")
    emp_code = '2078153732'
    print("\nemp_code:", emp_code)

    if emp_code is None:
        return redirect("/login")
    
    data = request.get_json()
    print("🛒 Received Data:", data)
    
    market_code = data.get("code")

    conn = sqlite3.connect("line_oa_shop.db")
    cur = conn.cursor()

    cur.execute("DELETE FROM addToCard WHERE emp_code = ? AND market_code = ?", (emp_code, market_code))
    conn.commit()
    conn.close()

    return jsonify({"status": "deleted"})

@app.route("/card_detail")
def card_detail():
    return render_template("line_oa/line_os_shop/card_detail.html")

def generate_doc_no():
    prefix = 'CAON'
    today = datetime.now()
    date_part = today.strftime('%y%m%d')  # YYMMDD
    base_code = f'{prefix}{date_part}'   # CAON250507

    with getcursor() as cur:
        # เช็ค max doc_no จาก 2 ตารางที่ขึ้นต้นด้วย base_code
        cur.execute("""
            SELECT MAX(doc_no) FROM (
                SELECT doc_no FROM ic_trans WHERE doc_no LIKE %s
                UNION ALL
                SELECT doc_no FROM ic_trans_detail WHERE doc_no LIKE %s
            ) AS combined
        """, (base_code + '%', base_code + '%'))

        row = cur.fetchone()
        last_doc = row['max'] if row and row['max'] else None

        if last_doc:
            # ดึงลำดับเลขท้าย แล้ว +1
            last_number = int(last_doc[-4:])
            new_number = last_number + 1
        else:
            new_number = 1

        # สร้าง doc_no ใหม่
        new_doc_no = f'{base_code}{new_number:04d}'
        return new_doc_no
    
@app.route("/card_detail_get", methods=["GET"])
def card_detail_get():
    
    # emp_code = session.get("custcode")
    emp_code = '2078153732'
    print("\nemp_code:", emp_code)

    if emp_code is None:
        return redirect("/login")

    conn = sqlite3.connect("line_oa_shop.db")
    cur = conn.cursor()

    cur.execute("SELECT market_code, market_name, sale_price, image, qty FROM addToCard WHERE emp_code = ?", (emp_code,))
    cart_items = cur.fetchall()
    conn.close()
    print("\ncart_items:", cart_items)

    doc_no = generate_doc_no()
    print("\n🔖 doc_no:", doc_no)

    cart_data = []
    for item in cart_items:
        cart_data.append({
            "market_code": item[0],
            "name": item[1],
            "sale_price": item[2],
            "image": item[3],
            "qty": item[4]
        })
    print("\ncart_data:", cart_data)

    with getcursor() as cur:
        cur.execute("SELECT code, name_1, telephone, address FROM ar_customer WHERE code = %s", (emp_code,))
        user_data = cur.fetchall()
        print("\nuser_data:", user_data)

    if user_data and len(user_data) > 0:
        user_row = user_data[0]
        user_info = {
            "code": user_row['code'],
            "name": user_row['name_1'],
            "phone": user_row['telephone'],
            "address": user_row['address']
        }
    else:
        user_info = {
            "code": "---",
            "name": "---",
            "phone": "---",
            "address": "---"
        }
    print("\nuser_data:", user_data)

    return jsonify({
        "status": "success",
        "cart": cart_data,
        "user": user_info,
        "doc_no": doc_no
    })

@app.route("/deleteItemCard", methods=["POST"])
def deleteItemCard():
    
    # emp_code = session.get("custcode")
    emp_code = '2078153732'
    print("\nemp_code:", emp_code)

    if emp_code is None:
        return redirect("/login")
    
    data = request.get_json()
    print("🛒 Received Data:", data)
    
    market_code = data.get("code")

    conn = sqlite3.connect("line_oa_shop.db")
    cur = conn.cursor()

    cur.execute("DELETE FROM addToCard WHERE emp_code = ? AND market_code = ?", (emp_code, market_code))
    conn.commit()
    conn.close()

    return jsonify({"status": "deleted"})

@app.route("/product_detail")
def product_detail():
    code = request.args.get("code")  # รับ code จาก URL

    print("\ncode:", code)

    if not code:
        return "Product code is missing", 400

    with getcursor() as cur:
        cur.execute("""
            SELECT 
                code,
                name_market,
                unit_cost,
                COALESCE(c.sale_price1, 0) AS regular_price,
                url_image,
                COALESCE(c.sale_price1, 0) AS sale_price,
                COALESCE(average_cost, 0) AS average_cost,
                item_brand,
                description,
                CASE 
                    WHEN balance_qty > 0 THEN 'ມີສະຕອກ' 
                    ELSE 'preorder' 
                END AS stock,
                name_1
            FROM 
                ic_inventory a
            LEFT JOIN 
                product_image b 
                ON b.ic_code = a.code AND line_number = 1
            LEFT JOIN 
                ic_inventory_price c 
                ON c.ic_code = a.code 
                AND currency_code = '02' 
                AND cust_group_1 = '101' 
                AND cust_group_2 = '10102' 
                AND to_date > CURRENT_DATE 
                AND from_qty = 1
            WHERE 
                a.code = %s;
        """, (code,))
        row = cur.fetchone()

        if row:
            product_data = dict(row)

            if not product_data.get("description"):
                product_data["description"] = "ບໍ່ມີລາຍລະອຽດໂດຍຫຍໍ້"
        else:
            product_data = None

        print("\nproduct_data:", product_data)

        cur.execute(""" 
            SELECT 
                split_part(name_1, ':', 1) AS name_1, 
                CASE 
                    WHEN split_part(name_1, ':', 2) = ' ' THEN '-' 
                    ELSE split_part(name_1, ':', 2) 
                END AS name_2 
            FROM ic_name_short 
            WHERE ic_code = %s 
            ORDER BY roworder
        """, (code,))
        product_detail = cur.fetchall()
        print("\nproduct_detail:", product_detail)

        cur.execute("SELECT description FROM ic_description WHERE ic_code = %s ", (code,))
        product_des = cur.fetchall()
        print("\nproduct_des:", product_des)

        cur.execute("""
            SELECT 
                code,
                name_market,
                COALESCE(c.sale_price1, 0) AS sale_price,
                COALESCE(c.sale_price1, 0) AS regular_price,
                url_image
            FROM ic_inventory a
            LEFT JOIN product_image b ON b.ic_code = a.code AND line_number = 1
            LEFT JOIN ic_inventory_price c 
                ON c.ic_code = a.code 
                AND currency_code = '02' 
                AND cust_group_1 = '101' 
                AND cust_group_2 = '10102' 
                AND to_date > CURRENT_DATE 
                AND from_qty = 1
            WHERE 
                a.code != %s AND a.item_brand = %s
            LIMIT 4;
        """, (code, product_data.get("item_brand")))

        related_products = cur.fetchall()
        print("\nrelated_products:", related_products)

    return render_template(
        "line_oa/line_os_shop/product_detail.html",
        product_data=product_data,
        product_detail=product_detail,
        product_des=product_des,
        related_products=related_products
    )

def card_2(): 
    
    # emp_code = session.get("custcode")
    emp_code = '2078153732'
    print("\nemp_code:", emp_code)

    if emp_code is None:
        return redirect("/login")
    
    conn = sqlite3.connect("line_oa_shop.db")
    cur = conn.cursor()

    cur.execute("SELECT market_code, market_name, qty, sale_price, amount, regular_price, image, emp_code, unit_code, average_cost FROM addToCard WHERE emp_code = ?",(emp_code,))
    rows = cur.fetchall()
    print("\nfunction card():", rows)
    return rows

@app.route('/submit_order/<doc_no>', methods=['POST'])
def submit_order(doc_no):
    data = request.get_json()
    print("\n ************ data ************ :", data)
    
    receiver_code = data.get('receiverCode')
    print("\nreceiver_code:", receiver_code)

    receiver_name = data.get('receiverName')
    receiver_phone = data.get('receiverPhone')
    receiver_address = data.get('receiverAddress')
    shipping_type = data.get('shippingType')
    products = data.get('products', [])
    total_product_price = data.get('allProductsPrice')
    shipping_price = data.get('shippingPrice')
    total_price = data.get('allPrice')
    doc_date = datetime.now().date()
    
    # emp_code = session.get("custcode")
    emp_code = '2078153732'
    print("\nemp_code:", emp_code)

    if emp_code is None:
        return redirect("/login")
    
    with getcursor() as cur:
        cur.execute("""select COALESCE(exchange_rate_present,0) as get_rate from erp_currency where code='02'""")
        get_rate = cur.fetchone()
        exchange_rate=float(get_rate["get_rate"])
        print("\nexchange_rate:", exchange_rate)

    vat_type = 2
    branch_code = '99'
    total_value = 0
    logis_price = '00'
    vat_amount = 0
    total_after_vat = 0
    total_before_vat = 0
    doc_format_code = 'CAE'
    inquiry_type = 1
    remark_5 = 'web'
    vat_rate = 10
    currency_code = '02'

    sum_amount = 0

    for data in products:
        market_code = data['code']

        conn = sqlite3.connect("line_oa_shop.db")
        cur = conn.cursor()

        cur.execute("SELECT amount FROM addToCard WHERE emp_code = ? AND market_code = ?", (emp_code, market_code))
        rows = cur.fetchall()
        print("\naddToCard:", rows)

        for row in rows:
            sum_amount += int(row[0])

    print("\n✅ sum_amount รวมทั้งสิ้น:", sum_amount)
        
    total_amount_2 = sum_amount + float(logis_price)
    print("\ntotal_amount_2:", total_amount_2)

    total_value_2 = total_amount_2
    print("\ntotal_value_2:", total_value_2)

    total_value = total_value_2*exchange_rate
    print("\ntotal_value:", total_value)

    total_amount = total_amount_2*exchange_rate
    print("\ntotal_amount:", total_amount)

    dateTimeObj = datetime.now()
    doc_time = dateTimeObj.strftime("%H:%M")
    # creator_code = session.get("custcode")
    creator_code = '2078153732'

    print("\n📦 ORDER RECEIVED:")
    print("\nรหัส:", receiver_code)
    print("\nชื่อ:", receiver_name)
    print("\nเบอร์:", receiver_phone)
    print("\nที่อยู่:", receiver_address)
    print("\nรูปแบบการจัดส่ง:", shipping_type)
    print("\nสินค้าที่สั่ง:")
    for product in products:
        print(f" - {product['code']} | {product['name']} | {product['qty']} ชิ้น | {product['price']} KIP | รูปภาพ: {product['image']}")
    print("\nราคารวมสินค้า:", total_product_price)
    print("\nค่าจัดส่ง:", shipping_price)
    print("\nวันที่ส่ง:", doc_date)
    print("\nรวมทั้งสิ้น:", total_price)
    print("\n")

    with getcursor() as cur:
        try:
            cur.execute("""
                INSERT INTO ic_trans (
                    trans_type,
                    trans_flag,
                    doc_date,
                    doc_no,
                    vat_type,
                    cust_code,
                    branch_code,
                    total_value,
                    total_vat_value,
                    total_after_vat,
                    total_amount,
                    total_before_vat,
                    doc_time,
                    doc_format_code,
                    creator_code,
                    inquiry_type,
                    table_number,
                    remark_5,
                    exchange_rate,
                    total_value_2,
                    total_amount_2,
                    vat_rate,
                    currency_code
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                            %s, %s, %s)
            """, (
                2,
                34,
                doc_date, 
                doc_no,
                vat_type,
                receiver_code,
                '99',
                total_value,
                vat_amount,
                total_after_vat,
                total_amount,
                total_before_vat,
                doc_time,
                'CAE',
                receiver_code,
                1,
                len(card_2()),
                'web',
                exchange_rate,
                total_value_2,
                total_amount_2,
                vat_rate,
                '02'
            ))
            print("✅ บันทึกข้อมูลลง ic_trans สำเร็จแล้ว!")
        except Exception as e:
            print(f"❌ Insert in to ic_trans faild: {product_code}: {e}")
        
        for row in card_2():
            product_code = row[0]
            product_name = row[1]
            unit_code = row[8]
            qty = float(row[2])
            price_2 = float(row[3])
            sum_amount_2 = float(row[4])

            price = round(price_2 * exchange_rate, 3)
            sum_amount = round(sum_amount_2 * exchange_rate, 3)
            
            cur.execute("""
                SELECT ROUND(average_cost, 4) AS average_cost
                FROM sml_ic_function_stock_balance(%s, %s)
                LIMIT 1
            """, (doc_date, product_code))
            get_cost = cur.fetchone()
            average_cost = float(get_cost["average_cost"])
            sum_of_cost = qty * average_cost

            try:
                cur.execute("""
                    INSERT INTO ic_trans_detail(
                        trans_type, trans_flag, doc_date, doc_no, cust_code,
                        item_code, item_name, unit_code, qty, price,
                        sum_amount, branch_code, wh_code, shelf_code, calc_flag,
                        doc_time, inquiry_type, stand_value, divide_value,
                        doc_date_calc, doc_time_calc, total_vat_value, vat_type,
                        sum_amount_exclude_vat, price_exclude_vat, price_2, sum_amount_2,
                        average_cost, sum_of_cost, average_cost_1, sum_of_cost_1
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    2, 34, doc_date, doc_no, emp_code,
                    product_code, product_name, unit_code, qty, price,
                    sum_amount, '99', '0000', '000000', -1,
                    doc_time, 1, 1, 1,
                    doc_date, doc_time, 0, 1,
                    sum_amount_2, sum_amount_2, price_2, sum_amount_2,
                    average_cost, sum_of_cost, average_cost, sum_of_cost
                ))
                print("✅ บันทึกข้อมูลลง ic_trans_detail สำเร็จแล้ว!")
            except Exception as e:
                print(f"❌ Insert failed for {product_code}: {e}")

    return jsonify({
        "status": "success",
        "message": "Saved data success!",
        "doc_no": doc_no
    })

# *********************************************** Old route from shop.py start ! ***********************************************
@app.route('/paymentpage_mb/<doc_no>')
def paymentpage_mb(doc_no):
    with getcursor() as cur: 
        cur.execute("""
            SELECT 
                trans_type,    -- 2
                trans_flag,    -- 34
                doc_no,        -- ເລກສັ່ງຊື້
                cust_code,     -- ລະຫັດລູກຄ້າ
                inquiry_type,  -- ປະເພດການຈັດສົ່ງ
                item_code,     -- ລະຫັດສິນຄ້າ
                item_name,     -- ຊື່ສິນຄ້າ
                unit_code,     -- ຫົວໜ່ວຍ
                qty,           -- ຈຳນວນ
                price,         -- ລາຄາ
                price_2,
                doc_date
            FROM
                ic_trans_detail
            WHERE
                doc_no = %s
            LIMIT 10
        """, (doc_no,))

        product_data = cur.fetchall();
        print("\nproduct_data:", product_data)

        sum_total = 0
        for item in product_data:
            qty = item['qty']
            price = item['price']
            price_2 = item['price_2']
            sum_total += round(qty * price, 3)

            print("\nqty:", qty)
            print("\nprice:", price)
            print("\nprice_2:", price_2)
            print("\nsum_total:", sum_total)
            
        amount_to_send = int(round(sum_total * 1000))

        print("💰 หน่วยย่อยที่ส่งออก:", amount_to_send)
        
        cart_items = card()
        countdata = len(cart_items)
        
        sum_amount = sum(item[5] for item in cart_items)
        
        sql_h = """
            SELECT
                doc_no,
                TO_CHAR(doc_date, 'DD-MM-YYYY HH:MI:SS') AS doc_date,
                total_value,
                0 AS logis_amount,
                total_amount,
                0 AS payment,
                (SELECT COUNT(doc_no) FROM ic_trans_detail WHERE doc_no = a.doc_no) AS item_count,
                TO_CHAR(total_amount, '999,999,999,999') AS total_amount_format,
                total_amount_2,
                TO_CHAR(total_amount_2, '999,999,999,999') AS total_amount_2_format
            FROM
                ic_trans a
            WHERE
                doc_no = %s
        """
        cur.execute(sql_h, (doc_no,))
        bill_h = cur.fetchone()

        # total_amount = bill_h["total_amount_2"]
        total_amount = bill_h["total_amount_2"] if bill_h and "total_amount_2" in bill_h else 0
        total_amount_format = bill_h["total_amount_2_format"] if bill_h and "total_amount_2" in bill_h else 0

        print("\ntotal_amount:", total_amount)
        print("\ntotal_amount_format:", total_amount_format)

    return render_template(
        "line_oa/line_os_shop/payment_mb.html",
        group_sub=groupsub(),
        group_sub_2=groupsub2(),
        top_banner_desktop=gettopbanner(),
        rows=cart_items,
        sum_amount=sum_amount,
        countdata=countdata,
        islogin=session.get("name"),
        bill_h=bill_h,
        accountname=session.get("name"),
        mydict=lang_dict(),
        mylang=session.get("lang"),
        current_path="carddetail",
        total_amount=total_amount,
        total_amount_format=total_amount_format,
        sum_total=amount_to_send
    )

@app.route('/thankyoupage/<doc_no>')
def thankyoupage(doc_no):
    if not session.get("name"):
        return redirect("/login")
    with getcursor() as cur:
        sql_head = """SELECT  doc_no, doc_date, total_value, 0 as logis_amount, total_amount, 0 as payment, doc_time,cust_code,doc_format_code,
                    (select COALESCE(exchange_rate_present,0) from erp_currency where code='02' limit 1) as exchange_lak,total_amount_2
                    FROM ic_trans a where doc_no=%s"""
        cur.execute(sql_head, (doc_no,))
        bill_h = cur.fetchone()
        print("\nbill_h:", bill_h)

        sql_h="""
        insert into cb_trans
        (trans_type,trans_flag,doc_date,doc_no,total_amount,total_net_amount,tranfer_amount,total_amount_pay,doc_time,ap_ar_code,pay_type,doc_format_code)
        values
        (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """
        cur.execute(sql_h, (2,44,bill_h["doc_date"],bill_h["doc_no"],bill_h["total_amount"],bill_h["total_amount"],bill_h["total_amount"],bill_h["total_amount"],bill_h["doc_time"],bill_h["cust_code"],1,bill_h["doc_format_code"]))


        sql_detail="""
        insert into cb_trans_detail
        (trans_type,trans_flag,doc_date,doc_no,trans_number,bank_code,bank_branch,exchange_rate,amount,chq_due_date,doc_type,doc_time,currency_code,sum_amount_2)
        values
        (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """
        cur.execute(sql_detail, (2,44,bill_h["doc_date"],bill_h["doc_no"],'1010201TEST','BCEL001','BCEL01',bill_h["exchange_lak"],bill_h["total_amount_2"],bill_h["doc_date"],1,bill_h["doc_time"],'02',bill_h["exchange_lak"]*bill_h["total_amount"]))

        cur.execute("""UPDATE ic_trans set trans_flag=44 where doc_no=%s""", (bill_h["doc_no"],))
        cur.execute("""UPDATE ic_trans_detail set trans_flag=44 where doc_no=%s""", (bill_h["doc_no"],))
        # cur.execute("""update ic_inventory a set
        # book_out_qty=book_out_qty-b.qty
        # from 
        # (select item_code,sum(qty) as qty from ic_trans_detail where doc_no=%s group by item_code) as b
        # where 
        # a.code in (select distinct item_code from ic_trans_detail where doc_no=%s)
        # and a.code=b.item_code""", (bill_h["doc_no"],bill_h["doc_no"]))

        # Clear shop card
        conn = sqlite3.connect("line_oa_shop.db")
        cur = conn.cursor()
        
        # cust_code = session.get("custcode")
        cust_code = '2078153732'
        print("\ncustcode:", cust_code)
        
        cur.execute("DELETE FROM addToCard WHERE emp_code = ?", (cust_code,))
        conn.commit()
        conn.close()

        print("\nFrom '/thankyoupage' Delete addToCard complete !!!")
        
    return redirect(url_for('thankyou_page', id=doc_no))

@app.route('/thankyou_page/<id>')
def thankyou_page(id):
    if not session.get("name"):
        return redirect("/login")
    return render_template("thankyou.html", tracking_number=id)

@app.route('/line_oa_order_list')
def line_oa_order_list():

    # cust_code = session.get("custcode")
    cust_code = '2078153732'
    print("\ncustcode:", cust_code)

    with getcursor() as cur:
        cur.execute("""
            SELECT 
                a.trans_flag, 
                a.doc_date, 
                a.doc_no, 
                a.cust_code, 
                a.total_amount_2,
                SUM(b.qty) AS total_qty
            FROM 
                ic_trans a
            LEFT JOIN 
                ic_trans_detail b ON a.doc_no = b.doc_no
            WHERE 
                a.trans_flag = '44'
                AND a.cust_code = %s
            GROUP BY 
                a.trans_flag, 
                a.doc_date, 
                a.doc_no, 
                a.cust_code, 
                a.total_amount_2;
        """, (cust_code,))

        order_list = cur.fetchall()
        print("\norder_list:", order_list)

    return render_template("line_oa/line_os_shop/line_oa_order_list.html", order_list=order_list)
# *********************************************** Old route from shop.py end ! ***********************************************

@app.route('/line_oa_order_detail/<doc_no>')
def line_oa_order_detail(doc_no):

    print("\ndoc_no:", doc_no)

    # cust_code = session.get("custcode")
    cust_code = '2078153732'
    print("\ncustcode:", cust_code)

    with getcursor() as cur:
        cur.execute("""
            SELECT 
                a.trans_flag,
                a.cust_code,
                a.doc_date, 
                a.doc_no, 
                a.item_code, 
                a.item_name,
                a.unit_code, 
                a.qty, 
                a.price_2,
                b.url_image
            FROM 
                ic_trans_detail a
            LEFT JOIN 
                product_image b ON b.ic_code = a.item_code
            WHERE 
                a.trans_flag = '44'
                AND a.cust_code = %s
                AND a.doc_no = %s
        """, (cust_code, doc_no))

        order_detail = cur.fetchall()
        print("\norder_detail:", order_detail)

        cur.execute("""
            SELECT 
                doc_no, 
                SUM(qty) AS total_qty
            FROM 
                ic_trans_detail
            WHERE 
                doc_no = %s
            GROUP BY 
                doc_no;
        """, (doc_no,))

        product_qty = cur.fetchall()
        print("\nproduct_qty:", product_qty)

        cur.execute("""
            SELECT
                total_amount_2
            FROM 
                ic_trans
            WHERE 
                doc_no = %s
        """, (doc_no,))

        total_amount_2 = cur.fetchall()
        print("\ntotal_amount_2:", total_amount_2)

    return render_template("line_oa/line_os_shop/line_oa_order_detail.html", 
                           order_detail=order_detail, 
                           product_qty=product_qty,
                           total_amount_2=total_amount_2)