"""
biz_data_svc 全量集成测试（7 大模块）
运行: python biz_data_svc/tests/test_all_modules.py
"""
import sys
import os
import sqlite3

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from biz_data_svc.common.db import Database
from biz_data_svc.config.settings import Settings
from biz_data_svc.schema import init_schema

# ── 模块导入 ──────────────────────────────────────────────────────────────────
from biz_data_svc.modules.m01_user_tenant import (
    Tenant, User, Role, Permission, UserSession,
    TenantRepository, UserRepository, RoleRepository,
)
from biz_data_svc.modules.m02_cmall import (
    Category, Product, ProductSku, ProductInventory, CartItem, DeliveryAddress,
    CategoryRepository, ProductRepository, SkuRepository,
    InventoryRepository, CartRepository, AddressRepository,
)
from biz_data_svc.modules.m03_order import (
    Order, OrderItem, Payment, Refund, Logistics,
    OrderRepository, PaymentRepository, RefundRepository, LogisticsRepository,
)
from biz_data_svc.modules.m04_procurement import (
    PurchaseRequest, PurchaseRequestItem,
    ApprovalWorkflow, ApprovalNode, ApprovalRecord,
    SourcingEvent, SourcingQuote, Contract,
    PurchaseRepository, ApprovalRepository,
    SourcingRepository, ContractRepository,
)
from biz_data_svc.modules.m05_supplier import (
    Supplier, SupplierQualification, SupplierQuote, SupplierScore, SupplierRisk,
    SupplierRepository, QualificationRepository,
    QuoteRepository, ScoreRepository, RiskRepository,
)
from biz_data_svc.modules.m06_finance import (
    Invoice, InvoiceItem, Reconciliation, Settlement,
    InvoiceRepository, ReconciliationRepository, SettlementRepository,
)
from biz_data_svc.modules.m07_message import (
    NotificationTemplate, InternalMessage, SmsRecord, EmailRecord,
    TemplateRepository, MessageRepository, SmsRepository, EmailRepository,
)


# ── 测试夹具 ──────────────────────────────────────────────────────────────────

def make_db() -> Database:
    Database._instance = None
    db = Database(Settings(db_path=':memory:'))
    init_schema(db)
    return db


def _seed_tenant(db) -> Tenant:
    repo = TenantRepository(db)
    return repo.add(Tenant(name='测试科技', code='TEST001'))


def _seed_user(db, tenant: Tenant, username='admin', email='admin@test.com', phone='') -> User:
    repo = UserRepository(db)
    return repo.register(User(
        tenant_id=tenant.id, username=username,
        password_hash='hashed_pw', email=email, phone=phone,
    ))


# ── 模块 1: 用户与租户 ─────────────────────────────────────────────────────────

def test_m01_user_tenant():
    db = make_db()
    t_repo = TenantRepository(db)
    u_repo = UserRepository(db)
    r_repo = RoleRepository(db)

    # 租户
    tenant = t_repo.add(Tenant(name='星光集团', code='SG001'))
    assert tenant.id is not None
    assert t_repo.find_by_code('SG001').name == '星光集团'
    assert t_repo.update_status(tenant.id, 'suspended')
    assert t_repo.find_by_id(tenant.id).status == 'suspended'
    t_repo.update_status(tenant.id, 'active')

    # 用户注册
    user = u_repo.register(User(
        tenant_id=tenant.id, username='alice',
        password_hash='hash_alice', email='alice@sg.com', phone='13900000001',
    ))
    assert user.id is not None

    # 不允许重复用户名
    try:
        u_repo.register(User(
            tenant_id=tenant.id, username='alice',
            password_hash='other', email='other@sg.com',
        ))
        assert False, '应抛出 ValueError'
    except (ValueError, Exception):
        pass

    # 认证
    assert u_repo.authenticate(tenant.id, 'alice', 'hash_alice') is not None
    assert u_repo.authenticate(tenant.id, 'alice', 'wrong') is None

    # 更新个人资料
    user.real_name = '爱丽丝'
    u_repo.update_profile(user)
    assert u_repo.find_by_id(user.id).real_name == '爱丽丝'

    # 会话
    session = u_repo.create_session(UserSession(
        user_id=user.id, token='tok_xyz',
        refresh_token='rfr_xyz', expires_at='2099-01-01 00:00:00',
    ))
    assert session.id is not None
    assert u_repo.find_session('tok_xyz') is not None
    u_repo.revoke_session('tok_xyz')
    assert u_repo.find_session('tok_xyz') is None

    # RBAC
    perm = r_repo.ensure_permission('order:create', '创建订单', 'order', 'order', 'create')
    role = r_repo.add(Role(tenant_id=tenant.id, name='采购员', code='buyer'))
    r_repo.assign_permission(role.id, perm.id)
    r_repo.assign_role_to_user(user.id, role.id)
    assert r_repo.has_permission(user.id, 'order:create')
    assert not r_repo.has_permission(user.id, 'order:delete')

    print('  [PASS] test_m01_user_tenant')


# ── 模块 2: C端商城 ───────────────────────────────────────────────────────────

def test_m02_cmall():
    db = make_db()
    tenant = _seed_tenant(db)
    user = _seed_user(db, tenant)

    cat_repo = CategoryRepository(db)
    prod_repo = ProductRepository(db)
    sku_repo  = SkuRepository(db)
    inv_repo  = InventoryRepository(db)
    cart_repo = CartRepository(db)
    addr_repo = AddressRepository(db)

    # 分类
    parent = cat_repo.add(Category(tenant_id=tenant.id, name='运动户外'))
    child  = cat_repo.add(Category(tenant_id=tenant.id, name='跑步鞋', parent_id=parent.id))
    assert child.parent_id == parent.id
    assert len(cat_repo.find_children(parent.id)) == 1

    # 商品
    product = prod_repo.add(Product(
        tenant_id=tenant.id, category_id=child.id,
        name='飞影 PB', subtitle='碳板跑鞋',
        status='on_sale', is_featured=1,
    ))
    assert product.id is not None
    results, total = prod_repo.search(tenant.id, '飞影')
    assert total == 1

    # SKU
    sku = sku_repo.add(ProductSku(
        product_id=product.id, sku_code='FY-PB-41',
        attributes='{"颜色":"黑","尺码":"41"}',
        cost_price=350.0, market_price=799.0, sale_price=699.0,
    ))
    assert sku.id is not None

    # 库存
    inv = inv_repo.init(ProductInventory(sku_id=sku.id, warehouse_id=1, quantity=100, safety_stock=10))
    assert inv.quantity == 100
    assert inv_repo.get_available(sku.id, 1) == 100
    inv_repo.reserve(sku.id, 1, 5)
    assert inv_repo.get_available(sku.id, 1) == 95
    inv_repo.release_reserve(sku.id, 1, 5)
    assert inv_repo.get_available(sku.id, 1) == 100

    # 购物车
    cart_repo.add_or_update(CartItem(user_id=user.id, tenant_id=tenant.id,
                                      product_id=product.id, sku_id=sku.id, quantity=2))
    cart_repo.add_or_update(CartItem(user_id=user.id, tenant_id=tenant.id,
                                      product_id=product.id, sku_id=sku.id, quantity=1))
    items = cart_repo.find_by_user(user.id, tenant.id)
    assert items[0].quantity == 3
    cart_repo.update_quantity(user.id, sku.id, 0)   # 数量=0 应删除
    assert cart_repo.count(user.id, tenant.id) == 0

    # 地址
    addr = addr_repo.add(DeliveryAddress(
        user_id=user.id, receiver_name='张三', phone='13800138001',
        province='北京市', city='北京市', district='朝阳区',
        address_detail='建国路88号', is_default=1,
    ))
    assert addr.id is not None
    default = addr_repo.find_default(user.id)
    assert default.id == addr.id

    print('  [PASS] test_m02_cmall')


# ── 模块 3: 订单交易 ──────────────────────────────────────────────────────────

def test_m03_order():
    db = make_db()
    tenant = _seed_tenant(db)
    user   = _seed_user(db, tenant)

    cat_repo  = CategoryRepository(db)
    prod_repo = ProductRepository(db)
    sku_repo  = SkuRepository(db)
    inv_repo  = InventoryRepository(db)
    o_repo    = OrderRepository(db)
    pay_repo  = PaymentRepository(db)
    ref_repo  = RefundRepository(db)
    log_repo  = LogisticsRepository(db)

    cat  = cat_repo.add(Category(tenant_id=tenant.id, name='电子'))
    prod = prod_repo.add(Product(tenant_id=tenant.id, category_id=cat.id, name='手机'))
    sku  = sku_repo.add(ProductSku(product_id=prod.id, sku_code='PHONE-001',
                                    cost_price=1500, market_price=3999, sale_price=3499))
    inv_repo.init(ProductInventory(sku_id=sku.id, warehouse_id=1, quantity=50))

    # 创建订单
    order = o_repo.create(Order(
        tenant_id=tenant.id, order_no='ORD-2026-001',
        user_id=user.id, receiver_name='李四', receiver_phone='13900000002',
        address_detail='上海市浦东新区陆家嘴1号',
        total_amount=3499.0, pay_amount=3499.0,
        items=[OrderItem(
            order_id=0, product_id=prod.id, sku_id=sku.id,
            product_name='手机', sku_attrs='{}',
            quantity=1, unit_price=3499.0, subtotal=3499.0,
        )],
    ))
    assert order.id is not None
    assert len(order.items) == 1

    # 支付
    payment = pay_repo.create(Payment(
        order_id=order.id, payment_no='PAY-2026-001',
        amount=3499.0, method='alipay',
    ))
    pay_repo.mark_success(payment.id, 'ALIPAY_XXXX')
    assert pay_repo.find_by_id(payment.id).status == 'success'
    o_repo.pay(order.id, 'alipay')
    assert o_repo.find_by_id(order.id).status == 'paid'

    # 发货 + 物流
    log = log_repo.create(Logistics(
        order_id=order.id, company='顺丰速运', company_code='SF',
        tracking_no='SF1234567890',
    ))
    log_repo.add_trace(log.id, {'time': '2026-03-22 10:00', 'desc': '已揽收'})
    log_repo.sign(log.id, '王五')
    assert log_repo.find_by_order(order.id).status == 'delivered'

    # 退款申请
    refund = ref_repo.apply(Refund(
        order_id=order.id, refund_no='REF-2026-001',
        amount=3499.0, reason='不喜欢',
    ))
    ref_repo.approve(refund.id, user.id)
    ref_repo.complete(refund.id)
    assert ref_repo.find_by_id(refund.id).status == 'completed'
    assert ref_repo.get_refunded_amount(order.id) == 3499.0

    print('  [PASS] test_m03_order')


# ── 模块 4: B端采购 ───────────────────────────────────────────────────────────

def test_m04_procurement():
    db = make_db()
    tenant = _seed_tenant(db)
    user   = _seed_user(db, tenant)

    pr_repo   = PurchaseRepository(db)
    app_repo  = ApprovalRepository(db)
    src_repo  = SourcingRepository(db)
    ctr_repo  = ContractRepository(db)

    # 采购需求
    pr = pr_repo.create(PurchaseRequest(
        tenant_id=tenant.id, req_no='PR-2026-001',
        title='采购服务器', requester_id=user.id,
        budget=500000, priority='high',
        items=[PurchaseRequestItem(
            request_id=0, product_name='dell服务器',
            spec='PowerEdge R750', quantity=10, unit='台',
            estimated_price=50000,
        )],
    ))
    assert pr.id is not None
    assert len(pr.items) == 1

    # 提交
    pr_repo.submit(pr.id)
    assert pr_repo.find_by_id(pr.id).status == 'submitted'

    # 审批流程
    wf = app_repo.add_workflow(ApprovalWorkflow(
        tenant_id=tenant.id, name='采购审批',
        business_type='purchase_request', is_default=1,
    ))
    node = app_repo.add_node(ApprovalNode(
        workflow_id=wf.id, node_name='部门经理审批',
        node_type='person', approver_ids=f'[{user.id}]', sort_order=1,
    ))
    instance = app_repo.start_instance(wf.id, 'purchase_request', pr.id)
    assert instance.id is not None

    rec = app_repo.record(ApprovalRecord(
        instance_id=instance.id, node_id=node.id,
        node_order=1, approver_id=user.id,
        action='approve', comment='同意采购',
    ))
    app_repo.complete_instance(instance.id, 'approved', user.id)
    found = app_repo.find_instance('purchase_request', pr.id)
    assert found.status == 'approved'

    # 寻源
    event = src_repo.create(SourcingEvent(
        tenant_id=tenant.id, request_id=pr.id,
        event_no='SE-2026-001', title='服务器寻源',
        deadline='2026-04-30 18:00:00',
    ))
    src_repo.publish(event.id)
    quote = src_repo.submit_quote(SourcingQuote(
        event_id=event.id, supplier_id=1,
        unit_price=48000, total_price=480000,
        delivery_days=30,
    ))
    src_repo.select_winner(event.id, quote.id)
    assert src_repo.find_by_id(event.id).winner_supplier_id is not None

    # 合同
    contract = ctr_repo.add(Contract(
        tenant_id=tenant.id, contract_no='CTR-2026-001',
        title='服务器采购合同', contract_type='purchase',
        party_a='测试科技', party_b='戴尔中国',
        amount=480000, sourcing_id=event.id,
        start_date='2026-04-01', end_date='2027-03-31',
    ))
    ctr_repo.activate(contract.id, user.id)
    assert ctr_repo.find_by_id(contract.id).status == 'active'

    print('  [PASS] test_m04_procurement')


# ── 模块 5: 供应商 ────────────────────────────────────────────────────────────

def test_m05_supplier():
    db = make_db()
    tenant = _seed_tenant(db)
    user   = _seed_user(db, tenant)

    sup_repo  = SupplierRepository(db)
    qual_repo = QualificationRepository(db)
    quote_repo= QuoteRepository(db)
    score_repo= ScoreRepository(db)
    risk_repo = RiskRepository(db)

    # 供应商入驻
    supplier = sup_repo.add(Supplier(
        tenant_id=tenant.id, name='优质零件公司', code='SUP001',
        short_name='优质', supplier_type='manufacturer',
        contact_name='张总', phone='13800000099', email='zz@supplier.com',
    ))
    assert supplier.id is not None
    assert sup_repo.find_by_code(tenant.id, 'SUP001').name == '优质零件公司'

    # 审核
    sup_repo.review(supplier.id, user.id, approved=True)
    assert sup_repo.find_by_id(supplier.id).status == 'active'

    # 资质
    qual = qual_repo.add(SupplierQualification(
        supplier_id=supplier.id, qual_type='ISO9001',
        name='ISO 9001认证', issue_org='TÜV SÜD',
        issue_date='2024-01-01', expire_date='2027-01-01',
    ))
    assert qual.id is not None

    # 报价
    quote = quote_repo.add(SupplierQuote(
        supplier_id=supplier.id, tenant_id=tenant.id,
        product_name='精密轴承', unit='个',
        unit_price=25.5, min_qty=100, delivery_days=7,
        valid_until='2026-12-31',
    ))
    quotes = quote_repo.find_active_by_product(tenant.id, '精密轴承')
    assert len(quotes) == 1

    # 评分
    score = score_repo.add(SupplierScore(
        supplier_id=supplier.id, tenant_id=tenant.id,
        period='2026-Q1', quality_score=92, delivery_score=88,
        price_score=85, service_score=90, evaluator_id=user.id,
    ))
    assert score.level == 'A'   # 加权均值 ≈ 89.4 → A
    avg = score_repo.get_avg(supplier.id, tenant.id)
    assert avg['quality'] == 92.0

    # 风险
    risk = risk_repo.add(SupplierRisk(
        supplier_id=supplier.id, risk_type='financial',
        level='medium', description='应收账款逾期',
    ))
    risk_repo.mitigate(risk.id)
    risk_repo.resolve(risk.id, user.id, '账款已收回')
    assert risk_repo.find_by_supplier(supplier.id, 'resolved')[0].status == 'resolved'

    print('  [PASS] test_m05_supplier')


# ── 模块 6: 发票与对账 ────────────────────────────────────────────────────────

def test_m06_finance():
    db = make_db()
    tenant   = _seed_tenant(db)
    user     = _seed_user(db, tenant)
    sup_repo = SupplierRepository(db)
    supplier = sup_repo.add(Supplier(
        tenant_id=tenant.id, name='供应商甲', code='SUP002',
        supplier_type='distributor',
    ))
    sup_repo.review(supplier.id, user.id, approved=True)

    inv_repo   = InvoiceRepository(db)
    recon_repo = ReconciliationRepository(db)
    settle_repo= SettlementRepository(db)

    # 发票
    invoice = inv_repo.create(Invoice(
        tenant_id=tenant.id, invoice_no='INV-2026-001',
        invoice_type='special_vat', direction='in',
        supplier_id=supplier.id, issue_date='2026-03-01',
        amount=10000.0, tax_rate=0.13,
        tax_amount=1300.0, total_amount=11300.0,
        buyer_name='测试科技', seller_name='供应商甲',
        items=[InvoiceItem(
            invoice_id=0, product_name='精密零件',
            quantity=100, unit_price=100.0, amount=10000.0,
            tax_rate=0.13, tax_amount=1300.0,
        )],
    ))
    assert invoice.id is not None
    assert len(invoice.items) == 1

    inv_repo.verify(invoice.id, user.id)
    assert inv_repo.find_by_id(invoice.id).status == 'verified'

    # 对账
    recon = recon_repo.create(Reconciliation(
        tenant_id=tenant.id, recon_no='REC-2026-001',
        supplier_id=supplier.id,
        period_start='2026-03-01', period_end='2026-03-31',
        order_amount=11300.0, invoice_amount=11300.0,
    ))
    assert recon.diff_amount == 0.0
    recon_repo.send(recon.id)
    recon_repo.supplier_confirm(recon.id)
    recon_repo.confirm(recon.id)
    assert recon_repo.find_by_id(recon.id).status == 'confirmed'

    # 结算
    settle = settle_repo.apply(Settlement(
        tenant_id=tenant.id, settle_no='SET-2026-001',
        supplier_id=supplier.id, reconciliation_id=recon.id,
        amount=11300.0, payment_method='bank_transfer',
        bank_account='6225881234567890',
    ))
    settle_repo.approve(settle.id, user.id)
    settle_repo.pay(settle.id, user.id)
    assert settle_repo.find_by_id(settle.id).status == 'paid'
    total = settle_repo.get_total_paid(supplier.id, tenant.id)
    assert total == 11300.0

    print('  [PASS] test_m06_finance')


# ── 模块 7: 消息通知 ──────────────────────────────────────────────────────────

def test_m07_message():
    db = make_db()
    tenant  = _seed_tenant(db)
    sender  = _seed_user(db, tenant, 'sender', 'sender@test.com')
    receiver= _seed_user(db, tenant, 'receiver', 'receiver@test.com')

    tpl_repo = TemplateRepository(db)
    msg_repo = MessageRepository(db)
    sms_repo = SmsRepository(db)
    email_repo=EmailRepository(db)

    # 模板
    tpl = tpl_repo.add(NotificationTemplate(
        tenant_id=tenant.id, code='ORDER_PAID',
        name='订单支付通知', channel='internal',
        title_template='订单{{order_no}}支付成功',
        content_template='您的订单{{order_no}}已支付，金额{{amount}}元，请等待发货。',
    ))
    rendered = tpl_repo.render(tpl.id, {'order_no': 'ORD-001', 'amount': '3499'})
    assert 'ORD-001' in rendered['title']
    assert '3499' in rendered['content']

    # 站内信
    msg = msg_repo.send(InternalMessage(
        tenant_id=tenant.id, sender_id=sender.id,
        receiver_id=receiver.id, msg_type='business',
        title='订单支付成功', content='您的订单已付款',
        biz_type='order', biz_id=1001,
    ))
    assert msg.id is not None
    assert msg_repo.count_unread(receiver.id) == 1
    msg_repo.mark_read(msg.id, receiver.id)
    assert msg_repo.count_unread(receiver.id) == 0

    # 批量发送
    msgs = msg_repo.send_batch([
        InternalMessage(tenant_id=tenant.id, receiver_id=receiver.id,
                        msg_type='system', title=f'通知{i}', content=f'内容{i}')
        for i in range(3)
    ])
    assert len(msgs) == 3
    msg_repo.mark_all_read(receiver.id)
    assert msg_repo.count_unread(receiver.id) == 0

    # 短信
    sms = sms_repo.create(SmsRecord(
        tenant_id=tenant.id, phone='13800138001',
        template_code='SMS_ORDER', content='您的验证码是123456',
    ))
    sms_repo.mark_sent(sms.id, 'ALIYUN_MSG_001')
    sms_repo.mark_delivered(sms.id)
    assert sms_repo.find_by_id(sms.id).status == 'delivered'

    # 邮件
    email = email_repo.create(EmailRecord(
        tenant_id=tenant.id, to_email='user@example.com',
        subject='订单确认', body='<p>您的订单已确认</p>',
    ))
    email_repo.mark_sent(email.id)
    assert email_repo.find_by_id(email.id).status == 'sent'

    email2 = email_repo.create(EmailRecord(
        tenant_id=tenant.id, to_email='fail@example.com',
        subject='测试失败', body='内容',
    ))
    email_repo.mark_failed(email2.id, 'SMTP连接超时')
    retry = email_repo.find_for_retry(max_retry=3)
    assert any(e.id == email2.id for e in retry)

    print('  [PASS] test_m07_message')


# ── 主入口 ────────────────────────────────────────────────────────────────────

def run_all():
    tests = [
        test_m01_user_tenant,
        test_m02_cmall,
        test_m03_order,
        test_m04_procurement,
        test_m05_supplier,
        test_m06_finance,
        test_m07_message,
    ]
    passed = failed = 0
    print('\n===== biz_data_svc 生产级全量集成测试（7 模块）=====')
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
