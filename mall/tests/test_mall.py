"""
商场数据存储层集成测试
运行方式: python -m pytest mall/tests/test_mall.py -v
         或直接运行: python mall/tests/test_mall.py
"""
import sqlite3
import sys
import os

# 确保可以从项目根目录导入
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from mall.database.schema import init_db
from mall.models import User, Category, Product, CartItem, Order, OrderItem
from mall.repositories import (
    UserRepository, CategoryRepository, ProductRepository,
    CartRepository, OrderRepository,
)


def get_test_conn() -> sqlite3.Connection:
    """创建内存数据库用于测试"""
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')
    init_db(conn)
    return conn


# ------------------------------------------------------------------ #
#  用户测试                                                             #
# ------------------------------------------------------------------ #

def test_user_add_and_find():
    conn = get_test_conn()
    repo = UserRepository(conn)

    user = User(username='alice', password='pass123', email='alice@example.com',
                phone='13800000001', address='北京市朝阳区')
    saved = repo.add(user)
    assert saved.id is not None

    found = repo.find_by_id(saved.id)
    assert found.username == 'alice'
    assert found.email == 'alice@example.com'
    print('  [PASS] test_user_add_and_find')


def test_user_update():
    conn = get_test_conn()
    repo = UserRepository(conn)

    user = repo.add(User(username='bob', password='pw', email='bob@example.com'))
    user.phone = '13900000002'
    ok = repo.update(user)
    assert ok

    updated = repo.find_by_id(user.id)
    assert updated.phone == '13900000002'
    print('  [PASS] test_user_update')


def test_user_authenticate():
    conn = get_test_conn()
    repo = UserRepository(conn)

    repo.add(User(username='carol', password='secret', email='carol@example.com'))
    found = repo.authenticate('carol', 'secret')
    assert found is not None
    assert found.username == 'carol'

    not_found = repo.authenticate('carol', 'wrong')
    assert not_found is None
    print('  [PASS] test_user_authenticate')


def test_user_delete():
    conn = get_test_conn()
    repo = UserRepository(conn)

    user = repo.add(User(username='dave', password='pw', email='dave@example.com'))
    ok = repo.delete(user.id)
    assert ok
    assert repo.find_by_id(user.id) is None
    print('  [PASS] test_user_delete')


# ------------------------------------------------------------------ #
#  分类测试                                                             #
# ------------------------------------------------------------------ #

def test_category_hierarchy():
    conn = get_test_conn()
    repo = CategoryRepository(conn)

    parent = repo.add(Category(name='电子产品', description='各类电子设备'))
    child = repo.add(Category(name='手机', description='智能手机', parent_id=parent.id))

    tops = repo.find_top_level()
    assert any(c.id == parent.id for c in tops)

    children = repo.find_children(parent.id)
    assert len(children) == 1
    assert children[0].name == '手机'
    print('  [PASS] test_category_hierarchy')


# ------------------------------------------------------------------ #
#  商品测试                                                             #
# ------------------------------------------------------------------ #

def test_product_crud():
    conn = get_test_conn()
    cat_repo = CategoryRepository(conn)
    prod_repo = ProductRepository(conn)

    cat = cat_repo.add(Category(name='服装'))
    product = prod_repo.add(Product(
        name='白色T恤', price=59.9, stock=100, category_id=cat.id,
        description='纯棉舒适',
    ))
    assert product.id is not None

    # 按分类查
    products = prod_repo.find_by_category(cat.id)
    assert len(products) == 1

    # 关键字搜索
    results = prod_repo.find_by_name('T恤')
    assert len(results) == 1

    # 价格区间
    in_range = prod_repo.find_by_price_range(50, 100)
    assert len(in_range) == 1
    print('  [PASS] test_product_crud')


def test_product_stock():
    conn = get_test_conn()
    cat_repo = CategoryRepository(conn)
    prod_repo = ProductRepository(conn)

    cat = cat_repo.add(Category(name='食品'))
    product = prod_repo.add(Product(name='苹果', price=5.0, stock=50, category_id=cat.id))

    ok = prod_repo.update_stock(product.id, -10)
    assert ok
    updated = prod_repo.find_by_id(product.id)
    assert updated.stock == 40

    # 库存不能为负
    fail = prod_repo.update_stock(product.id, -100)
    assert not fail
    print('  [PASS] test_product_stock')


# ------------------------------------------------------------------ #
#  购物车测试                                                            #
# ------------------------------------------------------------------ #

def test_cart_operations():
    conn = get_test_conn()
    user_repo = UserRepository(conn)
    cat_repo = CategoryRepository(conn)
    prod_repo = ProductRepository(conn)
    cart_repo = CartRepository(conn)

    user = user_repo.add(User(username='eve', password='pw', email='eve@example.com'))
    cat = cat_repo.add(Category(name='图书'))
    p1 = prod_repo.add(Product(name='Python编程', price=79.0, stock=20, category_id=cat.id))
    p2 = prod_repo.add(Product(name='数据结构', price=55.0, stock=15, category_id=cat.id))

    # 加入购物车
    cart_repo.add_item(CartItem(user_id=user.id, product_id=p1.id, quantity=2))
    cart_repo.add_item(CartItem(user_id=user.id, product_id=p2.id, quantity=1))

    items = cart_repo.find_by_user(user.id)
    assert len(items) == 2
    assert cart_repo.count(user.id) == 2

    # 累加数量
    cart_repo.add_item(CartItem(user_id=user.id, product_id=p1.id, quantity=1))
    item = cart_repo.find_item(user.id, p1.id)
    assert item.quantity == 3

    # 修改数量
    cart_repo.update_quantity(user.id, p1.id, 5)
    assert cart_repo.find_item(user.id, p1.id).quantity == 5

    # 移除商品
    cart_repo.remove_item(user.id, p2.id)
    assert cart_repo.count(user.id) == 1

    # 清空购物车
    cart_repo.clear(user.id)
    assert cart_repo.count(user.id) == 0
    print('  [PASS] test_cart_operations')


# ------------------------------------------------------------------ #
#  订单测试                                                             #
# ------------------------------------------------------------------ #

def test_order_create_and_query():
    conn = get_test_conn()
    user_repo = UserRepository(conn)
    cat_repo = CategoryRepository(conn)
    prod_repo = ProductRepository(conn)
    order_repo = OrderRepository(conn)

    user = user_repo.add(User(username='frank', password='pw', email='frank@example.com'))
    cat = cat_repo.add(Category(name='电器'))
    p = prod_repo.add(Product(name='电风扇', price=199.0, stock=30, category_id=cat.id))

    order = Order(
        user_id=user.id,
        total_amount=199.0,
        address='上海市浦东新区',
        items=[OrderItem(order_id=0, product_id=p.id, quantity=1, unit_price=199.0)],
    )
    saved = order_repo.create_order(order)
    assert saved.id is not None
    assert len(saved.items) == 1
    assert saved.items[0].id is not None

    # 查询
    found = order_repo.find_by_id(saved.id)
    assert found.total_amount == 199.0
    assert len(found.items) == 1

    # 用户订单列表
    user_orders = order_repo.find_by_user(user.id)
    assert len(user_orders) == 1
    print('  [PASS] test_order_create_and_query')


def test_order_status_update():
    conn = get_test_conn()
    user_repo = UserRepository(conn)
    cat_repo = CategoryRepository(conn)
    prod_repo = ProductRepository(conn)
    order_repo = OrderRepository(conn)

    user = user_repo.add(User(username='grace', password='pw', email='grace@example.com'))
    cat = cat_repo.add(Category(name='运动'))
    p = prod_repo.add(Product(name='跑鞋', price=299.0, stock=10, category_id=cat.id))

    order = Order(
        user_id=user.id,
        total_amount=299.0,
        address='广州市天河区',
        items=[OrderItem(order_id=0, product_id=p.id, quantity=1, unit_price=299.0)],
    )
    saved = order_repo.create_order(order)

    ok = order_repo.update_status(saved.id, 'paid')
    assert ok
    updated = order_repo.find_by_id(saved.id)
    assert updated.status == 'paid'

    by_status = order_repo.find_by_status('paid')
    assert any(o.id == saved.id for o in by_status)
    print('  [PASS] test_order_status_update')


# ------------------------------------------------------------------ #
#  主入口                                                               #
# ------------------------------------------------------------------ #

def run_all_tests():
    tests = [
        test_user_add_and_find,
        test_user_update,
        test_user_authenticate,
        test_user_delete,
        test_category_hierarchy,
        test_product_crud,
        test_product_stock,
        test_cart_operations,
        test_order_create_and_query,
        test_order_status_update,
    ]
    passed = 0
    failed = 0
    print('\n===== 商场数据存储层测试 =====')
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f'  [FAIL] {test.__name__}: {e}')
            failed += 1
    print(f'\n结果: {passed} 通过, {failed} 失败')
    return failed == 0


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
