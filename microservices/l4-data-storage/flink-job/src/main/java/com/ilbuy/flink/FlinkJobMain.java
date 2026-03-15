package com.ilbuy.flink;

import com.ilbuy.flink.model.ProductEvent;
import com.ilbuy.flink.sink.ClickHouseSink;
import com.ilbuy.flink.source.RabbitMQProductSource;
import com.ilbuy.flink.transform.ProductEnrichTransform;
import org.apache.flink.streaming.api.datastream.DataStream;
import org.apache.flink.streaming.api.environment.StreamExecutionEnvironment;

/**
 * ILbuy Flink 实时流处理作业
 *
 * 数据流：
 *   RabbitMQ(ilbuy.product.analytics) → 反序列化 ProductEvent
 *   → ProductEnrichTransform (计算分位数评分/时间窗口聚合)
 *   → ClickHouseSink (批量写入分析宽表)
 *
 * 运行方式：
 *   flink run -c com.ilbuy.flink.FlinkJobMain flink-job-1.0.0-uber.jar \
 *     --rabbitmq-host rabbitmq --rabbitmq-port 5672 \
 *     --clickhouse-url jdbc:clickhouse://clickhouse:8123/ilbuy_analytics
 */
public class FlinkJobMain {

    public static void main(String[] args) throws Exception {
        // ── 解析命令行参数 ──────────────────────────────────────────
        org.apache.flink.api.java.utils.ParameterTool params =
            org.apache.flink.api.java.utils.ParameterTool.fromArgs(args);

        String rmqHost      = params.get("rabbitmq-host", "localhost");
        int    rmqPort      = params.getInt("rabbitmq-port", 5672);
        String rmqUser      = params.get("rabbitmq-user", "guest");
        String rmqPass      = params.get("rabbitmq-pass", "guest");
        String clickhouseUrl = params.get("clickhouse-url",
            "jdbc:clickhouse://localhost:8123/ilbuy_analytics");
        String clickhouseUser = params.get("clickhouse-user", "default");
        String clickhousePass = params.get("clickhouse-pass", "");

        // ── Flink 执行环境 ─────────────────────────────────────────
        StreamExecutionEnvironment env = StreamExecutionEnvironment.getExecutionEnvironment();
        env.setParallelism(params.getInt("parallelism", 2));
        env.enableCheckpointing(30_000);   // 30s checkpoint
        env.getConfig().setGlobalJobParameters(params);

        // ── Source: RabbitMQ ────────────────────────────────────────
        DataStream<ProductEvent> productStream = env.addSource(
            new RabbitMQProductSource(rmqHost, rmqPort, rmqUser, rmqPass),
            "RabbitMQ-ProductSource"
        );

        // ── Transform: 流式富化 ─────────────────────────────────────
        DataStream<ProductEvent> enriched = productStream
            .map(new ProductEnrichTransform())
            .name("ProductEnrichTransform");

        // ── Sink: ClickHouse ────────────────────────────────────────
        enriched.addSink(
            new ClickHouseSink(clickhouseUrl, clickhouseUser, clickhousePass)
        ).name("ClickHouse-Sink");

        env.execute("ILbuy-Product-Analytics-Stream");
    }
}
