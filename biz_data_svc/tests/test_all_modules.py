"""
biz-data-svc 全量集成测试（7 个模块）
运行: python -m pytest biz-data-svc/tests/ -v
  或: python biz-data-svc/tests/test_all_modules.py
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import sqlite3
from biz_data_svc.common.db import Database
from biz_data_svc.schema import init_schema

# 模块导入
from biz_data_svc.modules.m01_user_tenant import (
    Tenant, User, UserSession, TenantRepository, UserRepository,
)
from biz_data_svc.modules.m02_mall import (
    Mall, Floor, Shop, MallRepository, ShopRepository,
)
from biz_data_svc.modules.m03_staff import (
    Role, Permission, Staff, RoleRepository, StaffRepository,
)
from biz_data_svc.modules.m04_product import (
    Category, Brand, Product, CategoryRepository, ProductRepository,
)
from biz_data_svc.modules.m05_order import (
    Customer, Order, OrderItem, Payment,
    CustomerRepository, OrderRepository, PaymentRepository,
)
from biz_data_svc.modules.m06_inventory import (
    Warehouse, Inventory, StockMovement,
    WarehouseRepository, InventoryRepository,
)
from biz_data_svc.modules.m07_marketing import (
    Promotion, Coupon, CouponRecord,
    PromotionRepository, CouponRepository,
)


# ------------------------------------------------------------------ #
#  测试夹具                                                             #
# ------------------------------------------------------------------ #

def make_db() -> Database:
    """每个测试用独立内存库"""
    # 重置单例
    Database._instance = None
    from biz_data_svc.config.settings import Settings
    db = Database(Settings(db_path=':memory:'))
    init_schema(db)
    return db


# ------------------------------------------------------------------ #
#  模块 1：用户与租户                                                    #
# ------------------------------------------------------------------ #

def test_m01_tenant_user():
    db = make_db()
    t_repo = TenantRepository(db)
    u_repo = UserRepository(db)

    tenant = t_repo.add(Tenant(name='测试商场', code='TEST001'))
    assert tenant.id is not None

    # 升级套餐
    ok = t_repo.update_plan(tenant.id, 'pro')
    assert ok
    assert t_repo.find_by_id(tenant.id).plan == 'pro'

    # 用户
    user = u_repo.add(User(tenant_id=tenant.id, username='admin',
                           password='admin123', email='admin@test.com'))
    assert user.id is not None

    # 认证
    found = u_repo.authenticate(tenant.id, 'admin', 'admin123')
    assert found is not None

    # 会话
    session = u_repo.create_session(UserSession(
        user_id=user.id, token='tok_abc123',
        expires_at='2099-01-01 00:00:00',
    ))
    assert session.id is not None
    assert u_repo.find_session('tok_abc123') is not None

    u_repo.revoke_session('tok_abc123')
    assert u_repo.find_session('tok_abc123') is None
    print('  [PASS] test_m01_tenant_user')


# ------------------------------------------------------------------ #
#  模块 2：商场                                                          #
# ------------------------------------------------------------------ #

def test_m02_mall():
    db = make_db()
    t_repo = TenantRepository(db)
    m_repo = MallRepository(db)
    s_repo = ShopRepository(db)

    tenant = t_repo.add(Tenant(name='星光商场', code='SG001'))
    mall = m_repo.add(Mall(tenant_id=tenant.id, name='星光广场',
                           city='上海', province='上海'))
    assert mall.id is not None

    floor = m_repo.add_floor(Floor(mall_id=mall.id, floor_no='1F', description='一楼'))
    assert floor.id is not None
    assert len(m_repo.list_floors(mall.id)) == 1

    shop = s_repo.add(Shop(mall_id=mall.id, floor_id=floor.id,
                           name='星巴克', shop_no='1F-01', area=80.0))
    assert shop.id is not None

    # 状态变更
    s_repo.update_status(shop.id, 'leased')
    assert s_repo.find_by_id(shop.id).status == 'leased'

    vacant = s_repo.find_vacant(mall.id)
    assert len(vacant) == 0
    print('  [PASS] test_m02_mall')


# ------------------------------------------------------------------ #
#  模块 3：员工与角色                                                    #
# ------------------------------------------------------------------ #

def test_m03_staff():
    db = make_db()
    t_repo = TenantRepository(db)
    r_repo = RoleRepository(db)
    s_repo = StaffRepository(db)

    tenant = t_repo.add(Tenant(name='T3', code='T3'))

    # 权限 & 角色
    perm = r_repo.ensure_permission('order:read', '查看订单')
    role = r_repo.add(Role(tenant_id=tenant.id, name='店长'))
    r_repo.assign_permission(role.id, perm.id)

    roles = r_repo.find_by_tenant(tenant.id)
    assert len(roles) == 1
    assert len(roles[0].permissions) == 1

    # 员工
    staff = s_repo.add(Staff(tenant_id=tenant.id, name='张三',
                              employee_no='E001', position='店长'))
    s_repo.assign_role(staff.id, role.id)

    assert s_repo.has_permission(staff.id, 'order:read')
    assert not s_repo.has_permission(staff.id, 'order:delete')
    print('  [PASS] test_m03_staff')


# ------------------------------------------------------------------ #
#  模块 4：商品与类目                                                    #
# ------------------------------------------------------------------ #

def test_m04_product():
    db = make_db()
    t_repo = TenantRepository(db)
    c_repo = CategoryRepository(db)
    p_repo = ProductRepository(db)

    tenant = t_repo.add(Tenant(name='T4', code='T4'))

    brand = c_repo.add_brand(Brand(tenant_id=tenant.id, name='耐克'))
    cat = c_repo.add(Category(tenant_id=tenant.id, name='运动鞋'))

    product = p_repo.add(Product(
        tenant_id=tenant.id, category_id=cat.id, brand_id=brand.id,
        name='Air Max 90', sku='SKU001', cost_price=300.0, sale_price=899.0,
    ))
    assert product.id is not None

    # 搜索
    results = p_repo.search(tenant.id, 'Air')
    assert len(results) == 1

    # 价格区间
    in_range = p_repo.find_by_price_range(tenant.id, 500, 1000)
    assert len(in_range) == 1

    # 下架
    p_repo.update_status(product.id, 'off_shelf')
    assert p_repo.find_by_id(product.id).status == 'off_shelf'

    # 分页
    items, total = p_repo.paginate_by_tenant(tenant.id, page=1, size=10)
    assert total == 1
    print('  [PASS] test_m04_product')


# ------------------------------------------------------------------ #
#  模块 5：订单与支付                                                    #
# ------------------------------------------------------------------ #

def test_m05_order():
    db = make_db()
    t_repo = TenantRepository(db)
    c_repo = CategoryRepository(db)
    p_repo = ProductRepository(db)
    cu_repo = CustomerRepository(db)
    o_repo = OrderRepository(db)
    pay_repo = PaymentRepository(db)

    tenant = t_repo.add(Tenant(name='T5', code='T5'))
    cat = c_repo.add(Category(tenant_id=tenant.id, name='电器'))
    product = p_repo.add(Product(
        tenant_id=tenant.id, category_id=cat.id,
        name='空调', sku='AC001', cost_price=1500.0, sale_price=2999.0,
    ))
    customer = cu_repo.add(Customer(tenant_id=tenant.id, name='李四', phone='13800000001'))

    order = o_repo.create(Order(
        tenant_id=tenant.id, order_no='ORD20260301001',
        total_amount=2999.0, pay_amount=2999.0,
        customer_id=customer.id,
        items=[OrderItem(order_id=0, product_id=product.id,
                         product_name='空调', quantity=1,
                         unit_price=2999.0, subtotal=2999.0)],
    ))
    assert order.id is not None
    assert len(order.items) == 1

    # 支付
    payment = pay_repo.create(Payment(
        order_id=order.id, payment_no='PAY001',
        amount=2999.0, method='alipay',
    ))
    ok = pay_repo.mark_success(payment.id)
    assert ok
    assert pay_repo.find_by_id(payment.id).status == 'success'

    # 订单状态流转
    o_repo.update_status(order.id, 'paid')
    o_repo.update_status(order.id, 'delivered')
    assert o_repo.find_by_id(order.id).status == 'delivered'

    # 客户订单列表
    orders = o_repo.find_by_customer(customer.id)
    assert len(orders) == 1

    # 分页
    items, total = o_repo.paginate_by_tenant(tenant.id, page=1, size=10)
    assert total == 1
    print('  [PASS] test_m05_order')


# ------------------------------------------------------------------ #
#  模块 6：库存与仓储                                                    #
# ------------------------------------------------------------------ #

def test_m06_inventory():
    db = make_db()
    t_repo = TenantRepository(db)
    c_repo = CategoryRepository(db)
    p_repo = ProductRepository(db)
    w_repo = WarehouseRepository(db)
    inv_repo = InventoryRepository(db)

    tenant = t_repo.add(Tenant(name='T6', code='T6'))
    cat = c_repo.add(Category(tenant_id=tenant.id, name='食品'))
    product = p_repo.add(Product(
        tenant_id=tenant.id, category_id=cat.id,
        name='牛奶', sku='MILK001', cost_price=3.0, sale_price=5.0,
    ))
    warehouse = w_repo.add(Warehouse(tenant_id=tenant.id, name='主仓'))

    # 初始化库存
    inv = inv_repo.init_stock(Inventory(
        warehouse_id=warehouse.id, product_id=product.id,
        quantity=100, safety_stock=20,
    ))
    assert inv.quantity == 100

    # 入库
    inv_repo.move_stock(warehouse.id, product.id, 50, 'in', remark='采购入库')
    updated = inv_repo.find_by_warehouse_product(warehouse.id, product.id)
    assert updated.quantity == 150

    # 出库
    inv_repo.move_stock(warehouse.id, product.id, -30, 'out', ref_type='order', ref_id=1)
    updated = inv_repo.find_by_warehouse_product(warehouse.id, product.id)
    assert updated.quantity == 120

    # 库存不足时拒绝出库
    try:
        inv_repo.move_stock(warehouse.id, product.id, -200, 'out')
        assert False, '应该抛出 ValueError'
    except ValueError:
        pass

    # 设置安全库存并查低库存
    inv_repo.set_safety_stock(warehouse.id, product.id, 150)
    low = inv_repo.find_below_safety(warehouse.id)
    assert len(low) == 1

    # 查流水
    movements = inv_repo.list_movements(warehouse.id)
    assert len(movements) == 2   # in + out
    print('  [PASS] test_m06_inventory')


# ------------------------------------------------------------------ #
#  模块 7：营销与促销                                                    #
# ------------------------------------------------------------------ #

def test_m07_marketing():
    db = make_db()
    t_repo = TenantRepository(db)
    c_repo = CategoryRepository(db)
    p_repo = ProductRepository(db)
    cu_repo = CustomerRepository(db)
    o_repo = OrderRepository(db)
    pr_repo = PromotionRepository(db)
    cp_repo = CouponRepository(db)

    tenant = t_repo.add(Tenant(name='T7', code='T7'))
    customer = cu_repo.add(Customer(tenant_id=tenant.id, name='王五', phone='13900000002'))

    # 建一个真实订单供核销引用
    cat = c_repo.add(Category(tenant_id=tenant.id, name='测试类目'))
    product = p_repo.add(Product(
        tenant_id=tenant.id, category_id=cat.id,
        name='测试商品', sku='TEST001', cost_price=100.0, sale_price=500.0,
    ))
    real_order = o_repo.create(Order(
        tenant_id=tenant.id, order_no='ORD_M7_001',
        total_amount=500.0, pay_amount=400.0, discount_amount=100.0,
        customer_id=customer.id,
        items=[OrderItem(order_id=0, product_id=product.id,
                         product_name='测试商品', quantity=1,
                         unit_price=500.0, subtotal=500.0)],
    ))

    # 促销活动
    promo = pr_repo.add(Promotion(
        tenant_id=tenant.id, name='双十一折扣',
        promo_type='discount', discount_rate=0.8,
        start_at='2026-11-11 00:00:00', end_at='2026-11-12 00:00:00',
        status='active',
    ))
    assert promo.id is not None

    # 优惠券
    coupon = cp_repo.add(Coupon(
        tenant_id=tenant.id, code='COUPON100',
        face_value=100.0, min_amount=500.0,
        start_at='2026-01-01 00:00:00', end_at='2099-12-31 23:59:59',
        total_qty=10,
    ))
    assert coupon.id is not None

    # 领券
    record = cp_repo.claim(coupon.id, customer.id)
    assert record.id is not None

    # 重复领券应失败
    try:
        cp_repo.claim(coupon.id, customer.id)
        assert False, '应该抛出 ValueError'
    except ValueError:
        pass

    # 核销（关联到真实订单）
    ok = cp_repo.use(coupon.id, customer.id, order_id=real_order.id)
    assert ok

    # 查客户券
    records = cp_repo.list_customer_coupons(customer.id)
    assert len(records) == 1 and records[0].order_id == real_order.id
    print('  [PASS] test_m07_marketing')


# ------------------------------------------------------------------ #
#  主入口                                                               #
# ------------------------------------------------------------------ #

def run_all():
    tests = [
        test_m01_tenant_user,
        test_m02_mall,
        test_m03_staff,
        test_m04_product,
        test_m05_order,
        test_m06_inventory,
        test_m07_marketing,
    ]
    passed = failed = 0
    print('\n===== biz-data-svc 7模块集成测试 =====')
    for t in tests:
        try:
            t()
            passed += 1
        except Exception as e:
            import traceback
            print(f'  [FAIL] {t.__name__}: {e}')
            traceback.print_exc()
            failed += 1
    print(f'\n结果: {passed} 通过, {failed} 失败')
    return failed == 0


if __name__ == '__main__':
    success = run_all()
    sys.exit(0 if success else 1)
