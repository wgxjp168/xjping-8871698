package com.ilbuy.data.repository;

import com.ilbuy.data.entity.ProductEntity;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface ProductRepository extends JpaRepository<ProductEntity, String> {

    List<ProductEntity> findByCategory(String category);

    List<ProductEntity> findByStatus(String status);

    List<ProductEntity> findByCategoryAndStatus(String category, String status);

    List<ProductEntity> findByPriceBetween(double minPrice, double maxPrice);

    @Query("SELECT p FROM ProductEntity p WHERE p.name LIKE %:keyword% OR p.description LIKE %:keyword%")
    List<ProductEntity> searchByKeyword(@Param("keyword") String keyword);

    @Modifying
    @Query("UPDATE ProductEntity p SET p.stock = p.stock - :qty WHERE p.id = :id AND p.stock >= :qty")
    int deductStock(@Param("id") String id, @Param("qty") int qty);
}
