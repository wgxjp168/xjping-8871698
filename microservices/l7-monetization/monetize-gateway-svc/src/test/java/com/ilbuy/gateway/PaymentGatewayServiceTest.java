package com.ilbuy.gateway;

import com.ilbuy.gateway.domain.PaymentOrder;
import com.ilbuy.gateway.domain.PaymentOrder.*;
import com.ilbuy.gateway.dto.CreatePaymentRequest;
import com.ilbuy.gateway.dto.PaymentResponse;
import com.ilbuy.gateway.repository.PaymentOrderRepository;
import com.ilbuy.gateway.repository.RefundRecordRepository;
import com.ilbuy.gateway.service.*;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.*;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.amqp.rabbit.core.RabbitTemplate;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.data.redis.core.ValueOperations;
import java.math.BigDecimal;
import java.util.Map;
import java.util.Optional;
import static org.assertj.core.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
class PaymentGatewayServiceTest {

    @Mock PaymentOrderRepository paymentOrderRepository;
    @Mock RefundRecordRepository refundRecordRepository;
    @Mock WechatPayGateway wechatPayGateway;
    @Mock AlipayGateway alipayGateway;
    @Mock UnionPayGateway unionPayGateway;
    @Mock RabbitTemplate rabbitTemplate;
    @Mock StringRedisTemplate redisTemplate;
    @Mock ValueOperations<String, String> valueOps;

    @InjectMocks
    PaymentGatewayServiceImpl paymentService;

    @BeforeEach
    void setup() {
        when(redisTemplate.opsForValue()).thenReturn(valueOps);
        when(redisTemplate.hasKey(anyString())).thenReturn(false);
    }

    @Test
    void createPayment_wechat_success() {
        // Arrange
        CreatePaymentRequest req = new CreatePaymentRequest();
        req.setBizOrderNo("BIZ-001");
        req.setUserId(100L);
        req.setAmount(new BigDecimal("99.00"));
        req.setChannel(PaymentChannel.WECHAT);
        req.setBizType(BizType.C_SINGLE);
        req.setSubject("单次报告付费");
        req.setChannelUserId("openid_test");

        when(paymentOrderRepository.save(any())).thenAnswer(inv -> inv.getArgument(0));
        when(wechatPayGateway.unifiedOrder(any(), anyString()))
            .thenReturn(Map.of("prepay_id", "wx_test_123", "signType", "RSA"));

        // Act
        PaymentResponse resp = paymentService.createPayment(req);

        // Assert
        assertThat(resp.getBizOrderNo()).isEqualTo("BIZ-001");
        assertThat(resp.getAmount()).isEqualByComparingTo("99.00");
        assertThat(resp.getStatus()).isEqualTo(PaymentStatus.PAYING);
        assertThat(resp.getChannelPayParams()).isNotNull();
        verify(paymentOrderRepository, times(2)).save(any());
    }

    @Test
    void createPayment_idempotent_returns_existing() {
        when(redisTemplate.hasKey(anyString())).thenReturn(true);
        PaymentOrder existing = PaymentOrder.builder()
            .paymentNo("PAY-EXIST").bizOrderNo("BIZ-001")
            .userId(100L).amount(new BigDecimal("99.00"))
            .channel(PaymentChannel.WECHAT).bizType(BizType.C_SINGLE)
            .status(PaymentStatus.PAYING).build();
        when(paymentOrderRepository.findByBizOrderNo("BIZ-001")).thenReturn(Optional.of(existing));

        CreatePaymentRequest req = new CreatePaymentRequest();
        req.setBizOrderNo("BIZ-001");
        req.setUserId(100L);
        req.setAmount(new BigDecimal("99.00"));
        req.setChannel(PaymentChannel.WECHAT);
        req.setBizType(BizType.C_SINGLE);
        req.setSubject("test");

        PaymentResponse resp = paymentService.createPayment(req);
        assertThat(resp.getPaymentNo()).isEqualTo("PAY-EXIST");
        verify(paymentOrderRepository, never()).save(any());
    }

    @Test
    void handleCallback_wechat_success_publishes_event() {
        // WeChat Pay V3: signature already verified in CallbackController before handleCallback is called.
        // handleCallback receives pre-verified, decrypted params — no verifySignature call inside.
        PaymentOrder order = PaymentOrder.builder()
            .paymentNo("PAY-001").bizOrderNo("BIZ-001")
            .amount(new BigDecimal("99.00"))
            .channel(PaymentChannel.WECHAT).bizType(BizType.C_SINGLE)
            .status(PaymentStatus.PAYING).build();
        when(paymentOrderRepository.findByBizOrderNo("BIZ-001")).thenReturn(Optional.of(order));
        when(paymentOrderRepository.save(any())).thenAnswer(inv -> inv.getArgument(0));

        // V3 notification maps trade_state (not result_code)
        Map<String, String> params = Map.of(
            "transaction_id", "wx_txn_001",
            "out_trade_no",   "BIZ-001",
            "trade_state",    "SUCCESS",
            "result_code",    "SUCCESS"
        );
        String result = paymentService.handleCallback("WECHAT", params, "{}");
        assertThat(result).isEqualTo("SUCCESS");
        assertThat(order.getStatus()).isEqualTo(PaymentStatus.SUCCESS);
        verify(rabbitTemplate).convertAndSend(anyString(), contains("payment.success"), anyMap());
        // verifySignature is NOT called for WECHAT — verification done upstream in CallbackController
        verify(wechatPayGateway, never()).verifySignature(anyMap());
    }

    @Test
    void queryPayment_notFound_throws() {
        when(paymentOrderRepository.findByPaymentNo("PAY-NOTEXIST")).thenReturn(Optional.empty());
        assertThatThrownBy(() -> paymentService.queryPayment("PAY-NOTEXIST"))
            .isInstanceOf(IllegalArgumentException.class);
    }
}
