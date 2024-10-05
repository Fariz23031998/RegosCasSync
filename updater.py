import fdb
import pyodbc
from datetime import datetime

def get_date():
	now = datetime.now()
	formatted_now = now.strftime("%d.%m.%Y %H:%M:%S")
	return formatted_now


with open("config.txt") as config_file:
    config = eval(config_file.read())

price_type = config["price_type"]
stock_house = config["object_id"]
host = config["host"]
database = config["database"]
user = config["user"]
password = config["password"]
mdb_conn = config["mdb_conn"]


class GetFromRegos:
	def __init__(self):
		self.groups = None
		self.mydb = None
		self.items_list = []
		self.my_cursor = None
		self.last_sync = 0

	def connect_fdb(self):
		try:
			self.mydb = fdb.connect(
				host=host,
				database=database,
				user=user,
				password=password,
				charset='utf-8',
			)
		except fdb.fbcore.DatabaseError:
			return False
		else:
			self.my_cursor = self.mydb.cursor()
			return True

	def check_cash_status(self):
		query = "SELECT SST_DATE, SST_STATUS " \
				"FROM SYS_SYNC_PROCCESS_REF " \
				"WHERE SST_STATUS = 1"
		self.my_cursor.execute(query)
		sync_process = self.my_cursor.fetchall()
		sync_value = 0
		for sync in sync_process:
			timestamp = sync[0].timestamp()
			if timestamp > sync_value:
				sync_value = timestamp

		if sync_value > self.last_sync:
			self.last_sync = sync_value
			print("Database changed")
			return True
		else:
			print("Database not changed")
			return False

	def get_groups(self):
		query = "SELECT ITMG_ID, ITMG_NAME, ITMG_DELETED FROM CTLG_ITM_GROUPS_REF " \
		        "WHERE ITMG_DELETED=0 " \
		        "ORDER BY ITMG_ID"

		self.my_cursor.execute(query)
		fetched_groups = self.my_cursor.fetchall()
		return fetched_groups

	def get_items(self):
		get_items_info_sql = """
		                     SELECT ITM_ID, ITM_CODE, 
		                     SUBSTRING(ITM_NAME FROM 1 FOR 64) AS ITM_NAME, 
		                     ITM_UNIT, ITM_GROUP, ITM_DELETED_MARK,  
		                     UNT_ID, UNT_TYPE
		                     FROM CTLG_ITM_ITEMS_REF 
		                     LEFT OUTER JOIN CTLG_UNT_UNITS_REF ON ITM_UNIT=UNT_ID
		                     WHERE ITM_DELETED_MARK=0
		                     ORDER BY ITM_ID
		                     """
		self.my_cursor.execute(get_items_info_sql)
		goods_list = self.my_cursor.fetchall()

		get_prices_sql = "SELECT PRC_ITEM, PRC_PRICE_TYPE, PRC_VALUE FROM CTLG_ITM_PRICES_REF " \
		                 "WHERE PRC_PRICE_TYPE = ?"
		self.my_cursor.execute(get_prices_sql, (price_type,))
		prices_list = self.my_cursor.fetchall()
		for good in goods_list:
			good_list = list(good)
			good_id = good_list[0]
			item_type = good_list[7]

			good_list.append(0)
			for price in prices_list:
				if good_id == price[0]:
					good_list[8] = float(price[2])

			if item_type != 1:
				good_list[7] = 3

			self.items_list.append(good_list)

		return self.items_list


class UpdateData:
	def __init__(self):
		self.mydb = None
		self.my_cursor = None
		self.regos_date = GetFromRegos()
		self.old_groups = 0

	def update_mdb(self):
		if self.regos_date.connect_fdb():
			try:
				self.mydb = pyodbc.connect(mdb_conn)
			except pyodbc.Error as e:
				return f"Ошибка: {e} ({get_date()})"
			else:
				self.my_cursor = self.mydb.cursor()
				self.add_groups()
				self.update_items()

				self.my_cursor.close()
				self.mydb.close()
				return f"База данных успешно обновлено ({get_date()})"

		else:
			return "Не получается подключится к база данных Regos"

	def add_groups(self):
		query_update = "UPDATE TbGroup SET GroupName = ? " \
		               "WHERE Code = ?"

		query_insert = "INSERT INTO TbGroup (Code, GroupName) VALUES (?, ?)"

		count_query = "SELECT COUNT(*) FROM TbGroup WHERE Code = ?"
		query_get_one = "SELECT GroupName FROM TbGroup WHERE Code = ?"

		groups_info = self.regos_date.get_groups()

		for group in groups_info:
			self.my_cursor.execute(count_query, (group[0], ))
			row_count = self.my_cursor.fetchone()[0]

			self.my_cursor.execute(query_get_one, (group[0], ))

			try:
				group_name = self.my_cursor.fetchone()[0]
			except TypeError:
				group_name = ""

			if row_count > 0:
				if group_name != group[1]:
					self.execute_sql(query_update, (group[1], group[0]))
				# else:
				# 	print("Same")
			else:
				self.execute_sql(query_insert, (group[0], group[1]))

	def update_items(self):
		query_insert = "INSERT INTO TbPLU (PluNo, PluType, ItemCode, Name1, UnitPrice, UpdateDate, GroupNo, DeptNo) " \
		        "VALUES (?, ?, ?, ?, ?, ?, ?, 1)"

		query_update = "UPDATE TbPLU SET PluType = ?, Name1 = ?,  UnitPrice = ?, UpdateDate = ?, GroupNo = ? " \
		               "WHERE PluNo = ?"

		count_query = "SELECT COUNT(*) FROM TbPLU WHERE PluNo = ?"
		query_get_one = "SELECT PluNo, PluType, ItemCode, Name1, " \
		                "UnitPrice, 2 AS Rounded_Price, " \
		                "UpdateDate, GroupNo " \
		                "FROM TbPLU WHERE PluNo = ?"

		items_info = self.regos_date.get_items()
		for item in items_info:
			PluNo = item[1]
			PluType = item[7]
			ItemCode = item[1]
			Name1 = item[2]
			UnitPrice = item[8]
			UpdateDate = get_date()
			GroupNo = item[4]

			self.my_cursor.execute(count_query, (PluNo, ))
			row_count = self.my_cursor.fetchone()[0]
			# print(row_count)

			self.my_cursor.execute(query_get_one, (PluNo,))
			item_row = self.my_cursor.fetchone()
			# print(f"MDB: {item_row[:5]}")

			tuple_arg_ins = (PluNo, PluType, ItemCode, Name1, UnitPrice, UpdateDate, GroupNo)
			# print(tuple_arg_ins[:5])
			tuple_arg_upd = (PluType, Name1, UnitPrice, UpdateDate, GroupNo, PluNo)
			# print(self.get_difference(1, 1.1))
			if row_count > 0:
				if item_row[:5] != tuple_arg_ins[:5] and self.get_difference(item_row[4], UnitPrice):
					self.execute_sql(query_update, tuple_arg_upd)
					# print(f"{item_row[4], type(item_row[4])} = {UnitPrice, type(UnitPrice)}")
					# print("not same, updated")
				# else:
				# 	print("Same, Not updated")
			else:
				self.execute_sql(query_insert, tuple_arg_ins)
		self.mydb.commit()

	def execute_sql(self, query, tuple_arg):
		try:
			self.my_cursor.execute(query, tuple_arg)
		except pyodbc.Error as e:
			print(f"Ошибка: {e} ({get_date()})")
			return f"Ошибка: {e} ({get_date()})"
		else:
			self.my_cursor.commit()
			print("Обновлен")

	def get_difference(self, x, y):
		if -0.5 < x - y < 0.5:
			return False
		else:
			return True


