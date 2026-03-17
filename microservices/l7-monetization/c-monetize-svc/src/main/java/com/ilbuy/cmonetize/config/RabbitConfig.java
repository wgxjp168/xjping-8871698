package com.ilbuy.cmonetize.config;

import org.springframework.amqp.core.*;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
public class RabbitConfig {
    public static final String EXCHANGE_PAYMENT = "ilbuy.payment";
    public static final String QUEUE_C_PAYMENT_SUCCESS = "c.monetize.payment.success";
    public static final String QUEUE_C_PAYMENT_FAILED  = "c.monetize.payment.failed";
    public static final String QUEUE_C_REFUND_SUCCESS  = "c.monetize.refund.success";

    @Bean public Queue cPaymentSuccessQueue() { return QueueBuilder.durable(QUEUE_C_PAYMENT_SUCCESS).build(); }
    @Bean public Queue cPaymentFailedQueue()  { return QueueBuilder.durable(QUEUE_C_PAYMENT_FAILED).build(); }
    @Bean public Queue cRefundSuccessQueue()  { return QueueBuilder.durable(QUEUE_C_REFUND_SUCCESS).build(); }

    @Bean
    public Binding bindCPaySuccess(Queue cPaymentSuccessQueue) {
        return BindingBuilder.bind(cPaymentSuccessQueue)
            .to(new TopicExchange(EXCHANGE_PAYMENT)).with("payment.success.c_#");
    }
    @Bean
    public Binding bindCPayFailed(Queue cPaymentFailedQueue) {
        return BindingBuilder.bind(cPaymentFailedQueue)
            .to(new TopicExchange(EXCHANGE_PAYMENT)).with("payment.failed.c_#");
    }
    @Bean
    public Binding bindCRefund(Queue cRefundSuccessQueue) {
        return BindingBuilder.bind(cRefundSuccessQueue)
            .to(new TopicExchange(EXCHANGE_PAYMENT)).with("refund.success.c_#");
    }
}
