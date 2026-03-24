package com.health.physical.protocol.impl;

import com.health.physical.protocol.dto.UrineDataPacket;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * 优利特尿机协议解析器单元测试
 */
class UritUrineProtocolParserTest {

    private UritUrineProtocolParser parser;

    private static final String SAMPLE_MESSAGE =
            "H|\\^&|||Urit-500B|||||||P|1|20240315120000\n" +
            "P|1||BARCODE001\n" +
            "O|1|BARCODE001||^^^LEU\\^^^NIT\\^^^PRO\\^^^GLU|R||||||||||||\n" +
            "R|1|^^^LEU|2+|neg/±/1+/2+/3+|||N|||F|||20240315120000\n" +
            "R|2|^^^NIT|neg|||||||F|||20240315120000\n" +
            "R|3|^^^PRO|1+|||||||F|||20240315120000\n" +
            "R|4|^^^GLU|neg|||||||F|||20240315120000\n" +
            "R|5|^^^KET|neg|||||||F|||20240315120000\n" +
            "R|6|^^^BIL|neg|||||||F|||20240315120000\n" +
            "R|7|^^^URO|neg|||||||F|||20240315120000\n" +
            "R|8|^^^ERY|neg|||||||F|||20240315120000\n" +
            "R|9|^^^BLD|neg|||||||F|||20240315120000\n" +
            "R|10|^^^SG|1.015|||||||F|||20240315120000\n" +
            "R|11|^^^PH|6.5|||||||F|||20240315120000\n" +
            "L|1|N\n";

    @BeforeEach
    void setUp() {
        parser = new UritUrineProtocolParser();
    }

    @Test
    void supports_uritMessage_returnsTrue() {
        assertThat(parser.supports(SAMPLE_MESSAGE)).isTrue();
    }

    @Test
    void supports_nonUritMessage_returnsFalse() {
        assertThat(parser.supports("H|\\^&|||BS-380|||||||P|1|20240315120000")).isFalse();
    }

    @Test
    void parse_validMessage_extractsBarcode() {
        UrineDataPacket packet = parser.parse(SAMPLE_MESSAGE);
        assertThat(packet.isParseSuccess()).isTrue();
        assertThat(packet.getBarcode()).isEqualTo("BARCODE001");
    }

    @Test
    void parse_validMessage_extractsDeviceSn() {
        UrineDataPacket packet = parser.parse(SAMPLE_MESSAGE);
        assertThat(packet.getDeviceSn()).isEqualTo("Urit-500B");
    }

    @Test
    void parse_validMessage_extractsResults() {
        UrineDataPacket packet = parser.parse(SAMPLE_MESSAGE);
        assertThat(packet.getLeu()).isEqualTo("2+");
        assertThat(packet.getNit()).isEqualTo("neg");
        assertThat(packet.getPro()).isEqualTo("1+");
        assertThat(packet.getGlu()).isEqualTo("neg");
        assertThat(packet.getSpecificGravity()).isEqualTo("1.015");
        assertThat(packet.getPh()).isEqualTo("6.5");
    }

    @Test
    void parse_nullMessage_returnsErrorPacket() {
        UrineDataPacket packet = parser.parse(null);
        assertThat(packet.isParseSuccess()).isFalse();
        assertThat(packet.getParseError()).isNotBlank();
    }

    @Test
    void parse_emptyMessage_returnsErrorPacket() {
        UrineDataPacket packet = parser.parse("   ");
        assertThat(packet.isParseSuccess()).isFalse();
    }
}
