package com.ilbuy.notify.repository;

import com.ilbuy.notify.model.entity.Notification;
import com.ilbuy.notify.model.enums.NotificationStatus;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface NotificationRepository extends JpaRepository<Notification, Long> {

    Page<Notification> findByUserIdOrderByCreatedAtDesc(Long userId, Pageable pageable);

    long countByUserIdAndStatusNot(Long userId, NotificationStatus status);

    List<Notification> findByUserIdAndStatusNot(Long userId, NotificationStatus status);

    @Modifying
    @Query("UPDATE Notification n SET n.status = 'READ' WHERE n.userId = :userId AND n.status != 'READ'")
    int markAllReadByUserId(@Param("userId") Long userId);
}
