import pymysql

def get_connection():
    connection = pymysql.connect(
        host="127.0.0.1",
        user="root",
        password="",
         database="dstutors",
        cursorclass=pymysql.cursors.DictCursor
    )
    return connection