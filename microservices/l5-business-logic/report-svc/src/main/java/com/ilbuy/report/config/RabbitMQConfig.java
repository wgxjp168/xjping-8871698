package com.ilbuy.report.config;

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

    @Value("${rabbitmq.report.exchange}")
    private String exchange;

    @Value("${rabbitmq.report.queue}")
    private String queue;

    @Value("${rabbitmq.report.routing-key}")
    private String routingKey;

    @Bean
    public TopicExchange reportExchange() {
        return new TopicExchange(exchange, true, false);
    }

    @Bean
    public Queue reportGenerateQueue() {
        return QueueBuilder.durable(queue).build();
    }

    @Bean
    public Binding reportGenerateBinding(Queue reportGenerateQueue, TopicExchange reportExchange) {
        return BindingBuilder.bind(reportGenerateQueue).to(reportExchange).with(routingKey);
    }

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
