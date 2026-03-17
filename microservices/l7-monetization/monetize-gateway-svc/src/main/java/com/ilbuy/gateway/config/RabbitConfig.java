package com.ilbuy.gateway.config;

import org.springframework.amqp.core.*;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
public class RabbitConfig {

    public static final String EXCHANGE_PAYMENT = "ilbuy.payment";
    public static final String QUEUE_PAYMENT_SUCCESS = "payment.success";
    public static final String QUEUE_PAYMENT_FAILED  = "payment.failed";
    public static final String QUEUE_REFUND_SUCCESS  = "refund.success";

    @Bean
    public TopicExchange paymentExchange() {
        return new TopicExchange(EXCHANGE_PAYMENT, true, false);
    }

    @Bean
    public Queue paymentSuccessQueue() { return QueueBuilder.durable(QUEUE_PAYMENT_SUCCESS).build(); }

    @Bean
    public Queue paymentFailedQueue() { return QueueBuilder.durable(QUEUE_PAYMENT_FAILED).build(); }

    @Bean
    public Queue refundSuccessQueue() { return QueueBuilder.durable(QUEUE_REFUND_SUCCESS).build(); }

    @Bean
    public Binding bindSuccess(Queue paymentSuccessQueue, TopicExchange paymentExchange) {
        return BindingBuilder.bind(paymentSuccessQueue).to(paymentExchange).with("payment.success.#");
    }

    @Bean
    public Binding bindFailed(Queue paymentFailedQueue, TopicExchange paymentExchange) {
        return BindingBuilder.bind(paymentFailedQueue).to(paymentExchange).with("payment.failed.#");
    }

    @Bean
    public Binding bindRefund(Queue refundSuccessQueue, TopicExchange paymentExchange) {
        return BindingBuilder.bind(refundSuccessQueue).to(paymentExchange).with("refund.success.#");
    }
}
