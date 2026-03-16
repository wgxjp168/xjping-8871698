package com.ilbuy.notify.repository;

import com.ilbuy.notify.model.entity.NotificationTemplate;
import com.ilbuy.notify.model.enums.NotificationChannel;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.Optional;

@Repository
public interface NotificationTemplateRepository extends JpaRepository<NotificationTemplate, Long> {

    Optional<NotificationTemplate> findByTemplateCode(String templateCode);

    Optional<NotificationTemplate> findByTemplateCodeAndChannel(String templateCode, NotificationChannel channel);
}
