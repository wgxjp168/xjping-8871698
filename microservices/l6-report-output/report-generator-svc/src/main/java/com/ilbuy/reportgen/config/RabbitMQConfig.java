package com.ilbuy.reportgen.config;

import org.springframework.amqp.core.*;
import org.springframework.amqp.rabbit.config.SimpleRabbitListenerContainerFactory;
import org.springframework.amqp.rabbit.connection.ConnectionFactory;
import org.springframework.amqp.rabbit.core.RabbitTemplate;
import org.springframework.amqp.support.converter.Jackson2JsonMessageConverter;
import org.springframework.amqp.support.converter.MessageConverter;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
public class RabbitMQConfig {

    @Value("${rabbitmq.exchange.l5-report}")
    private String l5ReportExchange;

    @Value("${rabbitmq.exchange.l6-generator}")
    private String l6GeneratorExchange;

    @Value("${rabbitmq.queue.report-generate-request}")
    private String generateRequestQueue;

    @Value("${rabbitmq.queue.report-generate-dlq}")
    private String generateDlq;

    @Value("${rabbitmq.queue.report-generate-result}")
    private String generateResultQueue;

    @Bean
    public TopicExchange l5ReportExchange() {
        return ExchangeBuilder.topicExchange(l5ReportExchange).durable(true).build();
    }

    @Bean
    public TopicExchange l6GeneratorExchange() {
        return ExchangeBuilder.topicExchange(l6GeneratorExchange).durable(true).build();
    }

    @Bean
    public Queue generateRequestQueue() {
        return QueueBuilder.durable(generateRequestQueue)
                .withArgument("x-dead-letter-exchange", "")
                .withArgument("x-dead-letter-routing-key", generateDlq)
                .withArgument("x-message-ttl", 300000)
                .build();
    }

    @Bean
    public Queue generateDlq() {
        return QueueBuilder.durable(generateDlq).build();
    }

    @Bean
    public Queue generateResultQueue() {
        return QueueBuilder.durable(generateResultQueue).build();
    }

    @Bean
    public Binding generateRequestBinding() {
        return BindingBuilder.bind(generateRequestQueue())
                .to(l5ReportExchange())
                .with("report.generate.#");
    }

    @Bean
    public MessageConverter jsonMessageConverter() {
        return new Jackson2JsonMessageConverter();
    }

    @Bean
    public RabbitTemplate rabbitTemplate(ConnectionFactory connectionFactory) {
        RabbitTemplate template = new RabbitTemplate(connectionFactory);
        template.setMessageConverter(jsonMessageConverter());
        template.setMandatory(true);
        return template;
    }

    @Bean
    public SimpleRabbitListenerContainerFactory rabbitListenerContainerFactory(
            ConnectionFactory connectionFactory) {
        SimpleRabbitListenerContainerFactory factory = new SimpleRabbitListenerContainerFactory();
        factory.setConnectionFactory(connectionFactory);
        factory.setMessageConverter(jsonMessageConverter());
        factory.setAcknowledgeMode(AcknowledgeMode.MANUAL);
        factory.setPrefetchCount(5);
        return factory;
    }
}
