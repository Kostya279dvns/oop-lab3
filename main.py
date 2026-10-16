import csv
import itertools
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from enum import Enum


class OrderStatus(Enum):
    NEW = "Нове"
    PAID = "Оплачене"
    SHIPPED = "Відправлене"
    CANCELLED = "Скасоване"


class ProductCategory(Enum):
    ELECTRONICS = "Електроніка"
    CLOTHING = "Одяг"
    FOOD = "Продукти харчування"
    OTHER = "Інше"


@dataclass
class Customer:
    username: str
    email: str
    city: str


class Product:
    def __init__(self, sku: str, name: str, price: float, stock: int,
                 category: ProductCategory = ProductCategory.OTHER):
        self.sku = sku
        self.name = name
        self.price = price
        self.stock = stock
        self.category = category

    @property
    def sku(self) -> str:
        return self._sku

    @sku.setter
    def sku(self, value: str):
        if not isinstance(value, str) or len(value.strip()) < 3:
            raise ValueError("Артикул має містити щонайменше 3 символи!")
        self._sku = value.strip()

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, value: str):
        if not isinstance(value, str) or len(value.strip()) < 3:
            raise ValueError("Назва товару має містити щонайменше 3 символи!")
        self._name = value.strip()

    @property
    def price(self) -> float:
        return self._price

    @price.setter
    def price(self, value: float):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("Ціна товару має бути числом!")
        if not 0 < value <= 1_000_000:
            raise ValueError("Ціна товару має бути в межах від 0 (не включно) до 1 000 000 грн!")
        self._price = float(value)

    @property
    def stock(self) -> int:
        return self._stock

    @stock.setter
    def stock(self, value: int):
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError("Кількість на складі має бути цілим числом!")
        if value < 0:
            raise ValueError("Кількість на складі не може бути від'ємною!")
        self._stock = value

    @property
    def category(self) -> ProductCategory:
        return self._category

    @category.setter
    def category(self, value: ProductCategory):
        if not isinstance(value, ProductCategory):
            raise ValueError("Категорія має бути елементом ProductCategory!")
        self._category = value

    def discount_rate(self) -> float:
        return 0.0

    def final_price(self) -> float:
        return round(self.price * (1 - self.discount_rate()), 2)

    def get_info(self) -> str:
        return (
            f"[{self.sku}] {self.name} | {self.category.value} | "
            f"{self.price:.2f} -> {self.final_price():.2f} грн | Залишок: {self.stock}"
        )

    def __lt__(self, other):
        if not isinstance(other, Product):
            return NotImplemented
        return self.final_price() < other.final_price()


class Electronics(Product):
    MAX_WARRANTY_MONTHS = 60

    def __init__(self, sku: str, name: str, price: float, stock: int, warranty_months: int):
        super().__init__(sku, name, price, stock, ProductCategory.ELECTRONICS)
        self.warranty_months = warranty_months

    @property
    def warranty_months(self) -> int:
        return self._warranty_months

    @warranty_months.setter
    def warranty_months(self, value: int):
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError("Гарантійний строк має бути цілим числом місяців!")
        if not 0 <= value <= self.MAX_WARRANTY_MONTHS:
            raise ValueError(f"Гарантійний строк має бути від 0 до {self.MAX_WARRANTY_MONTHS} місяців!")
        self._warranty_months = value

    def discount_rate(self) -> float:
        return 0.10

    def get_info(self) -> str:
        return f"{super().get_info()} | Гарантія: {self.warranty_months} міс."


class Clothing(Product):
    SIZES = ("XS", "S", "M", "L", "XL")

    def __init__(self, sku: str, name: str, price: float, stock: int, size: str):
        super().__init__(sku, name, price, stock, ProductCategory.CLOTHING)
        self.size = size

    @property
    def size(self) -> str:
        return self._size

    @size.setter
    def size(self, value: str):
        if value not in self.SIZES:
            raise ValueError(f"Розмір має бути одним із: {', '.join(self.SIZES)}!")
        self._size = value

    def discount_rate(self) -> float:
        return 0.20

    def get_info(self) -> str:
        return f"{super().get_info()} | Розмір: {self.size}"


class FoodProduct(Product):
    EXPIRING_SOON_DAYS = 3

    def __init__(self, sku: str, name: str, price: float, stock: int, expiry_date: date):
        super().__init__(sku, name, price, stock, ProductCategory.FOOD)
        self.expiry_date = expiry_date

    @property
    def expiry_date(self) -> date:
        return self._expiry_date

    @expiry_date.setter
    def expiry_date(self, value: date):
        if not isinstance(value, date) or value < date.today():
            raise ValueError("Термін придатності не може бути в минулому!")
        self._expiry_date = value

    def discount_rate(self) -> float:
        days_left = (self.expiry_date - date.today()).days
        return 0.30 if days_left <= self.EXPIRING_SOON_DAYS else 0.0

    def get_info(self) -> str:
        return f"{super().get_info()} | Придатний до: {self.expiry_date:%Y-%m-%d}"


class ShoppingCart:
    def __init__(self):
        self._lines: dict[str, tuple[Product, int]] = {}

    def add(self, product: Product, quantity: int):
        if not isinstance(product, Product):
            raise TypeError("До кошика можна додати лише об'єкти типу Product!")
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity < 1:
            raise ValueError("Кількість у кошику має бути цілим числом не менше 1!")
        _, current = self._lines.get(product.sku, (product, 0))
        self._lines[product.sku] = (product, current + quantity)

    def lines(self) -> list[tuple[Product, int]]:
        return list(self._lines.values())

    @property
    def total(self) -> float:
        return sum(product.final_price() * quantity for product, quantity in self._lines.values())

    def __len__(self) -> int:
        return len(self._lines)


class Order:
    MAX_QUANTITY = 10
    _id_counter = itertools.count(1)

    def __init__(self, customer: Customer, product: Product, quantity: int):
        self.customer = customer
        self.product = product
        self.quantity = quantity
        self.status = OrderStatus.NEW
        self.created_at = datetime.now()
        self.order_id = f"ORD-{next(Order._id_counter):03d}"

    @property
    def quantity(self) -> int:
        return self._quantity

    @quantity.setter
    def quantity(self, value: int):
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError("Кількість у замовленні має бути цілим числом!")
        if not 1 <= value <= self.MAX_QUANTITY:
            raise ValueError(f"Кількість у замовленні має бути від 1 до {self.MAX_QUANTITY}!")
        if value > self.product.stock:
            raise ValueError(f"Недостатньо товару на складі (доступно: {self.product.stock})!")
        self._quantity = value

    @property
    def status(self) -> OrderStatus:
        return self._status

    @status.setter
    def status(self, value: OrderStatus):
        if not isinstance(value, OrderStatus):
            raise ValueError("Статус має бути елементом OrderStatus!")
        self._status = value

    @property
    def total(self) -> float:
        return self.product.final_price() * self._quantity


class StoreManager:
    def __init__(self):
        self._products: list[Product] = []
        self._orders: list[Order] = []

    def add_product(self, product: Product):
        if not isinstance(product, Product):
            raise TypeError("Менеджер приймає лише об'єкти типу Product!")
        if any(item.sku == product.sku for item in self._products):
            raise ValueError(f"Товар з артикулом {product.sku} уже існує!")
        self._products.append(product)
        print(f"Додано: {product.get_info()}")

    def add_orders(self, orders: list[Order]):
        self._orders.extend(orders)

    def show_all(self, sort_by_price: bool = False):
        title = "за ціною" if sort_by_price else "у порядку додавання"
        print(f"\n--- Усі товари ({title}) ---")
        products = sorted(self._products) if sort_by_price else self._products
        for product in products:
            print(product.get_info())

    def __getitem__(self, sku: str) -> Product:
        for product in self._products:
            if product.sku == sku:
                return product
        raise KeyError(f"Товар з артикулом {sku} не знайдено")

    def __iter__(self):
        return iter([product for product in self._products if product.stock > 0])

    def low_stock(self, threshold: int):
        for product in self._products:
            if product.stock < threshold:
                yield product

    def export_sales_csv(self, path: str):
        with open(path, "w", newline="", encoding="utf-8-sig") as file:
            writer = csv.writer(file, delimiter=";")
            writer.writerow(["Замовлення", "Дата", "Покупець", "Артикул", "Товар",
                             "Категорія", "Кількість", "Ціна за од., грн", "Сума, грн", "Статус"])
            for order in self._orders:
                writer.writerow([
                    order.order_id,
                    order.created_at.strftime("%Y-%m-%d %H:%M"),
                    order.customer.username,
                    order.product.sku,
                    order.product.name,
                    order.product.category.value,
                    order.quantity,
                    f"{order.product.final_price():.2f}",
                    f"{order.total:.2f}",
                    order.status.value,
                ])
        revenue = sum(order.total for order in self._orders)
        print(f"Звіт збережено: {path} (замовлень: {len(self._orders)}, виручка: {revenue:.2f} грн)")


class Checkout:
    def __init__(self, store: StoreManager, customer: Customer, cart: ShoppingCart):
        self._store = store
        self._customer = customer
        self._cart = cart
        self._orders: list[Order] = []

    def __enter__(self):
        return self

    def place_orders(self):
        for product, quantity in self._cart.lines():
            order = Order(self._customer, product, quantity)
            product.stock -= quantity
            self._orders.append(order)

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type is None:
            for order in self._orders:
                order.status = OrderStatus.PAID
            self._store.add_orders(self._orders)
            print(f"[Checkout] Оформлено замовлень: {len(self._orders)}")
            return False
        for order in self._orders:
            order.product.stock += order.quantity
            order.status = OrderStatus.CANCELLED
        print(f"[Checkout] Помилка ({exc_value}) Залишки відновлено, замовлення скасовано")
        return False


if __name__ == "__main__":
    customer = Customer(username="Anna", email="anna@example.com", city="Vinnytsia")
    store = StoreManager()

    print("--- Створення товарів ---")
    laptop = Electronics("EL-001", "Ноутбук Lenovo", 30000, 5, warranty_months=24)
    jacket = Clothing("CL-001", "Куртка зимова", 2500, 4, size="L")
    milk = FoodProduct("FD-001", "Молоко 2.5%", 40, 20, date.today() + timedelta(days=2))
    cheese = FoodProduct("FD-002", "Сир твердий", 250, 2, date.today() + timedelta(days=30))
    for product in (laptop, jacket, milk, cheese):
        store.add_product(product)

    store.show_all()
    store.show_all(sort_by_price=True)

    print("\n--- Поліморфізм: однаковий метод, різна знижка ---")
    for product in store:
        print(f"{type(product).__name__}: знижка {product.discount_rate():.0%}, "
              f"{product.price:.2f} -> {product.final_price():.2f} грн")

    print("\n--- Порівняння та пошук за артикулом ---")
    print(f"Ноутбук дешевший за куртку: {laptop < jacket}")
    print(f"store['CL-001'] -> {store['CL-001'].name}")

    print("\n--- Успішне оформлення замовлення ---")
    cart = ShoppingCart()
    cart.add(laptop, 1)
    cart.add(milk, 3)
    print(f"Сума кошика: {cart.total:.2f} грн")
    with Checkout(store, customer, cart) as checkout:
        checkout.place_orders()
    print(f"Залишок ноутбуків: {laptop.stock}, молока: {milk.stock}")

    print("\n--- Невдале оформлення (відновлення залишків) ---")
    broken_cart = ShoppingCart()
    broken_cart.add(cheese, 1)
    broken_cart.add(jacket, 9)
    print(f"Залишок до: сир {cheese.stock}, куртка {jacket.stock}")
    try:
        with Checkout(store, customer, broken_cart) as checkout:
            checkout.place_orders()
    except ValueError as e:
        print(f"[ПОМИЛКА ВАЛІДАЦІЇ] {e}")
    print(f"Залишок після: сир {cheese.stock}, куртка {jacket.stock}")

    print("\n--- Генератор: залишок нижче 5 ---")
    for product in store.low_stock(5):
        print(product.get_info())

    print("\n--- CSV-звіт про продажі ---")
    store.export_sales_csv("sales_report.csv")

    print("\n--- Інспекція внутрішнього стану (vars) ---")
    print(vars(laptop))

    print("\n--- Запуск краш-тестів ---")
    crash_tests = {
        "Від'ємна ціна": lambda: Electronics("EL-002", "Смартфон", -100, 3, 12),
        "Дробова кількість": lambda: Clothing("CL-002", "Футболка", 500, 2.5, "M"),
        "Гарантія 100 міс.": lambda: Electronics("EL-003", "Планшет", 9000, 3, 100),
        "Прострочений продукт": lambda: FoodProduct("FD-003", "Йогурт", 30, 5, date.today() - timedelta(days=1)),
        "Розмір 5XL": lambda: Clothing("CL-003", "Светр", 1200, 3, "5XL"),
        "Дублікат артикулу": lambda: store.add_product(Electronics("EL-001", "Ноутбук Dell", 28000, 2, 12)),
        "Сторонній об'єкт у менеджері": lambda: store.add_product("не товар"),
        "Замовлення 11 шт.": lambda: Order(customer, milk, 11),
    }
    for test_name, create_invalid in crash_tests.items():
        try:
            create_invalid()
        except (ValueError, TypeError) as error:
            print(f"{test_name}: {error}")