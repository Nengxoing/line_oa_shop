from flask import Flask
from flask_session import Session
import os
import sys
import sqlite3
from flask_cors import CORS
UPLOAD_FOLDER = 'static/image/bank/'
app = Flask(__name__)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"

app.secret_key = "secret key"
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

Session(app)
app.secret_key = os.urandom(12)
CORS(app)
 
# from  home import *
# from member import *
# from shop  import *
# from shoppage  import *
# from back  import *
# from account  import *
# from report  import *
# from tracking  import *
# from datasyn import *
# from admin import *
# from banner import *
# from member_home import *
# from member_imageshow import *
# from member_manage import *
# from member_report import *
# from member_print import *
# from ods_service import *
# from inventory import *
# from getjson import *
# from gps import *
# from bestsale import *
# from newproduct import *
# from FastSale import *
# from whole_sale_ecat import *
# from shopbybrand import *
# from  teskgoogle import * 

#LINE Official Account
# from lineoa import *
# from mobile import *
# from line_employee import *
# from line_oa_doc import *
# from line_oa_doc_pps import *
# from line_oa_edoc_sqlite import *
# from trip_plain import *
# from odg_random import *
# from odg_poa import *
# from line_odg_poa import *
from line_os_shop import *
# from line_odg_poa_copy import *

if __name__ == "__main__":
    # app.run(debug=True,port='5000',host='0.0.0.0')
    # app.run(debug=True,port='5000',host='0.0.0.0',ssl_context=('cert.pem', 'key.pem'),)
    app.run(debug=True, port=5000, host='0.0.0.0')  # ลบ ssl_context ออก

