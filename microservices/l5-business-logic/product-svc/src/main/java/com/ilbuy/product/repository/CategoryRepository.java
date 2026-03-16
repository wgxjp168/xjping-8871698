package com.ilbuy.product.repository;

import com.ilbuy.product.model.entity.Category;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface CategoryRepository extends JpaRepository<Category, Long> {

    /** Returns all enabled root categories (parentId IS NULL). */
    List<Category> findByParentIdIsNullAndEnabledTrueOrderBySortOrderAsc();

    /** Returns all enabled children of a given parent. */
    List<Category> findByParentIdAndEnabledTrueOrderBySortOrderAsc(Long parentId);

    /** Returns all enabled categories (used to build the full tree in memory). */
    List<Category> findByEnabledTrueOrderBySortOrderAsc();
}
