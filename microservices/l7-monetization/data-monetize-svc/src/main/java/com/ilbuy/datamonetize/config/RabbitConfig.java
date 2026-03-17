package com.ilbuy.datamonetize.config;

import org.springframework.amqp.core.*;
import org.springframework.context.annotation.*;

@Configuration
public class RabbitConfig {
    public static final String EXCHANGE_PAYMENT = "ilbuy.payment";
    public static final String QUEUE_DATA_PAYMENT_SUCCESS = "payment.success.data";
    public static final String QUEUE_DATA_PAYMENT_FAILED  = "payment.failed.data";

    @Bean
    public Queue dataPaySuccessQueue() {
        return QueueBuilder.durable(QUEUE_DATA_PAYMENT_SUCCESS).build();
    }

    @Bean
    public Queue dataPayFailedQueue() {
        return QueueBuilder.durable(QUEUE_DATA_PAYMENT_FAILED).build();
    }

    @Bean
    public Binding bindDataSuccess(Queue dataPaySuccessQueue) {
        return BindingBuilder.bind(dataPaySuccessQueue)
            .to(new TopicExchange(EXCHANGE_PAYMENT))
            .with("payment.success.data_#");
    }

    @Bean
    public Binding bindDataFailed(Queue dataPayFailedQueue) {
        return BindingBuilder.bind(dataPayFailedQueue)
            .to(new TopicExchange(EXCHANGE_PAYMENT))
            .with("payment.failed.data_#");
    }
}
