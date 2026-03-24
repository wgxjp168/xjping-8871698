package com.health.physical.protocol.impl;

import com.health.physical.protocol.dto.LabDataItem;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * ASTM HL7 生化仪协议解析器单元测试
 */
class Hl7AstmLabProtocolParserTest {

    private Hl7AstmLabProtocolParser parser;

    private static final String SAMPLE_BIOCHEM =
            "H|\\^&|||BS-380|||||||P|1|20240315120000\n" +
            "P|1||BARCODE002\n" +
            "O|1|BARCODE002||^^^GLU\\^^^CHOL\\^^^TG|R||||||||||||\n" +
            "R|1|^^^GLU|5.3|mmol/L|3.9^6.1|N|||F|||20240315120000\n" +
            "R|2|^^^CHOL|6.8|mmol/L|3.1^5.7|H|||F|||20240315120000\n" +
            "R|3|^^^TG|0.9|mmol/L|0.4^1.7|N|||F|||20240315120000\n" +
            "L|1|N\n";

    @BeforeEach
    void setUp() {
        parser = new Hl7AstmLabProtocolParser();
    }

    @Test
    void supports_astmMessage_returnsTrue() {
        assertThat(parser.supports(SAMPLE_BIOCHEM)).isTrue();
    }

    @Test
    void supports_uritMessage_returnsFalse() {
        assertThat(parser.supports("H|\\^&|||Urit-500B|||||||P|1|20240315")).isFalse();
    }

    @Test
    void parse_validMessage_extractsBarcode() {
        LabDataItem item = parser.parse(SAMPLE_BIOCHEM);
        assertThat(item.isParseSuccess()).isTrue();
        assertThat(item.getBarcode()).isEqualTo("BARCODE002");
    }

    @Test
    void parse_validMessage_extractsDeviceModel() {
        LabDataItem item = parser.parse(SAMPLE_BIOCHEM);
        assertThat(item.getDeviceModel()).isEqualTo("BS-380");
    }

    @Test
    void parse_validMessage_extractsThreeResults() {
        LabDataItem item = parser.parse(SAMPLE_BIOCHEM);
        assertThat(item.getResults()).hasSize(3);
    }

    @Test
    void parse_validMessage_extractsGluResult() {
        LabDataItem item = parser.parse(SAMPLE_BIOCHEM);
        LabDataItem.ResultItem glu = item.getResults().stream()
                .filter(r -> "GLU".equals(r.getItemCode()))
                .findFirst().orElse(null);
        assertThat(glu).isNotNull();
        assertThat(glu.getResultValue()).isEqualTo("5.3");
        assertThat(glu.getUnit()).isEqualTo("mmol/L");
        assertThat(glu.getAbnormalFlag()).isEqualTo("N");
    }

    @Test
    void parse_highValue_flaggedAsH() {
        LabDataItem item = parser.parse(SAMPLE_BIOCHEM);
        LabDataItem.ResultItem chol = item.getResults().stream()
                .filter(r -> "CHOL".equals(r.getItemCode()))
                .findFirst().orElse(null);
        assertThat(chol).isNotNull();
        assertThat(chol.getAbnormalFlag()).isEqualTo("H");
    }

    @Test
    void parse_nullMessage_returnsError() {
        LabDataItem item = parser.parse(null);
        assertThat(item.isParseSuccess()).isFalse();
    }
}
