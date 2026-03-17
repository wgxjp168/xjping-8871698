package com.ilbuy.bmonetize.config;

import org.springframework.amqp.core.*;
import org.springframework.context.annotation.*;

@Configuration
public class RabbitConfig {
    public static final String EXCHANGE_PAYMENT = "ilbuy.payment";
    public static final String QUEUE_B_PAYMENT_SUCCESS = "b.monetize.payment.success";
    public static final String QUEUE_B_PAYMENT_FAILED  = "b.monetize.payment.failed";

    @Bean public Queue bPaySuccessQueue() { return QueueBuilder.durable(QUEUE_B_PAYMENT_SUCCESS).build(); }
    @Bean public Queue bPayFailedQueue()  { return QueueBuilder.durable(QUEUE_B_PAYMENT_FAILED).build(); }

    @Bean public Binding bindBSuccess(Queue bPaySuccessQueue) {
        return BindingBuilder.bind(bPaySuccessQueue).to(new TopicExchange(EXCHANGE_PAYMENT)).with("payment.success.b_#");
    }

    @Bean public Binding bindBFailed(Queue bPayFailedQueue) {
        return BindingBuilder.bind(bPayFailedQueue).to(new TopicExchange(EXCHANGE_PAYMENT)).with("payment.failed.b_#");
    }
}
