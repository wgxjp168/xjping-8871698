package com.ilbuy.datasvc.mq.config;

import org.springframework.amqp.core.*;
import org.springframework.amqp.rabbit.config.RetryInterceptorBuilder;
import org.springframework.amqp.rabbit.config.SimpleRabbitListenerContainerFactory;
import org.springframework.amqp.rabbit.connection.ConnectionFactory;
import org.springframework.amqp.rabbit.core.RabbitTemplate;
import org.springframework.amqp.rabbit.retry.RejectAndDontRequeueRecoverer;
import org.springframework.amqp.support.converter.Jackson2JsonMessageConverter;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.retry.interceptor.RetryOperationsInterceptor;

/**
 * RabbitMQ 拓扑配置
 *
 * Exchange: ilbuy.direct (Direct)
 * Queues:
 *   ilbuy.product.es          → ES 索引写入消费者
 *   ilbuy.product.analytics   → ClickHouse 分析写入消费者
 *   ilbuy.product.es.dlq      → ES 写入死信队列
 *   ilbuy.product.analytics.dlq
 *
 * 消息持久化 + 消费者 ACK 模式
 */
@Configuration
public class RabbitMQConfig {

    // ── Exchange ──────────────────────────────────────────────────────
    public static final String EXCHANGE = "ilbuy.direct";

    // ── Routing keys ──────────────────────────────────────────────────
    public static final String RK_ES         = "product.es";
    public static final String RK_ANALYTICS  = "product.analytics";
    public static final String RK_ES_DLQ     = "product.es.dlq";
    public static final String RK_ANALYTICS_DLQ = "product.analytics.dlq";

    // ── Queue names ───────────────────────────────────────────────────
    public static final String Q_ES          = "ilbuy.product.es";
    public static final String Q_ANALYTICS   = "ilbuy.product.analytics";
    public static final String Q_ES_DLQ      = "ilbuy.product.es.dlq";
    public static final String Q_ANALYTICS_DLQ = "ilbuy.product.analytics.dlq";

    @Bean
    DirectExchange ilbuyExchange() {
        return ExchangeBuilder.directExchange(EXCHANGE).durable(true).build();
    }

    // ── DLQ Exchange ──────────────────────────────────────────────────
    @Bean
    DirectExchange ilbuyDlqExchange() {
        return ExchangeBuilder.directExchange(EXCHANGE + ".dlq").durable(true).build();
    }

    // ── Queues (ES) ───────────────────────────────────────────────────
    @Bean
    Queue esQueue() {
        return QueueBuilder.durable(Q_ES)
            .withArgument("x-dead-letter-exchange", EXCHANGE + ".dlq")
            .withArgument("x-dead-letter-routing-key", RK_ES_DLQ)
            .withArgument("x-message-ttl", 86400000)  // 24h TTL
            .build();
    }

    @Bean
    Queue esDlqQueue() {
        return QueueBuilder.durable(Q_ES_DLQ).build();
    }

    @Bean
    Binding esBinding(Queue esQueue, DirectExchange ilbuyExchange) {
        return BindingBuilder.bind(esQueue).to(ilbuyExchange).with(RK_ES);
    }

    @Bean
    Binding esDlqBinding(Queue esDlqQueue, DirectExchange ilbuyDlqExchange) {
        return BindingBuilder.bind(esDlqQueue).to(ilbuyDlqExchange).with(RK_ES_DLQ);
    }

    // ── Queues (Analytics) ─────────────────────────────────────────────
    @Bean
    Queue analyticsQueue() {
        return QueueBuilder.durable(Q_ANALYTICS)
            .withArgument("x-dead-letter-exchange", EXCHANGE + ".dlq")
            .withArgument("x-dead-letter-routing-key", RK_ANALYTICS_DLQ)
            .withArgument("x-message-ttl", 86400000)
            .build();
    }

    @Bean
    Queue analyticsDlqQueue() {
        return QueueBuilder.durable(Q_ANALYTICS_DLQ).build();
    }

    @Bean
    Binding analyticsBinding(Queue analyticsQueue, DirectExchange ilbuyExchange) {
        return BindingBuilder.bind(analyticsQueue).to(ilbuyExchange).with(RK_ANALYTICS);
    }

    @Bean
    Binding analyticsDlqBinding(Queue analyticsDlqQueue, DirectExchange ilbuyDlqExchange) {
        return BindingBuilder.bind(analyticsDlqQueue).to(ilbuyDlqExchange).with(RK_ANALYTICS_DLQ);
    }

    // ── Message converter ──────────────────────────────────────────────
    @Bean
    Jackson2JsonMessageConverter jsonConverter() {
        return new Jackson2JsonMessageConverter();
    }

    @Bean
    RabbitTemplate rabbitTemplate(ConnectionFactory cf, Jackson2JsonMessageConverter converter) {
        RabbitTemplate tmpl = new RabbitTemplate(cf);
        tmpl.setMessageConverter(converter);
        tmpl.setMandatory(true);
        return tmpl;
    }

    // ── Listener container factory (explicit, overrides Spring Boot auto-config) ──
    /**
     * 明确配置 rabbitListenerContainerFactory：
     * - 使用 Jackson2JsonMessageConverter 反序列化 ProductIngestDTO
     * - 重试 3 次（2s → 4s → 8s），耗尽后由 RejectAndDontRequeueRecoverer
     *   拒绝消息并触发 x-dead-letter-exchange → DLQ
     */
    @Bean
    SimpleRabbitListenerContainerFactory rabbitListenerContainerFactory(
            ConnectionFactory connectionFactory,
            Jackson2JsonMessageConverter jsonConverter) {

        RetryOperationsInterceptor interceptor = RetryInterceptorBuilder.stateless()
            .maxAttempts(3)
            .backOffOptions(2000, 2.0, 10000)
            .recoverer(new RejectAndDontRequeueRecoverer())
            .build();

        SimpleRabbitListenerContainerFactory factory = new SimpleRabbitListenerContainerFactory();
        factory.setConnectionFactory(connectionFactory);
        factory.setMessageConverter(jsonConverter);
        factory.setAcknowledgeMode(AcknowledgeMode.AUTO);
        factory.setPrefetchCount(10);
        factory.setConcurrentConsumers(2);
        factory.setMaxConcurrentConsumers(8);
        factory.setAdviceChain(interceptor);
        return factory;
    }
}
