package com.ilbuy.flink.source;

import com.fasterxml.jackson.databind.DeserializationFeature;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule;
import com.ilbuy.flink.model.ProductEvent;
import com.rabbitmq.client.*;
import lombok.extern.slf4j.Slf4j;
import org.apache.flink.streaming.api.functions.source.RichSourceFunction;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.LinkedBlockingQueue;
import java.util.concurrent.TimeUnit;

/**
 * Flink RabbitMQ Source
 *
 * 消费 ilbuy.product.analytics 队列，
 * 将 JSON 消息反序列化为 ProductEvent 并推入 Flink 流
 */
@Slf4j
public class RabbitMQProductSource extends RichSourceFunction<ProductEvent> {

    private static final long serialVersionUID = 1L;

    private final String host;
    private final int    port;
    private final String username;
    private final String password;

    private static final String QUEUE   = "ilbuy.product.analytics";
    private static final int    TIMEOUT = 5000;

    private volatile boolean running = true;
    private transient Connection connection;
    private transient Channel    channel;
    private transient LinkedBlockingQueue<ProductEvent> buffer;

    private static final ObjectMapper mapper = new ObjectMapper()
        .registerModule(new JavaTimeModule())
        .disable(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES);

    public RabbitMQProductSource(String host, int port, String username, String password) {
        this.host = host;
        this.port = port;
        this.username = username;
        this.password = password;
    }

    @Override
    public void open(org.apache.flink.configuration.Configuration parameters) throws Exception {
        buffer = new LinkedBlockingQueue<>(10_000);

        ConnectionFactory factory = new ConnectionFactory();
        factory.setHost(host);
        factory.setPort(port);
        factory.setUsername(username);
        factory.setPassword(password);
        factory.setAutomaticRecoveryEnabled(true);

        connection = factory.newConnection("flink-source");
        channel    = connection.createChannel();
        channel.basicQos(100);   // prefetch

        channel.basicConsume(QUEUE, false, new DefaultConsumer(channel) {
            @Override
            public void handleDelivery(String consumerTag, Envelope envelope,
                                       AMQP.BasicProperties properties, byte[] body) throws IOException {
                try {
                    String json = new String(body, StandardCharsets.UTF_8);
                    ProductEvent event = mapper.readValue(json, ProductEvent.class);
                    buffer.offer(event);
                    channel.basicAck(envelope.getDeliveryTag(), false);
                } catch (Exception e) {
                    log.error("Failed to parse message: {}", e.getMessage());
                    channel.basicNack(envelope.getDeliveryTag(), false, true);
                }
            }
        });

        log.info("RabbitMQ source started: {}:{} queue={}", host, port, QUEUE);
    }

    @Override
    public void run(SourceContext<ProductEvent> ctx) throws Exception {
        while (running) {
            ProductEvent event = buffer.poll(TIMEOUT, TimeUnit.MILLISECONDS);
            if (event != null) {
                event.setProcessedAt(System.currentTimeMillis());
                synchronized (ctx.getCheckpointLock()) {
                    ctx.collect(event);
                }
            }
        }
    }

    @Override
    public void cancel() {
        running = false;
        try {
            if (channel != null) channel.close();
            if (connection != null) connection.close();
        } catch (Exception e) {
            log.warn("Close error: {}", e.getMessage());
        }
    }
}
