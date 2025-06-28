import sys
import re
import os
from datetime import datetime, date, time
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLineEdit, QMessageBox, QTableWidget, QTableWidgetItem,
    QFormLayout, QComboBox, QDateEdit, QTimeEdit, QDialog, QListWidget,
    QListWidgetItem, QInputDialog, QSpinBox, QLabel, QStackedWidget
)
from PySide6.QtCore import Qt, QTime, Signal
import ast

DATA_DIR = "restaurant_data"
os.makedirs(DATA_DIR, exist_ok=True)

class TextFileDatabase:
    def __init__(self, filename):
        self.filename = os.path.join(DATA_DIR, filename)
        self.data = []
        self.load()
    
    def load(self):
        self.data = []
        if os.path.exists(self.filename):
            with open(self.filename, 'r', encoding='utf-8') as f:
                headers = f.readline().strip().split('|')
                for line in f:
                    values = line.strip().split('|')
                    if len(values) == len(headers):
                        item = dict(zip(headers, values))
                        if 'isAdmin' in item:
                            item['isAdmin'] = item['isAdmin'] == 'True'
                        if 'isAvailable' in item:
                            item['isAvailable'] = item['isAvailable'] == 'True'
                        if 'paid' in item:
                            item['paid'] = item['paid'] == 'True'
                        if 'price' in item:
                            try:
                                item['price'] = float(item['price'])
                            except ValueError:
                                item['price'] = 0
                        # Handle dishes data conversion from string to list
                        if 'dishes' in item and isinstance(item['dishes'], str):
                            try:
                                item['dishes'] = ast.literal_eval(item['dishes'])
                            except (ValueError, SyntaxError):
                                item['dishes'] = []
                        self.data.append(item)
    
    def save(self):
        if not self.data:
            return
        
        headers = list(self.data[0].keys())
        with open(self.filename, 'w', encoding='utf-8') as f:
            f.write('|'.join(headers) + '\n')
            for item in self.data:
                values = []
                for header in headers:
                    value = item.get(header, '')
                    if isinstance(value, list):
                        # Serialize list as a string representation
                        value = str(value)
                    else:
                        value = str(value)
                    values.append(value)
                f.write('|'.join(values) + '\n')
    
    def find(self, query=None):
        if query is None:
            return self.data.copy()
        
        results = []
        for item in self.data:
            match = True
            for key, value in query.items():
                if key not in item or str(item[key]) != str(value):
                    match = False
                    break
            if match:
                results.append(item)
        return results
    
    def find_one(self, query):
        results = self.find(query)
        return results[0] if results else None
    
    def insert_one(self, document):
        if "id" not in document:
            max_id = max([int(item.get('id', 0)) for item in self.data] or [0])
            document["id"] = str(max_id + 1)
        self.data.append(document)
        self.save()
        return document
    
    def update_one(self, query, update):
        item = self.find_one(query)
        if item:
            if "$set" in update:
                for key, value in update["$set"].items():
                    item[key] = value
            self.save()
        return item
    
    def delete_one(self, query):
        item = self.find_one(query)
        if item:
            self.data.remove(item)
            self.save()
        return item
    
    def delete_many(self, query):
        items = self.find(query)
        for item in items:
            self.data.remove(item)
        if items:
            self.save()
        return len(items)
    
    def aggregate(self, pipeline):
        results = self.data.copy()
        for stage in pipeline:
            if "$match" in stage:
                query = stage["$match"]
                results = [item for item in results if all(
                    str(item.get(k)) == str(v) for k, v in query.items()
                )]
            elif "$group" in stage:
                group = stage["$group"]
                groups = {}
                for item in results:
                    group_key = item.get(group["_id"].lstrip("$"))
                    if group_key not in groups:
                        groups[group_key] = {"_id": group_key, "count": 0}
                    groups[group_key]["count"] += 1
                results = list(groups.values())
            elif "$sort" in stage:
                sort = stage["$sort"]
                key = list(sort.keys())[0]
                reverse = sort[key] == -1
                results.sort(key=lambda x: x.get(key, 0), reverse=reverse)
        return results

# Инициализация "коллекций"
waiter_collection = TextFileDatabase("waiters.txt")
table_collection = TextFileDatabase("restaurantTables.txt")
reservation_collection = TextFileDatabase("reservations.txt")
customer_collection = TextFileDatabase("customers.txt")
menu_collection = TextFileDatabase("menuItems.txt")
order_collection = TextFileDatabase("orders.txt")
receipt_collection = TextFileDatabase("receipts.txt")

class LoginWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Авторизация")
        self.resize(300, 200)
        
        button_style = """
            QPushButton {
                padding: 8px 16px;
                font-size: 14px;
                border-radius: 4px;
                min-width: 120px;
                margin: 5px;
            }
            QPushButton#login {
                background-color: #4CAF50;
                color: white;
                border: 1px solid #45a049;
            }
            QPushButton#login:hover {
                background-color: #45a049;
            }
            QPushButton#login:pressed {
                background-color: #3e8e41;
            }
            QPushButton#register {
                background-color: #2196F3;
                color: white;
                border: 1px solid #1976D2;
            }
            QPushButton#register:hover {
                background-color: #1976D2;
            }
            QPushButton#register:pressed {
                background-color: #0D47A1;
            }
        """
        
        layout = QVBoxLayout(self)
        
        line_edit_style = """
            QLineEdit {
                padding: 8px;
                font-size: 14px;
                border: 1px solid #ccc;
                border-radius: 4px;
                margin: 5px;
            }
        """
        
        self.login_input = QLineEdit()
        self.login_input.setPlaceholderText("Логин")
        self.login_input.setStyleSheet(line_edit_style)
        
        self.pass_input = QLineEdit()
        self.pass_input.setPlaceholderText("Пароль")
        self.pass_input.setEchoMode(QLineEdit.Password)
        self.pass_input.setStyleSheet(line_edit_style)

        btn_login = QPushButton("Войти")
        btn_login.setObjectName("login")
        btn_login.setStyleSheet(button_style)
        
        btn_register = QPushButton("Регистрация")
        btn_register.setObjectName("register")
        btn_register.setStyleSheet(button_style)

        layout.addWidget(QLabel("Логин:"))
        layout.addWidget(self.login_input)
        layout.addWidget(QLabel("Пароль:"))
        layout.addWidget(self.pass_input)
        layout.addWidget(btn_login)
        layout.addWidget(btn_register)

        btn_login.clicked.connect(self.login)
        btn_register.clicked.connect(self.show_register_window)

    def login(self):
        login = self.login_input.text().strip()
        password = self.pass_input.text().strip()

        if not re.fullmatch(r'[A-Za-z0-9]{4,}', login):
            QMessageBox.warning(self, "Ошибка", "Логин должен быть на латинице и не менее 4 символов")
            return
        if not re.fullmatch(r'[A-Za-z0-9]{4,}', password):
            QMessageBox.warning(self, "Ошибка", "Пароль должен быть на латинице и не менее 4 символов")
            return

        user = waiter_collection.find_one({"login": login, "password": password})
        if user:
            self.main_window = MainWindow(user)
            self.main_window.show()
            self.close()
        else:
            QMessageBox.warning(self, "Ошибка", "Неверный логин или пароль")

    def show_register_window(self):
        self.register_window = RegisterWindow()
        self.register_window.show()

class RegisterWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Регистрация")
        self.resize(300, 250)
        
        button_style = """
            QPushButton {
                padding: 8px 16px;
                font-size: 14px;
                border-radius: 4px;
                min-width: 120px;
                margin: 5px;
            }
            QPushButton#register {
                background-color: #4CAF50;
                color: white;
                border: 1px solid #45a049;
            }
            QPushButton#register:hover {
                background-color: #45a049;
            }
            QPushButton#register:pressed {
                background-color: #3e8e41;
            }
            QPushButton#back {
                background-color: #2196F3;
                color: white;
                border: 1px solid #1976D2;
            }
            QPushButton#back:hover {
                background-color: #1976D2;
            }
            QPushButton#back:pressed {
                background-color: #0D47A1;
            }
        """
        
        layout = QVBoxLayout(self)
        
        line_edit_style = """
            QLineEdit {
                padding: 8px;
                font-size: 14px;
                border: 1px solid #ccc;
                border-radius: 4px;
                margin: 5px;
            }
        """
        
        self.login_input = QLineEdit()
        self.login_input.setPlaceholderText("Логин")
        self.login_input.setStyleSheet(line_edit_style)
        
        self.pass_input = QLineEdit()
        self.pass_input.setPlaceholderText("Пароль")
        self.pass_input.setEchoMode(QLineEdit.Password)
        self.pass_input.setStyleSheet(line_edit_style)

        self.pass_confirm_input = QLineEdit()
        self.pass_confirm_input.setPlaceholderText("Подтверждение пароля")
        self.pass_confirm_input.setEchoMode(QLineEdit.Password)
        self.pass_confirm_input.setStyleSheet(line_edit_style)

        btn_register = QPushButton("Зарегистрироваться")
        btn_register.setObjectName("register")
        btn_register.setStyleSheet(button_style)
        
        btn_back = QPushButton("Назад")
        btn_back.setObjectName("back")
        btn_back.setStyleSheet(button_style)

        layout.addWidget(QLabel("Логин:"))
        layout.addWidget(self.login_input)
        layout.addWidget(QLabel("Пароль:"))
        layout.addWidget(self.pass_input)
        layout.addWidget(QLabel("Подтверждение пароля:"))
        layout.addWidget(self.pass_confirm_input)
        layout.addWidget(btn_register)
        layout.addWidget(btn_back)

        btn_register.clicked.connect(self.register)
        btn_back.clicked.connect(self.close)

    def register(self):
        login = self.login_input.text().strip()
        password = self.pass_input.text().strip()
        password_confirm = self.pass_confirm_input.text().strip()

        if not re.fullmatch(r'[A-Za-z0-9]{4,}', login):
            QMessageBox.warning(self, "Ошибка", "Логин должен быть на латинице и не менее 4 символов")
            return
        if not re.fullmatch(r'[A-Za-z0-9]{4,}', password):
            QMessageBox.warning(self, "Ошибка", "Пароль должен быть на латинице и не менее 4 символа")
            return
        if password != password_confirm:
            QMessageBox.warning(self, "Ошибка", "Пароли не совпадают")
            return

        if waiter_collection.find_one({"login": login}):
            QMessageBox.warning(self, "Ошибка", "Пользователь с таким логином уже существует")
            return

        waiter_collection.insert_one({
            "login": login,
            "password": password,
            "isAdmin": False
        })
        QMessageBox.information(self, "Успешно", "Пользователь зарегистрирован")
        self.close()

class MainWindow(QMainWindow):
    def __init__(self, user):
        super().__init__()
        self.user = user
        self.setWindowTitle(f"Ресторан — Пользователь: {user['login']}")
        self.resize(1000, 700)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        self.create_navigation_bar(main_layout)
        
        self.stack = QStackedWidget()
        main_layout.addWidget(self.stack)
        
        self.tables_tab = TablesTab(is_admin=user.get("isAdmin", False))
        self.reservations_tab = ReservationsTab()
        self.orders_tab = OrdersTab(user)
        self.receipts_tab = ReceiptsTab(user)
        self.menu_tab = MenuTab(is_admin=user.get("isAdmin", False))
        self.stats_tab = StatsTab()
        
        self.stack.addWidget(self.tables_tab)
        self.stack.addWidget(self.reservations_tab)
        self.stack.addWidget(self.orders_tab)
        self.stack.addWidget(self.receipts_tab)
        self.stack.addWidget(self.menu_tab)
        self.stack.addWidget(self.stats_tab)
        
        self.stack.setCurrentWidget(self.tables_tab)
        
        self.reservations_tab.reservation_created.connect(self.tables_tab.load_tables)
        self.orders_tab.order_updated.connect(self.reservations_tab.load_reservations)
        self.orders_tab.receipt_created.connect(self.receipts_tab.load_receipts)
        self.receipts_tab.receipt_paid.connect(self.orders_tab.load_orders)
        
        btn_logout = QPushButton("Выйти из аккаунта")
        btn_logout.setStyleSheet("""
            QPushButton {
                padding: 8px 16px;
                font-size: 14px;
                border-radius: 4px;
                background-color: #f44336;
                color: white;
                border: 1px solid #d32f2f;
                margin: 10px;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
            QPushButton:pressed {
                background-color: #b71c1c;
            }
        """)
        btn_logout.clicked.connect(self.logout)
        main_layout.addWidget(btn_logout)
    
    def create_navigation_bar(self, layout):
        nav_layout = QHBoxLayout()
        
        self.btn_tables = QPushButton("Столы")
        self.btn_reservations = QPushButton("Бронирования")
        self.btn_orders = QPushButton("Заказы")
        self.btn_receipts = QPushButton("Счета")
        self.btn_menu = QPushButton("Меню")
        self.btn_stats = QPushButton("Статистика")
        
        button_style = """
            QPushButton {
                padding: 10px 15px;
                font-size: 14px;
                min-width: 120px;
                border: 1px solid #4CAF50;
                border-radius: 5px;
                background-color: #f8f9fa;
                color: #333;
                margin: 2px;
            }
            QPushButton:hover {
                background-color: #e9ecef;
                border-color: #3e8e41;
            }
            QPushButton:pressed {
                background-color: #dae0e5;
            }
            QPushButton:checked {
                background-color: #4CAF50;
                color: white;
            }
        """
        
        for btn in [self.btn_tables, self.btn_reservations, self.btn_orders, 
                   self.btn_receipts, self.btn_menu, self.btn_stats]:
            btn.setStyleSheet(button_style)
            btn.setCheckable(True)
        
        self.btn_tables.setChecked(True)
        
        nav_layout.addWidget(self.btn_tables)
        nav_layout.addWidget(self.btn_reservations)
        nav_layout.addWidget(self.btn_orders)
        nav_layout.addWidget(self.btn_receipts)
        nav_layout.addWidget(self.btn_menu)
        nav_layout.addWidget(self.btn_stats)
        
        self.btn_tables.clicked.connect(lambda: self.show_section(self.tables_tab))
        self.btn_reservations.clicked.connect(lambda: self.show_section(self.reservations_tab))
        self.btn_orders.clicked.connect(lambda: self.show_section(self.orders_tab))
        self.btn_receipts.clicked.connect(lambda: self.show_section(self.receipts_tab))
        self.btn_menu.clicked.connect(lambda: self.show_section(self.menu_tab))
        self.btn_stats.clicked.connect(lambda: self.show_section(self.stats_tab))
        
        layout.addLayout(nav_layout)
    
    def show_section(self, section_widget):
        self.stack.setCurrentWidget(section_widget)
        
        for btn in [self.btn_tables, self.btn_reservations, self.btn_orders, 
                   self.btn_receipts, self.btn_menu, self.btn_stats]:
            btn.setChecked(False)
        
        if section_widget == self.tables_tab:
            self.btn_tables.setChecked(True)
        elif section_widget == self.reservations_tab:
            self.btn_reservations.setChecked(True)
        elif section_widget == self.orders_tab:
            self.btn_orders.setChecked(True)
        elif section_widget == self.receipts_tab:
            self.btn_receipts.setChecked(True)
        elif section_widget == self.menu_tab:
            self.btn_menu.setChecked(True)
        elif section_widget == self.stats_tab:
            self.btn_stats.setChecked(True)

    def logout(self):
        self.close()
        self.login_window = LoginWindow()
        self.login_window.show()

class TablesTab(QWidget):
    def __init__(self, is_admin=False):
        super().__init__()
        layout = QVBoxLayout(self)

        self.table_widget = QTableWidget()
        self.table_widget.setColumnCount(4)
        self.table_widget.setHorizontalHeaderLabels(["Номер", "Мест", "Доступен", "Статус"])

        button_style = """
            QPushButton {
                padding: 8px 16px;
                font-size: 14px;
                border-radius: 4px;
                margin: 5px;
                min-width: 120px;
            }
        """
        
        btn_add = QPushButton("Добавить стол")
        btn_add.setStyleSheet(button_style + """
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: 1px solid #45a049;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3e8e41;
            }
        """)
        
        btn_delete = QPushButton("Удалить стол")
        btn_delete.setStyleSheet(button_style + """
            QPushButton {
                background-color: #f44336;
                color: white;
                border: 1px solid #d32f2f;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
            QPushButton:pressed {
                background-color: #b71c1c;
            }
        """)
        
        btn_toggle = QPushButton("Изменить доступность")
        btn_toggle.setStyleSheet(button_style + """
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: 1px solid #1976D2;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:pressed {
                background-color: #0D47A1;
            }
        """)

        btn_layout = QHBoxLayout()
        if is_admin:
            btn_layout.addWidget(btn_add)
            btn_layout.addWidget(btn_delete)
            btn_layout.addWidget(btn_toggle)

        layout.addWidget(self.table_widget)
        if is_admin:
            layout.addLayout(btn_layout)

        btn_add.clicked.connect(self.add_table)
        btn_delete.clicked.connect(self.delete_table)
        btn_toggle.clicked.connect(self.toggle_availability)

        self.load_tables()

    def load_tables(self):
        self.table_widget.setRowCount(0)
        now = datetime.now()
        today = now.date()
        current_time = now.time()

        for table in table_collection.find():
            row = self.table_widget.rowCount()
            self.table_widget.insertRow(row)
            self.table_widget.setItem(row, 0, QTableWidgetItem(str(table["tableNumber"])))
            self.table_widget.setItem(row, 1, QTableWidgetItem(str(table["seats"])))
            self.table_widget.setItem(row, 2, QTableWidgetItem("Да" if table.get("isAvailable", True) else "Нет"))

            reservations = list(reservation_collection.find({
                "tableId": table["id"],
                "reservationDate": today.strftime("%Y-%m-%d"),
                "status": {"$ne": "cancelled"}
            }))

            status = table.get("status", "free")
            busy_now = False
            reserved_today = False

            for res in reservations:
                start = datetime.strptime(res["startTime"], "%H:%M").time()
                end = datetime.strptime(res["endTime"], "%H:%M").time()
                if start <= current_time < end:
                    busy_now = True
                    break
                reserved_today = True

            if busy_now:
                status = "занят"
            elif reserved_today:
                status = "забронирован"
            else:
                status = "свободен" if table.get("isAvailable", True) else "недоступен"

            self.table_widget.setItem(row, 3, QTableWidgetItem(status))
            self.table_widget.item(row, 0).setData(Qt.UserRole, table["id"])

    def add_table(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Добавить стол")
        layout = QFormLayout(dialog)

        spin_num = QSpinBox()
        spin_num.setRange(1, 1000)
        spin_seats = QSpinBox()
        spin_seats.setRange(1, 50)

        layout.addRow("Номер стола:", spin_num)
        layout.addRow("Мест:", spin_seats)

        btn_box = QHBoxLayout()
        btn_ok = QPushButton("Добавить")
        btn_ok.setStyleSheet("""
            QPushButton {
                padding: 8px 16px;
                font-size: 14px;
                border-radius: 4px;
                background-color: #4CAF50;
                color: white;
                border: 1px solid #45a049;
                margin: 5px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3e8e41;
            }
        """)
        btn_cancel = QPushButton("Отмена")
        btn_cancel.setStyleSheet("""
            QPushButton {
                padding: 8px 16px;
                font-size: 14px;
                border-radius: 4px;
                background-color: #f44336;
                color: white;
                border: 1px solid #d32f2f;
                margin: 5px;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
            QPushButton:pressed {
                background-color: #b71c1c;
            }
        """)
        btn_box.addWidget(btn_ok)
        btn_box.addWidget(btn_cancel)
        layout.addRow(btn_box)

        def on_ok():
            if table_collection.find_one({"tableNumber": str(spin_num.value())}):
                QMessageBox.warning(dialog, "Ошибка", "Такой стол уже есть")
                return
            table_collection.insert_one({
                "tableNumber": str(spin_num.value()),
                "seats": str(spin_seats.value()),
                "isAvailable": True,
                "status": "free"
            })
            self.load_tables()
            dialog.accept()

        btn_ok.clicked.connect(on_ok)
        btn_cancel.clicked.connect(dialog.reject)

        dialog.exec()

    def delete_table(self):
        selected = self.table_widget.selectedItems()
        if not selected:
            QMessageBox.warning(self, "Ошибка", "Выберите стол")
            return
        row = self.table_widget.currentRow()
        table_id = self.table_widget.item(row, 0).data(Qt.UserRole)
        table_collection.delete_one({"id": table_id})
        reservation_collection.delete_many({"tableId": table_id})
        self.load_tables()

    def toggle_availability(self):
        selected = self.table_widget.selectedItems()
        if not selected:
            QMessageBox.warning(self, "Ошибка", "Выберите стол")
            return
        row = self.table_widget.currentRow()
        table_id = self.table_widget.item(row, 0).data(Qt.UserRole)
        table = table_collection.find_one({"id": table_id})
        new_status = not table.get("isAvailable", True)
        table_collection.update_one({"id": table_id}, {"$set": {"isAvailable": new_status}})
        self.load_tables()

class ReservationsTab(QWidget):
    reservation_created = Signal()

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)

        form_layout = QFormLayout()
        self.name_input = QLineEdit()
        self.phone_input = QLineEdit()
        self.table_combo = QComboBox()
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDate(date.today())
        self.start_time = QTimeEdit()
        self.end_time = QTimeEdit()
        self.start_time.setTime(QTime(8, 0))
        self.end_time.setTime(QTime(9, 0))
        self.start_time.setMinimumTime(QTime(8, 0))
        self.start_time.setMaximumTime(QTime(21, 0))
        self.end_time.setMinimumTime(QTime(8, 0))
        self.end_time.setMaximumTime(QTime(22, 0))

        line_edit_style = """
            QLineEdit, QComboBox, QDateEdit, QTimeEdit {
                padding: 8px;
                font-size: 14px;
                border: 1px solid #ccc;
                border-radius: 4px;
                margin: 5px;
            }
        """
        
        self.name_input.setStyleSheet(line_edit_style)
        self.phone_input.setStyleSheet(line_edit_style)
        self.table_combo.setStyleSheet(line_edit_style)
        self.date_edit.setStyleSheet(line_edit_style)
        self.start_time.setStyleSheet(line_edit_style)
        self.end_time.setStyleSheet(line_edit_style)

        form_layout.addRow("Имя клиента:", self.name_input)
        form_layout.addRow("Телефон клиента:", self.phone_input)
        form_layout.addRow("Стол:", self.table_combo)
        form_layout.addRow("Дата:", self.date_edit)
        form_layout.addRow("Время начала:", self.start_time)
        form_layout.addRow("Время конца:", self.end_time)

        button_style = """
            QPushButton {
                padding: 8px 16px;
                font-size: 14px;
                border-radius: 4px;
                margin: 5px;
                min-width: 120px;
            }
        """
        
        btn_book = QPushButton("Забронировать")
        btn_book.setStyleSheet(button_style + """
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: 1px solid #45a049;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3e8e41;
            }
        """)

        btn_cancel_res = QPushButton("Отменить бронирование")
        btn_cancel_res.setStyleSheet(button_style + """
            QPushButton {
                background-color: #f44336;
                color: white;
                border: 1px solid #d32f2f;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
            QPushButton:pressed {
                background-color: #b71c1c;
            }
        """)

        btn_delete_res = QPushButton("Удалить бронирование")
        btn_delete_res.setStyleSheet(button_style + """
            QPushButton {
                background-color: #ff9800;
                color: white;
                border: 1px solid #f57c00;
            }
            QPushButton:hover {
                background-color: #f57c00;
            }
            QPushButton:pressed {
                background-color: #e65100;
            }
        """)

        btn_edit_res = QPushButton("Редактировать бронирование")
        btn_edit_res.setStyleSheet(button_style + """
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: 1px solid #1976D2;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:pressed {
                background-color: #0D47A1;
            }
        """)

        button_layout = QHBoxLayout()
        button_layout.addWidget(btn_book)
        button_layout.addWidget(btn_cancel_res)
        button_layout.addWidget(btn_delete_res)
        button_layout.addWidget(btn_edit_res)

        layout.addLayout(form_layout)
        layout.addLayout(button_layout)

        self.reservations_list = QTableWidget()
        self.reservations_list.setColumnCount(6)
        self.reservations_list.setHorizontalHeaderLabels([
            "Клиент", "Телефон", "Стол", "Дата", "Время", "Статус"
        ])
        layout.addWidget(self.reservations_list)

        self.load_tables()
        self.load_reservations()

        self.date_edit.dateChanged.connect(self.load_tables)
        self.start_time.timeChanged.connect(self.load_tables)
        self.end_time.timeChanged.connect(self.load_tables)

        btn_book.clicked.connect(self.book_table)
        btn_cancel_res.clicked.connect(self.cancel_reservation)
        btn_delete_res.clicked.connect(self.delete_reservation)
        btn_edit_res.clicked.connect(self.edit_reservation)

    def load_tables(self):
        self.table_combo.clear()
        res_date = self.date_edit.date().toPython()
        start = self.start_time.time().toPython()
        end = self.end_time.time().toPython()
        if start >= end:
            return

        res_date_str = res_date.strftime("%Y-%m-%d")
        for table in table_collection.find({"isAvailable": True}):
            busy = False
            for res in reservation_collection.find({
                "tableId": table["id"],
                "reservationDate": res_date_str,
                "status": {"$ne": "cancelled"}
            }):
                res_start = datetime.strptime(res["startTime"], "%H:%M").time()
                res_end = datetime.strptime(res["endTime"], "%H:%M").time()
                if res_start < end and res_end > start:
                    busy = True
                    break
            if not busy:
                self.table_combo.addItem(f"Стол {table['tableNumber']} (мест: {table['seats']})", table["id"])

    def load_reservations(self):
        self.reservations_list.setRowCount(0)
        for res in reservation_collection.find():
            row = self.reservations_list.rowCount()
            self.reservations_list.insertRow(row)
            customer = customer_collection.find_one({"id": res["customerId"]})
            table = table_collection.find_one({"id": res["tableId"]})
            self.reservations_list.setItem(row, 0, QTableWidgetItem(customer.get("name", "") if customer else ""))
            self.reservations_list.setItem(row, 1, QTableWidgetItem(customer.get("phone", "") if customer else ""))
            self.reservations_list.setItem(row, 2, QTableWidgetItem(str(table["tableNumber"]) if table else ""))
            self.reservations_list.setItem(row, 3, QTableWidgetItem(str(res["reservationDate"])))
            self.reservations_list.setItem(row, 4, QTableWidgetItem(f"{res['startTime']} - {res['endTime']}"))
            self.reservations_list.setItem(row, 5, QTableWidgetItem(res.get("status", "confirmed")))
            self.reservations_list.item(row, 0).setData(Qt.UserRole, res["id"])

    def book_table(self):
        name = self.name_input.text().strip()
        phone = self.phone_input.text().strip()
        table_id = self.table_combo.currentData()
        res_date = self.date_edit.date().toPython()
        start = self.start_time.time().toPython()
        end = self.end_time.time().toPython()

        today = datetime.now().date()
        if res_date < today:
            QMessageBox.warning(self, "Ошибка", "Нельзя бронировать на прошедшую дату")
            return
        if res_date == today and start <= datetime.now().time():
            QMessageBox.warning(self, "Ошибка", "Время бронирования должно быть позже текущего")
            return

        if not name or not phone or not table_id:
            QMessageBox.warning(self, "Ошибка", "Заполните все поля")
            return
        if start >= end:
            QMessageBox.warning(self, "Ошибка", "Время начала должно быть меньше конца")
            return

        start_dt = datetime.combine(res_date, start)
        end_dt = datetime.combine(res_date, end)
        if (end_dt - start_dt).total_seconds() < 3600:
            QMessageBox.warning(self, "Ошибка", "Минимальное время бронирования — 1 час")
            return

        open_time = time(8, 0)
        close_time = time(22, 0)
        if start < open_time or end > close_time:
            QMessageBox.warning(self, "Ошибка", "Бронирование возможно только с 8:00 до 22:00")
            return

        res_date_str = res_date.strftime("%Y-%m-%d")

        overlapping = reservation_collection.find_one({
            "tableId": table_id,
            "reservationDate": res_date_str,
            "$or": [
                {"startTime": {"$lt": end.strftime("%H:%M")}, "endTime": {"$gt": start.strftime("%H:%M")}}
            ],
            "status": {"$ne": "cancelled"}
        })
        if overlapping:
            QMessageBox.warning(self, "Ошибка", "Стол в это время уже забронирован")
            return

        customer = customer_collection.find_one({"phone": phone})
        if not customer:
            customer = customer_collection.insert_one({"name": name, "phone": phone})
            customer_id = customer["id"]
        else:
            customer_id = customer["id"]

        reservation_collection.insert_one({
            "tableId": table_id,
            "customerId": customer_id,
            "reservationDate": res_date_str,
            "startTime": start.strftime("%H:%M"),
            "endTime": end.strftime("%H:%M"),
            "status": "confirmed"
        })

        QMessageBox.information(self, "Успешно", "Бронирование создано")
        self.load_reservations()
        self.reservation_created.emit()

    def cancel_reservation(self):
        selected = self.reservations_list.selectedItems()
        if not selected:
            QMessageBox.warning(self, "Ошибка", "Выберите бронирование")
            return
        row = self.reservations_list.currentRow()
        res_id = self.reservations_list.item(row, 0).data(Qt.UserRole)
        reservation_collection.update_one({"id": res_id}, {"$set": {"status": "cancelled"}})
        QMessageBox.information(self, "Отмена", "Бронирование отменено")
        self.load_reservations()
        self.reservation_created.emit()

    def delete_reservation(self):
        selected = self.reservations_list.selectedItems()
        if not selected:
            QMessageBox.warning(self, "Ошибка", "Выберите бронирование")
            return
        row = self.reservations_list.currentRow()
        res_id = self.reservations_list.item(row, 0).data(Qt.UserRole)
        reply = QMessageBox.question(self, "Удалить", "Удалить выбранное бронирование?", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            reservation_collection.delete_one({"id": res_id})
            QMessageBox.information(self, "Удалено", "Бронирование удалено")
            self.load_reservations()
            self.reservation_created.emit()

    def edit_reservation(self):
        selected = self.reservations_list.selectedItems()
        if not selected:
            QMessageBox.warning(self, "Ошибка", "Выберите бронирование")
            return
        row = self.reservations_list.currentRow()
        res_id = self.reservations_list.item(row, 0).data(Qt.UserRole)
        reservation = reservation_collection.find_one({"id": res_id})
        if not reservation:
            QMessageBox.warning(self, "Ошибка", "Бронирование не найдено")
            return

        customer = customer_collection.find_one({"id": reservation["customerId"]})

        dialog = QDialog(self)
        dialog.setWindowTitle("Редактировать бронирование")
        layout = QFormLayout(dialog)

        name_edit = QLineEdit(customer.get("name", "") if customer else "")
        phone_edit = QLineEdit(customer.get("phone", "") if customer else "")
        table_combo = QComboBox()
        for t in table_collection.find({"isAvailable": True}):
            table_combo.addItem(f"Стол {t['tableNumber']} (мест: {t['seats']})", t["id"])
            if t["id"] == reservation["tableId"]:
                table_combo.setCurrentIndex(table_combo.count() - 1)
        date_edit = QDateEdit()
        date_edit.setCalendarPopup(True)
        res_date = datetime.strptime(reservation["reservationDate"], "%Y-%m-%d").date() if isinstance(reservation["reservationDate"], str) else reservation["reservationDate"].date()
        date_edit.setDate(res_date)
        start_time = QTimeEdit()
        end_time = QTimeEdit()
        start_time.setTime(QTime.fromString(reservation["startTime"], "HH:mm"))
        end_time.setTime(QTime.fromString(reservation["endTime"], "HH:mm"))

        layout.addRow("Имя клиента:", name_edit)
        layout.addRow("Телефон клиента:", phone_edit)
        layout.addRow("Стол:", table_combo)
        layout.addRow("Дата:", date_edit)
        layout.addRow("Время начала:", start_time)
        layout.addRow("Время конца:", end_time)

        btn_ok = QPushButton("Сохранить")
        btn_ok.setStyleSheet("""
            QPushButton {
                padding: 8px 16px;
                font-size: 14px;
                border-radius: 4px;
                background-color: #4CAF50;
                color: white;
                border: 1px solid #45a049;
                margin: 5px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3e8e41;
            }
        """)
        btn_cancel = QPushButton("Отмена")
        btn_cancel.setStyleSheet("""
            QPushButton {
                padding: 8px 16px;
                font-size: 14px;
                border-radius: 4px;
                background-color: #f44336;
                color: white;
                border: 1px solid #d32f2f;
                margin: 5px;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
            QPushButton:pressed {
                background-color: #b71c1c;
            }
        """)
        btn_box = QHBoxLayout()
        btn_box.addWidget(btn_ok)
        btn_box.addWidget(btn_cancel)
        layout.addRow(btn_box)

        def on_ok():
            name = name_edit.text().strip()
            phone = phone_edit.text().strip()
            table_id = table_combo.currentData()
            res_date = date_edit.date().toPython()
            start = start_time.time().toPython()
            end = end_time.time().toPython()

            if not name or not phone or not table_id:
                QMessageBox.warning(dialog, "Ошибка", "Заполните все поля")
                return
            if start >= end:
                QMessageBox.warning(dialog, "Ошибка", "Время начала должно быть меньше конца")
                return

            res_date_str = res_date.strftime("%Y-%m-%d")

            overlapping = reservation_collection.find_one({
                "tableId": table_id,
                "reservationDate": res_date_str,
                "$or": [
                    {"startTime": {"$lt": end.strftime("%H:%M")}, "endTime": {"$gt": start.strftime("%H:%M")}}
                ],
                "status": {"$ne": "cancelled"},
                "id": {"$ne": res_id}
            })
            if overlapping:
                QMessageBox.warning(dialog, "Ошибка", "Стол в это время уже забронирован")
                return

            customer = customer_collection.find_one({"phone": phone})
            if customer:
                customer_collection.update_one(
                    {"id": customer["id"]},
                    {"$set": {"name": name, "phone": phone}}
                )
                customer_id = customer["id"]
            else:
                customer = customer_collection.insert_one({"name": name, "phone": phone})
                customer_id = customer["id"]

            reservation_collection.update_one(
                {"id": res_id},
                {"$set": {
                    "tableId": table_id,
                    "customerId": customer_id,
                    "reservationDate": res_date_str,
                    "startTime": start.strftime("%H:%M"),
                    "endTime": end.strftime("%H:%M"),
                    "status": "confirmed"
                }}
            )
            QMessageBox.information(dialog, "Успешно", "Бронирование обновлено")
            self.load_reservations()
            self.reservation_created.emit()
            dialog.accept()

        btn_ok.clicked.connect(on_ok)
        btn_cancel.clicked.connect(dialog.reject)
        dialog.exec()

class OrdersTab(QWidget):
    order_updated = Signal()
    receipt_created = Signal()

    def __init__(self, user):
        super().__init__()
        self.user = user
        layout = QVBoxLayout(self)

        self.orders_table = QTableWidget()
        self.orders_table.setColumnCount(6)
        self.orders_table.setHorizontalHeaderLabels([
            "Клиент", "Стол", "Дата", "Блюда", "Статус", "Ответственный"
        ])

        layout.addWidget(self.orders_table)

        order_button_style = """
            QPushButton {
                padding: 8px 16px;
                font-size: 14px;
                border-radius: 4px;
                margin: 5px;
                min-width: 120px;
            }
        """

        btn_edit_order = QPushButton("Редактировать заказ")
        btn_edit_order.setStyleSheet(order_button_style + """
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: 1px solid #1976D2;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:pressed {
                background-color: #0D47A1;
            }
        """)
        layout.addWidget(btn_edit_order)
        btn_edit_order.clicked.connect(self.edit_order)

        btn_new_order = QPushButton("Создать заказ")
        btn_new_order.setStyleSheet(order_button_style + """
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: 1px solid #45a049;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3e8e41;
            }
        """)

        btn_change_status = QPushButton("Изменить статус заказа")
        btn_change_status.setStyleSheet(order_button_style + """
            QPushButton {
                background-color: #FFC107;
                color: black;
                border: 1px solid #FFA000;
            }
            QPushButton:hover {
                background-color: #FFA000;
            }
            QPushButton:pressed {
                background-color: #FF8F00;
            }
        """)

        btn_create_receipt = QPushButton("Выдать счет")
        btn_create_receipt.setStyleSheet(order_button_style + """
            QPushButton {
                background-color: #9C27B0;
                color: white;
                border: 1px solid #7B1FA2;
            }
            QPushButton:hover {
                background-color: #7B1FA2;
            }
            QPushButton:pressed {
                background-color: #6A1B9A;
            }
        """)

        btn_delete_order = QPushButton("Удалить заказ")
        btn_delete_order.setStyleSheet(order_button_style + """
            QPushButton {
                background-color: #f44336;
                color: white;
                border: 1px solid #d32f2f;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
            QPushButton:pressed {
                background-color: #b71c1c;
            }
        """)

        button_layout = QHBoxLayout()
        button_layout.addWidget(btn_new_order)
        button_layout.addWidget(btn_change_status)
        button_layout.addWidget(btn_create_receipt)
        button_layout.addWidget(btn_delete_order)
        layout.addLayout(button_layout)

        btn_new_order.clicked.connect(self.create_order)
        btn_change_status.clicked.connect(self.change_status)
        btn_create_receipt.clicked.connect(self.create_receipt)
        btn_delete_order.clicked.connect(self.delete_order)

        self.load_orders()

    def delete_order(self):
        selected = self.orders_table.selectedItems()
        if not selected:
            QMessageBox.warning(self, "Ошибка", "Выберите заказ")
            return
        row = self.orders_table.currentRow()
        order_id = self.orders_table.item(row, 0).data(Qt.UserRole)
        reply = QMessageBox.question(self, "Удалить", "Удалить выбранный заказ?", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            receipt_collection.delete_many({"orderId": order_id})
            order_collection.delete_one({"id": order_id})
            QMessageBox.information(self, "Удалено", "Заказ удален")
            self.load_orders()
            self.order_updated.emit()

    def load_orders(self):
        self.orders_table.setRowCount(0)
        for order in order_collection.find():
            row = self.orders_table.rowCount()
            self.orders_table.insertRow(row)
            customer = customer_collection.find_one({"id": order.get("customerId")})
            table = table_collection.find_one({"id": order.get("tableId")})
            
            # Handle dishes data - it might be stored as a string or list
            dishes = order.get("dishes", [])
            if isinstance(dishes, str):
                try:
                    dishes = ast.literal_eval(dishes)
                except (ValueError, SyntaxError):
                    dishes = []
            
            dishes_text = ", ".join([f"{item['name']} x{item['quantity']}" for item in dishes]) if dishes else ""
            
            self.orders_table.setItem(row, 0, QTableWidgetItem(customer.get("name", "") if customer else ""))
            self.orders_table.setItem(row, 1, QTableWidgetItem(str(table["tableNumber"]) if table else ""))
            self.orders_table.setItem(row, 2, QTableWidgetItem(str(order.get("orderDate", ""))))
            self.orders_table.setItem(row, 3, QTableWidgetItem(dishes_text))
            self.orders_table.setItem(row, 4, QTableWidgetItem(order.get("status", "new")))
            self.orders_table.setItem(row, 5, QTableWidgetItem(order.get("waiterLogin", "")))

            self.orders_table.item(row, 0).setData(Qt.UserRole, order["id"])

    def create_order(self):
        dialog = OrderDialog(self.user)
        if dialog.exec():
            self.load_orders()
            self.order_updated.emit()

    def change_status(self):
        selected = self.orders_table.selectedItems()
        if not selected:
            QMessageBox.warning(self, "Ошибка", "Выберите заказ")
            return
        row = self.orders_table.currentRow()
        order_id = self.orders_table.item(row, 0).data(Qt.UserRole)

        order = order_collection.find_one({"id": order_id})
        if not order:
            QMessageBox.warning(self, "Ошибка", "Заказ не найден")
            return

        statuses = ["new", "preparing", "ready", "delivered", "cancelled", "paid"]
        current_status = order.get("status", "new")
        try:
            current_index = statuses.index(current_status)
        except ValueError:
            current_index = 0
        next_status, ok = QInputDialog.getItem(self, "Изменить статус", "Новый статус", statuses, current_index, False)
        if ok and next_status:
            order_collection.update_one({"id": order_id}, {"$set": {"status": next_status}})
            self.load_orders()
            self.order_updated.emit()

    def create_receipt(self):
        selected = self.orders_table.selectedItems()
        if not selected:
            QMessageBox.warning(self, "Ошибка", "Выберите заказ")
            return
        row = self.orders_table.currentRow()
        order_id = self.orders_table.item(row, 0).data(Qt.UserRole)
        order = order_collection.find_one({"id": order_id})
        if not order:
            QMessageBox.warning(self, "Ошибка", "Заказ не найден")
            return

        existing = receipt_collection.find_one({"orderId": order_id})
        if existing:
            QMessageBox.information(self, "Инфо", "Счет на этот заказ уже выдан")
            return

        # Handle dishes data - it might be stored as a string or list
        dishes = order.get("dishes", [])
        if isinstance(dishes, str):
            try:
                dishes = ast.literal_eval(dishes)
            except (ValueError, SyntaxError):
                dishes = []

        amount = sum(item["price"] * item["quantity"] for item in dishes)

        receipt_collection.insert_one({
            "orderId": order["id"],
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "amount": amount,
            "paid": False,
            "waiterLogin": order.get("waiterLogin", "")
        })

        QMessageBox.information(self, "Успешно", "Счет выдан")
        self.receipt_created.emit()

    def edit_order(self):
        selected = self.orders_table.selectedItems()
        if not selected:
            QMessageBox.warning(self, "Ошибка", "Выберите заказ")
            return
        row = self.orders_table.currentRow()
        order_id = self.orders_table.item(row, 0).data(Qt.UserRole)
        order = order_collection.find_one({"id": order_id})
        if not order:
            QMessageBox.warning(self, "Ошибка", "Заказ не найден")
            return

        if order.get("status") in ["cancelled", "paid"]:
            QMessageBox.warning(self, "Ошибка", "Нельзя редактировать отменённый или оплаченный заказ")
            return
        receipt = receipt_collection.find_one({"orderId": order_id})
        if receipt:
            QMessageBox.warning(self, "Ошибка", "Нельзя редактировать заказ, по которому уже выдан счет")
            return

        customer = customer_collection.find_one({"id": order.get("customerId")})
        table = table_collection.find_one({"id": order.get("tableId")})

        dialog = QDialog(self)
        dialog.setWindowTitle("Редактировать заказ")
        layout = QFormLayout(dialog)

        name_edit = QLineEdit(customer.get("name", "") if customer else "")
        phone_edit = QLineEdit(customer.get("phone", "") if customer else "")

        table_combo = QComboBox()
        for t in table_collection.find({"isAvailable": True}):
            table_combo.addItem(f"Стол {t['tableNumber']} (мест: {t['seats']})", t["id"])
            if table and t["id"] == table["id"]:
                table_combo.setCurrentIndex(table_combo.count() - 1)

        menu_items = list(menu_collection.find())
        dishes_list = QListWidget()
        for item in menu_items:
            lw_item = QListWidgetItem(f"{item['name']} - {item['price']} руб.")
            lw_item.setData(Qt.UserRole, item)
            dishes_list.addItem(lw_item)

        # Handle dishes data - it might be stored as a string or list
        order_dishes = order.get("dishes", [])
        if isinstance(order_dishes, str):
            try:
                order_dishes = ast.literal_eval(order_dishes)
            except (ValueError, SyntaxError):
                order_dishes = []

        selected_dishes = []
        for d in order_dishes:
            for item in menu_items:
                if item["name"] == d["name"]:
                    selected_dishes.append({"item": item, "quantity": d["quantity"]})

        order_dishes_list = QListWidget()
        for d in selected_dishes:
            order_dishes_list.addItem(f"{d['item']['name']} x{d['quantity']}")

        def add_dish():
            selected = dishes_list.currentItem()
            if not selected:
                return
            item = selected.data(Qt.UserRole)
            quantity, ok = QInputDialog.getInt(dialog, "Количество", f"Сколько {item['name']} добавить?", 1, 1)
            if ok:
                found = False
                for d in selected_dishes:
                    if d["item"]["id"] == item["id"]:
                        d["quantity"] += quantity
                        found = True
                        break
                if not found:
                    selected_dishes.append({"item": item, "quantity": quantity})
                refresh_order_dishes()

        def remove_dish():
            selected_items = order_dishes_list.selectedItems()
            if not selected_items:
                return
            for item in selected_items:
                text = item.text()
                name = text.split(" x")[0]
                selected_dishes[:] = [d for d in selected_dishes if d['item']['name'] != name]
            refresh_order_dishes()

        def refresh_order_dishes():
            order_dishes_list.clear()
            for d in selected_dishes:
                order_dishes_list.addItem(f"{d['item']['name']} x{d['quantity']}")

        btn_add_dish = QPushButton("Добавить блюдо")
        btn_add_dish.setStyleSheet("""
            QPushButton {
                padding: 8px 16px;
                font-size: 14px;
                border-radius: 4px;
                background-color: #4CAF50;
                color: white;
                border: 1px solid #45a049;
                margin: 5px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3e8e41;
            }
        """)
        btn_add_dish.clicked.connect(add_dish)

        btn_remove_dish = QPushButton("Удалить выбранное блюдо")
        btn_remove_dish.setStyleSheet("""
            QPushButton {
                padding: 8px 16px;
                font-size: 14px;
                border-radius: 4px;
                background-color: #f44336;
                color: white;
                border: 1px solid #d32f2f;
                margin: 5px;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
            QPushButton:pressed {
                background-color: #b71c1c;
            }
        """)
        btn_remove_dish.clicked.connect(remove_dish)

        layout.addRow("Имя клиента:", name_edit)
        layout.addRow("Телефон клиента:", phone_edit)
        layout.addRow("Стол:", table_combo)
        layout.addRow("Меню:", dishes_list)
        layout.addRow(btn_add_dish)
        layout.addRow(btn_remove_dish)
        layout.addRow("Выбранные блюда:", order_dishes_list)

        btn_ok = QPushButton("Сохранить")
        btn_ok.setStyleSheet("""
            QPushButton {
                padding: 8px 16px;
                font-size: 14px;
                border-radius: 4px;
                background-color: #4CAF50;
                color: white;
                border: 1px solid #45a049;
                margin: 5px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3e8e41;
            }
        """)
        btn_cancel = QPushButton("Отмена")
        btn_cancel.setStyleSheet("""
            QPushButton {
                padding: 8px 16px;
                font-size: 14px;
                border-radius: 4px;
                background-color: #f44336;
                color: white;
                border: 1px solid #d32f2f;
                margin: 5px;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
            QPushButton:pressed {
                background-color: #b71c1c;
            }
        """)
        btn_box = QHBoxLayout()
        btn_box.addWidget(btn_ok)
        btn_box.addWidget(btn_cancel)
        layout.addRow(btn_box)

        def on_ok():
            name = name_edit.text().strip()
            phone = phone_edit.text().strip()
            table_id = table_combo.currentData()

            if not name or not phone or not table_id:
                QMessageBox.warning(dialog, "Ошибка", "Заполните все поля")
                return
            if not selected_dishes:
                QMessageBox.warning(dialog, "Ошибка", "Добавьте хотя бы одно блюдо")
                return

            customer = customer_collection.find_one({"phone": phone})
            if not customer:
                customer = customer_collection.insert_one({"name": name, "phone": phone})
                customer_id = customer["id"]
            else:
                customer_id = customer["id"]

            order_collection.update_one(
                {"id": order_id},
                {"$set": {
                    "customerId": customer_id,
                    "tableId": table_id,
                    "dishes": [{"name": d["item"]["name"], "price": d["item"]["price"], "quantity": d["quantity"]} for d in selected_dishes]
                }}
            )
            QMessageBox.information(dialog, "Успешно", "Заказ обновлен")
            self.load_orders()
            self.order_updated.emit()
            dialog.accept()

        btn_ok.clicked.connect(on_ok)
        btn_cancel.clicked.connect(dialog.reject)
        dialog.exec()

class OrderDialog(QDialog):
    def __init__(self, user):
        super().__init__()
        self.user = user
        self.setWindowTitle("Создать заказ")
        self.resize(400, 400)

        layout = QVBoxLayout(self)

        self.customer_name = QLineEdit()
        self.customer_phone = QLineEdit()
        self.table_combo = QComboBox()
        self.load_tables()

        self.menu_list = QListWidget()
        self.load_menu()

        self.selected_dishes = []

        btn_add_dish = QPushButton("Добавить в заказ")
        btn_add_dish.setStyleSheet("""
            QPushButton {
                padding: 8px 16px;
                font-size: 14px;
                border-radius: 4px;
                background-color: #4CAF50;
                color: white;
                border: 1px solid #45a049;
                margin: 5px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3e8e41;
            }
        """)
        btn_add_dish.clicked.connect(self.add_dish_to_order)

        btn_remove_dish = QPushButton("Удалить выбранное блюдо")
        btn_remove_dish.setStyleSheet("""
            QPushButton {
                padding: 8px 16px;
                font-size: 14px;
                border-radius: 4px;
                background-color: #f44336;
                color: white;
                border: 1px solid #d32f2f;
                margin: 5px;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
            QPushButton:pressed {
                background-color: #b71c1c;
            }
        """)
        btn_remove_dish.clicked.connect(self.remove_dish_from_order)

        btn_submit = QPushButton("Создать заказ")
        btn_submit.setStyleSheet("""
            QPushButton {
                padding: 8px 16px;
                font-size: 14px;
                border-radius: 4px;
                background-color: #2196F3;
                color: white;
                border: 1px solid #1976D2;
                margin: 5px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:pressed {
                background-color: #0D47A1;
            }
        """)
        btn_submit.clicked.connect(self.submit_order)

        layout.addWidget(QLabel("Имя клиента:"))
        layout.addWidget(self.customer_name)
        layout.addWidget(QLabel("Телефон клиента:"))
        layout.addWidget(self.customer_phone)
        layout.addWidget(QLabel("Стол:"))
        layout.addWidget(self.table_combo)
        layout.addWidget(QLabel("Меню:"))
        layout.addWidget(self.menu_list)
        layout.addWidget(btn_add_dish)
        layout.addWidget(btn_remove_dish)

        self.order_dishes_list = QListWidget()
        layout.addWidget(QLabel("Выбранные блюда:"))
        layout.addWidget(self.order_dishes_list)

        layout.addWidget(btn_submit)

    def load_tables(self):
        self.table_combo.clear()
        now = datetime.now()
        today = now.date()
        current_time = now.time()
        for table in table_collection.find({"isAvailable": True}):
            reservations = reservation_collection.find({
                "tableId": table["id"],
                "reservationDate": today.strftime("%Y-%m-%d"),
                "status": {"$ne": "cancelled"}
            })
            busy_now = False
            for res in reservations:
                start = datetime.strptime(res["startTime"], "%H:%M").time()
                end = datetime.strptime(res["endTime"], "%H:%M").time()
                if start <= current_time < end:
                    busy_now = True
                    break
            if not busy_now:
                self.table_combo.addItem(f"Стол {table['tableNumber']} (мест: {table['seats']})", table["id"])

    def load_menu(self):
        self.menu_list.clear()
        for item in menu_collection.find():
            lw_item = QListWidgetItem(f"{item['name']} - {item['price']} руб.")
            lw_item.setData(Qt.UserRole, item)
            self.menu_list.addItem(lw_item)

    def add_dish_to_order(self):
        selected = self.menu_list.currentItem()
        if not selected:
            return
        item = selected.data(Qt.UserRole)
        quantity, ok = QInputDialog.getInt(self, "Количество", f"Сколько {item['name']} добавить?", 1, 1)
        if ok:
            found = False
            for d in self.selected_dishes:
                if d["item"]["id"] == item["id"]:
                    d["quantity"] += quantity
                    found = True
                    break
            if not found:
                self.selected_dishes.append({"item": item, "quantity": quantity})
            self.refresh_order_dishes()

    def remove_dish_from_order(self):
        selected_items = self.order_dishes_list.selectedItems()
        if not selected_items:
            return
        for item in selected_items:
            text = item.text()
            name = text.split(" x")[0]
            self.selected_dishes[:] = [d for d in self.selected_dishes if d['item']['name'] != name]
        self.refresh_order_dishes()

    def refresh_order_dishes(self):
        self.order_dishes_list.clear()
        for d in self.selected_dishes:
            self.order_dishes_list.addItem(f"{d['item']['name']} x{d['quantity']}")

    def submit_order(self):
        name = self.customer_name.text().strip()
        phone = self.customer_phone.text().strip()
        table_id = self.table_combo.currentData()

        if not name or not phone or not table_id:
            QMessageBox.warning(self, "Ошибка", "Заполните все поля")
            return
        if not self.selected_dishes:
            QMessageBox.warning(self, "Ошибка", "Добавьте хотя бы одно блюдо")
            return

        customer = customer_collection.find_one({"phone": phone})
        if not customer:
            customer = customer_collection.insert_one({"name": name, "phone": phone})
            customer_id = customer["id"]
        else:
            customer_id = customer["id"]

        order_collection.insert_one({
            "customerId": customer_id,
            "tableId": table_id,
            "orderDate": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "dishes": [{"name": d["item"]["name"], "price": d["item"]["price"], "quantity": d["quantity"]} for d in self.selected_dishes],
            "status": "new",
            "waiterLogin": self.user["login"]
        })

        QMessageBox.information(self, "Успешно", "Заказ создан")
        self.accept()

class ReceiptsTab(QWidget):
    receipt_paid = Signal()

    def __init__(self, user):
        super().__init__()
        self.user = user
        layout = QVBoxLayout(self)

        self.receipts_table = QTableWidget()
        self.receipts_table.setColumnCount(7)
        self.receipts_table.setHorizontalHeaderLabels([
            "Клиент", "Дата", "Заказ", "Сумма", "Оплачен", "Ответственный", "Кто закрыл"
        ])

        button_style = """
            QPushButton {
                padding: 8px 16px;
                font-size: 14px;
                border-radius: 4px;
                margin: 5px;
                min-width: 120px;
            }
        """
        
        btn_pay = QPushButton("Оплатить счет")
        btn_pay.setStyleSheet(button_style + """
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: 1px solid #45a049;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3e8e41;
            }
        """)
        
        btn_create_total = QPushButton("Создать общий счет")
        btn_create_total.setStyleSheet(button_style + """
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: 1px solid #1976D2;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:pressed {
                background-color: #0D47A1;
            }
        """)
        
        layout.addWidget(self.receipts_table)
        layout.addWidget(btn_create_total)
        layout.addWidget(btn_pay)

        btn_create_total.clicked.connect(self.create_total_receipt)
        btn_pay.clicked.connect(self.pay_receipt)

        self.load_receipts()

    def load_receipts(self):
        self.receipts_table.setRowCount(0)
        for receipt in receipt_collection.find():
            row = self.receipts_table.rowCount()
            self.receipts_table.insertRow(row)

            order = None
            customer = None
            if "orderId" in receipt:
                order = order_collection.find_one({"id": receipt["orderId"]})
                if order:
                    customer = customer_collection.find_one({"id": order["customerId"]})
            elif "customerId" in receipt:
                customer = customer_collection.find_one({"id": receipt["customerId"]})

            self.receipts_table.setItem(row, 0, QTableWidgetItem(customer.get("name", "") if customer else ""))
            self.receipts_table.setItem(row, 1, QTableWidgetItem(str(receipt.get("date", ""))))
            self.receipts_table.setItem(row, 2, QTableWidgetItem(str(order["id"]) if order else ""))
            self.receipts_table.setItem(row, 3, QTableWidgetItem(str(receipt.get("amount", 0))))
            self.receipts_table.setItem(row, 4, QTableWidgetItem("Да" if receipt.get("paid", False) else "Нет"))
            self.receipts_table.setItem(row, 5, QTableWidgetItem(receipt.get("waiterLogin", "")))
            self.receipts_table.setItem(row, 6, QTableWidgetItem(receipt.get("closedBy", "") if receipt.get("paid") else ""))

            self.receipts_table.item(row, 0).setData(Qt.UserRole, receipt["id"])

    def pay_receipt(self):
        selected = self.receipts_table.selectedItems()
        if not selected:
            QMessageBox.warning(self, "Ошибка", "Выберите счет")
            return
        row = self.receipts_table.currentRow()
        receipt_id = self.receipts_table.item(row, 0).data(Qt.UserRole)
        receipt = receipt_collection.find_one({"id": receipt_id})
        if not receipt:
            QMessageBox.warning(self, "Ошибка", "Счет не найден")
            return
        if receipt.get("paid", False):
            QMessageBox.information(self, "Инфо", "Счет уже оплачен")
            return

        closed_by = getattr(self, "user", {}).get("login", "Неизвестно")

        receipt_collection.update_one(
            {"id": receipt_id},
            {"$set": {"paid": True, "paymentDate": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "closedBy": closed_by}}
        )

        if "orderIds" in receipt:
            order_collection.update_many(
                {"id": {"$in": receipt["orderIds"]}},
                {"$set": {"status": "paid"}}
            )
        elif "orderId" in receipt:
            order_collection.update_one({"id": receipt["orderId"]}, {"$set": {"status": "paid"}})

        QMessageBox.information(self, "Оплата", "Счет оплачен")
        self.load_receipts()
        self.receipt_paid.emit()

        main_window = self.window()
        if hasattr(main_window, "stats_tab"):
            main_window.stats_tab.load_stats()

    def create_total_receipt(self):
        selected = self.receipts_table.selectedItems()
        if not selected:
            QMessageBox.warning(self, "Ошибка", "Выберите счет клиента")
            return
        row = self.receipts_table.currentRow()
        customer_name = self.receipts_table.item(row, 0).text()
        customer = customer_collection.find_one({"name": customer_name})
        if not customer:
            QMessageBox.warning(self, "Ошибка", "Клиент не найден")
            return

        orders = list(order_collection.find({
            "customerId": customer["id"],
            "status": {"$ne": "paid"}
        }))
        if not orders:
            QMessageBox.information(self, "Инфо", "Нет неоплаченных заказов для этого клиента")
            return

        order_ids = [o["id"] for o in orders]
        existing = receipt_collection.find_one({"orderIds": ",".join(order_ids)})
        if existing:
            QMessageBox.information(self, "Инфо", "Общий счет уже создан")
            return

        amount = 0
        for order in orders:
            # Handle dishes data - it might be stored as a string or list
            dishes = order.get("dishes", [])
            if isinstance(dishes, str):
                try:
                    dishes = ast.literal_eval(dishes)
                except (ValueError, SyntaxError):
                    dishes = []
            amount += sum(item["price"] * item["quantity"] for item in dishes)

        receipt_collection.insert_one({
            "orderIds": ",".join(order_ids),
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "amount": amount,
            "paid": False,
            "waiterLogin": orders[0].get("waiterLogin", "") if orders else "",
            "customerId": customer["id"]
        })

        QMessageBox.information(self, "Успешно", "Общий счет создан")
        self.load_receipts()

class MenuTab(QWidget):
    def __init__(self, is_admin=False):
        super().__init__()
        layout = QVBoxLayout(self)

        self.menu_table = QTableWidget()
        self.menu_table.setColumnCount(5)
        self.menu_table.setHorizontalHeaderLabels(["Название", "Описание", "Цена", "Категория", "Ингредиенты"])

        button_style = """
            QPushButton {
                padding: 8px 16px;
                font-size: 14px;
                border-radius: 4px;
                margin: 5px;
                min-width: 120px;
            }
        """
        
        btn_add = QPushButton("Добавить блюдо")
        btn_add.setStyleSheet(button_style + """
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: 1px solid #45a049;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3e8e41;
            }
        """)
        
        btn_edit = QPushButton("Редактировать блюдо")
        btn_edit.setStyleSheet(button_style + """
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: 1px solid #1976D2;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:pressed {
                background-color: #0D47A1;
            }
        """)
        
        btn_delete = QPushButton("Удалить блюдо")
        btn_delete.setStyleSheet(button_style + """
            QPushButton {
                background-color: #f44336;
                color: white;
                border: 1px solid #d32f2f;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
            QPushButton:pressed {
                background-color: #b71c1c;
            }
        """)

        btn_layout = QHBoxLayout()
        if is_admin:
            btn_layout.addWidget(btn_add)
            btn_layout.addWidget(btn_edit)
            btn_layout.addWidget(btn_delete)

        layout.addWidget(self.menu_table)
        if is_admin:
            layout.addLayout(btn_layout)

        if is_admin:
            btn_add.clicked.connect(self.add_item)
            btn_edit.clicked.connect(self.edit_item)
            btn_delete.clicked.connect(self.delete_item)

        self.setLayout(layout)
        self.load_menu()

    def load_menu(self):
        self.menu_table.setRowCount(0)
        for item in menu_collection.find():
            row = self.menu_table.rowCount()
            self.menu_table.insertRow(row)
            self.menu_table.setItem(row, 0, QTableWidgetItem(item.get("name", "")))
            self.menu_table.setItem(row, 1, QTableWidgetItem(item.get("description", "")))
            self.menu_table.setItem(row, 2, QTableWidgetItem(str(item.get("price", ""))))
            self.menu_table.setItem(row, 3, QTableWidgetItem(str(item.get("category", ""))))
            ingredients = item.get("ingredients", [])
            if isinstance(ingredients, str):
                ingredients = ingredients.split(',')
            self.menu_table.setItem(row, 4, QTableWidgetItem(", ".join(ingredients)))
            self.menu_table.item(row, 0).setData(Qt.UserRole, item["id"])

    def add_item(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Добавить блюдо")
        layout = QFormLayout(dialog)
        name_edit = QLineEdit()
        desc_edit = QLineEdit()
        price_edit = QSpinBox()
        price_edit.setRange(0, 100000)
        category_edit = QLineEdit()
        ingredients_edit = QLineEdit()
        ingredients_edit.setPlaceholderText("Через запятую")

        layout.addRow("Название:", name_edit)
        layout.addRow("Описание:", desc_edit)
        layout.addRow("Цена:", price_edit)
        layout.addRow("Категория:", category_edit)
        layout.addRow("Ингредиенты:", ingredients_edit)

        btn_ok = QPushButton("Добавить")
        btn_ok.setStyleSheet("""
            QPushButton {
                padding: 8px 16px;
                font-size: 14px;
                border-radius: 4px;
                background-color: #4CAF50;
                color: white;
                border: 1px solid #45a049;
                margin: 5px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3e8e41;
            }
        """)
        btn_cancel = QPushButton("Отмена")
        btn_cancel.setStyleSheet("""
            QPushButton {
                padding: 8px 16px;
                font-size: 14px;
                border-radius: 4px;
                background-color: #f44336;
                color: white;
                border: 1px solid #d32f2f;
                margin: 5px;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
            QPushButton:pressed {
                background-color: #b71c1c;
            }
        """)
        btn_box = QHBoxLayout()
        btn_box.addWidget(btn_ok)
        btn_box.addWidget(btn_cancel)
        layout.addRow(btn_box)

        def on_ok():
            if not name_edit.text().strip():
                QMessageBox.warning(dialog, "Ошибка", "Введите название блюда")
                return
            menu_collection.insert_one({
                "name": name_edit.text().strip(),
                "description": desc_edit.text().strip(),
                "price": price_edit.value(),
                "category": category_edit.text().strip(),
                "ingredients": ingredients_edit.text().strip()
            })
            self.load_menu()
            dialog.accept()

        btn_ok.clicked.connect(on_ok)
        btn_cancel.clicked.connect(dialog.reject)
        dialog.exec()

    def edit_item(self):
        selected = self.menu_table.selectedItems()
        if not selected:
            QMessageBox.warning(self, "Ошибка", "Выберите блюдо")
            return
        row = self.menu_table.currentRow()
        item_id = self.menu_table.item(row, 0).data(Qt.UserRole)
        item = menu_collection.find_one({"id": item_id})
        if not item:
            QMessageBox.warning(self, "Ошибка", "Блюдо не найдено")
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("Редактировать блюдо")
        layout = QFormLayout(dialog)
        name_edit = QLineEdit(item.get("name", ""))
        desc_edit = QLineEdit(item.get("description", ""))
        price_edit = QSpinBox()
        price_edit.setRange(0, 100000)
        price_edit.setValue(float(item.get("price", 0)))
        category_edit = QLineEdit(item.get("category", ""))
        ingredients_edit = QLineEdit(item.get("ingredients", ""))

        layout.addRow("Название:", name_edit)
        layout.addRow("Описание:", desc_edit)
        layout.addRow("Цена:", price_edit)
        layout.addRow("Категория:", category_edit)
        layout.addRow("Ингредиенты:", ingredients_edit)

        btn_ok = QPushButton("Сохранить")
        btn_ok.setStyleSheet("""
            QPushButton {
                padding: 8px 16px;
                font-size: 14px;
                border-radius: 4px;
                background-color: #4CAF50;
                color: white;
                border: 1px solid #45a049;
                margin: 5px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3e8e41;
            }
        """)
        btn_cancel = QPushButton("Отмена")
        btn_cancel.setStyleSheet("""
            QPushButton {
                padding: 8px 16px;
                font-size: 14px;
                border-radius: 4px;
                background-color: #f44336;
                color: white;
                border: 1px solid #d32f2f;
                margin: 5px;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
            QPushButton:pressed {
                background-color: #b71c1c;
            }
        """)
        btn_box = QHBoxLayout()
        btn_box.addWidget(btn_ok)
        btn_box.addWidget(btn_cancel)
        layout.addRow(btn_box)

        def on_ok():
            if not name_edit.text().strip():
                QMessageBox.warning(dialog, "Ошибка", "Введите название блюда")
                return
            menu_collection.update_one(
                {"id": item_id},
                {"$set": {
                    "name": name_edit.text().strip(),
                    "description": desc_edit.text().strip(),
                    "price": price_edit.value(),
                    "category": category_edit.text().strip(),
                    "ingredients": ingredients_edit.text().strip()
                }}
            )
            self.load_menu()
            dialog.accept()

        btn_ok.clicked.connect(on_ok)
        btn_cancel.clicked.connect(dialog.reject)
        dialog.exec()

    def delete_item(self):
        selected = self.menu_table.selectedItems()
        if not selected:
            QMessageBox.warning(self, "Ошибка", "Выберите блюдо")
            return
        row = self.menu_table.currentRow()
        item_id = self.menu_table.item(row, 0).data(Qt.UserRole)
        reply = QMessageBox.question(self, "Удалить", "Удалить выбранное блюдо?", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            menu_collection.delete_one({"id": item_id})
            self.load_menu()

class StatsTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)

        self.stats_table = QTableWidget()
        self.stats_table.setColumnCount(2)
        self.stats_table.setHorizontalHeaderLabels(["Официант", "Закрыто счетов"])

        layout.addWidget(self.stats_table)
        self.setLayout(layout)
        self.load_stats()

    def load_stats(self):
        self.stats_table.setRowCount(0)
        stats = receipt_collection.aggregate([
            {"$match": {"paid": True, "closedBy": {"$ne": None}}},
            {"$group": {"_id": "$closedBy", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}}
        ])
        for stat in stats:
            row = self.stats_table.rowCount()
            self.stats_table.insertRow(row)
            self.stats_table.setItem(row, 0, QTableWidgetItem(str(stat["_id"])))
            self.stats_table.setItem(row, 1, QTableWidgetItem(str(stat["count"])))

        if hasattr(self.parent(), "stats_tab"):
            self.parent().stats_tab.load_stats()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = LoginWindow()
    window.show()
    sys.exit(app.exec())