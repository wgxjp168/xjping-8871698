package com.ilbuy.data.service;

import com.ilbuy.data.entity.ProductEntity;
import com.ilbuy.data.repository.ProductRepository;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import java.util.List;

@Service
public class DataProductService {

    private final ProductRepository repo;

    public DataProductService(ProductRepository repo) { this.repo = repo; }

    public List<ProductEntity> findAll() { return repo.findAll(); }
    public List<ProductEntity> findByCategory(String cat) { return repo.findByCategory(cat); }
    public ProductEntity findById(String id) { return repo.findById(id).orElse(null); }
    public ProductEntity save(ProductEntity p) { return repo.save(p); }
    public void delete(String id) { repo.deleteById(id); }
    public List<ProductEntity> search(String keyword) { return repo.searchByKeyword(keyword); }

    @Transactional
    public boolean deductStock(String id, int qty) {
        return repo.deductStock(id, qty) > 0;
    }
}
