package com.ilbuy.notify.config;

import org.springframework.amqp.core.*;
import org.springframework.amqp.rabbit.connection.ConnectionFactory;
import org.springframework.amqp.rabbit.core.RabbitTemplate;
import org.springframework.amqp.support.converter.Jackson2JsonMessageConverter;
import org.springframework.amqp.support.converter.MessageConverter;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
public class RabbitMQConfig {

    // Order exchange / queue
    @Value("${rabbitmq.order.exchange}")
    private String orderExchange;

    @Value("${rabbitmq.order.queue}")
    private String orderEventsQueue;

    // Report exchange / queue
    @Value("${rabbitmq.report.exchange}")
    private String reportExchange;

    @Value("${rabbitmq.report.queue}")
    private String reportReadyQueue;

    @Value("${rabbitmq.report.routing-key}")
    private String reportReadyRoutingKey;

    // ---- Order topology ----

    @Bean
    public TopicExchange orderExchangeBean() {
        return new TopicExchange(orderExchange, true, false);
    }

    @Bean
    public Queue orderEventsQueueBean() {
        return QueueBuilder.durable(orderEventsQueue).build();
    }

    @Bean
    public Binding orderEventsBinding(Queue orderEventsQueueBean, TopicExchange orderExchangeBean) {
        return BindingBuilder.bind(orderEventsQueueBean).to(orderExchangeBean).with("order.status.changed");
    }

    // ---- Report topology ----

    @Bean
    public TopicExchange reportExchangeBean() {
        return new TopicExchange(reportExchange, true, false);
    }

    @Bean
    public Queue reportReadyQueueBean() {
        return QueueBuilder.durable(reportReadyQueue).build();
    }

    @Bean
    public Binding reportReadyBinding(Queue reportReadyQueueBean, TopicExchange reportExchangeBean) {
        return BindingBuilder.bind(reportReadyQueueBean).to(reportExchangeBean).with(reportReadyRoutingKey);
    }

    // ---- Shared infrastructure ----

    @Bean
    public MessageConverter jsonMessageConverter() {
        return new Jackson2JsonMessageConverter();
    }

    @Bean
    public RabbitTemplate rabbitTemplate(ConnectionFactory connectionFactory) {
        RabbitTemplate template = new RabbitTemplate(connectionFactory);
        template.setMessageConverter(jsonMessageConverter());
        return template;
    }
}
