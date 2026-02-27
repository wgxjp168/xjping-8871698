package com.ilbuy.data.config;

import com.ilbuy.data.entity.ProductEntity;
import com.ilbuy.data.entity.UserEntity;
import com.ilbuy.data.repository.ProductRepository;
import com.ilbuy.data.repository.UserRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.CommandLineRunner;
import org.springframework.stereotype.Component;

@Component
public class DataInitializer implements CommandLineRunner {

    private static final Logger log = LoggerFactory.getLogger(DataInitializer.class);
    private final UserRepository userRepo;
    private final ProductRepository productRepo;

    public DataInitializer(UserRepository userRepo, ProductRepository productRepo) {
        this.userRepo = userRepo;
        this.productRepo = productRepo;
    }

    @Override
    public void run(String... args) {
        if (userRepo.count() == 0) {
            UserEntity u1 = new UserEntity("zhangsan", "zhangsan@ilbuy.com", "13800138001", "张三");
            u1.setMemberLevel("VIP");
            UserEntity u2 = new UserEntity("lisi", "lisi@ilbuy.com", "13800138002", "李四");
            UserEntity u3 = new UserEntity("wangwu", "wangwu@ilbuy.com", "13800138003", "王五");
            u3.setMemberLevel("SVIP");
            userRepo.save(u1);
            userRepo.save(u2);
            userRepo.save(u3);
            log.info("初始化 3 个用户数据");
        }

        if (productRepo.count() == 0) {
            productRepo.save(new ProductEntity("智能手表Pro", "高清AMOLED屏幕，健康监测", "electronics", 1299.00, 200));
            productRepo.save(new ProductEntity("无线降噪耳机", "主动降噪，40小时续航", "electronics", 899.00, 500));
            productRepo.save(new ProductEntity("运动跑鞋飞翼", "轻量透气，碳板助力", "sports", 599.00, 300));
            productRepo.save(new ProductEntity("有机绿茶礼盒", "明前特级，罐装礼盒", "food", 168.00, 1000));
            productRepo.save(new ProductEntity("便携充电宝20000mAh", "双向快充，轻薄设计", "electronics", 199.00, 800));
            productRepo.save(new ProductEntity("纯棉T恤", "舒适透气，多色可选", "clothing", 89.00, 2000));
            productRepo.save(new ProductEntity("智能台灯", "护眼LED，色温调节", "home", 259.00, 150));
            productRepo.save(new ProductEntity("蓝牙音箱", "IPX7防水，360°环绕音", "electronics", 349.00, 400));
            log.info("初始化 8 个商品数据");
        }
    }
}
