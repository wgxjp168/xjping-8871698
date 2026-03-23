package com.huidong.physical.protocol.parser;

import ca.uhn.hl7v2.DefaultHapiContext;
import ca.uhn.hl7v2.HapiContext;
import ca.uhn.hl7v2.model.Message;
import ca.uhn.hl7v2.model.v25.message.ORU_R01;
import ca.uhn.hl7v2.model.v25.segment.MSH;
import ca.uhn.hl7v2.model.v25.segment.OBX;
import ca.uhn.hl7v2.model.v25.segment.PID;
import ca.uhn.hl7v2.parser.Parser;
import com.huidong.physical.common.exception.BusinessException;
import com.huidong.physical.common.result.ResultCode;
import com.huidong.physical.protocol.dto.HL7ParseResult;
import com.huidong.physical.protocol.dto.LabItemResult;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

import javax.annotation.PostConstruct;
import javax.annotation.PreDestroy;
import java.util.ArrayList;
import java.util.List;

/**
 * HL7 v2.5 检验报文解析器
 * 支持：迈瑞生化仪、万瑞血常规、万瑞糖化血红蛋白、优利特尿机
 */
@Slf4j
@Component
public class HL7MessageParser {

    private HapiContext hapiContext;
    private Parser parser;

    @PostConstruct
    public void init() {
        hapiContext = new DefaultHapiContext();
        parser = hapiContext.getPipeParser();
        log.info("HL7解析器初始化完成");
    }

    @PreDestroy
    public void destroy() throws Exception {
        if (hapiContext != null) {
            hapiContext.close();
        }
    }

    /**
     * 解析HL7 ORU^R01 检验结果报文
     *
     * @param hl7Message 原始HL7报文（管道符分隔格式）
     * @return 解析后的结构化结果
     */
    public HL7ParseResult parseOruR01(String hl7Message) {
        try {
            Message message = parser.parse(hl7Message);
            if (!(message instanceof ORU_R01)) {
                throw new BusinessException(ResultCode.HL7_PARSE_ERROR);
            }

            ORU_R01 oru = (ORU_R01) message;
            HL7ParseResult result = new HL7ParseResult();
            result.setRawMessage(hl7Message);

            // 解析 MSH - 消息头
            MSH msh = oru.getMSH();
            result.setSendingApp(msh.getMsh3_SendingApplication().getHd1_NamespaceID().getValue());
            result.setMessageDateTime(msh.getMsh7_DateTimeOfMessage().getTs1_Time().getValue());

            // 解析 PID - 患者标识
            PID pid = oru.getPATIENT_RESULT().getPATIENT().getPID();
            String patientId = pid.getPid3_PatientIdentifierList(0).getCx1_IDNumber().getValue();
            result.setPatientId(patientId);
            result.setPatientName(pid.getPid5_PatientName(0).getXpn1_FamilyName().getFn1_Surname().getValue());

            // 解析 OBX - 检验结果（多个）
            List<LabItemResult> items = new ArrayList<>();
            int obxCount = oru.getPATIENT_RESULT().getORDER_OBSERVATION().getOBSERVATIONReps();
            for (int i = 0; i < obxCount; i++) {
                OBX obx = oru.getPATIENT_RESULT().getORDER_OBSERVATION().getOBSERVATION(i).getOBX();
                LabItemResult item = parseObx(obx);
                if (item != null) {
                    items.add(item);
                }
            }
            result.setItems(items);
            log.debug("HL7报文解析成功: patientId={}, itemCount={}", patientId, items.size());
            return result;

        } catch (BusinessException e) {
            throw e;
        } catch (Exception e) {
            log.error("HL7报文解析异常: {}", e.getMessage());
            throw new BusinessException(ResultCode.HL7_PARSE_ERROR);
        }
    }

    private LabItemResult parseObx(OBX obx) {
        try {
            LabItemResult item = new LabItemResult();
            item.setItemCode(obx.getObx3_ObservationIdentifier().getCwe1_Identifier().getValue());
            item.setItemName(obx.getObx3_ObservationIdentifier().getCwe2_Text().getValue());
            item.setResultValue(obx.getObx5_ObservationValue(0).getData() != null
                    ? obx.getObx5_ObservationValue(0).getData().toString() : "");
            item.setUnit(obx.getObx6_Units().getCwe1_Identifier().getValue());
            item.setReferenceRange(obx.getObx7_ReferencesRange().getValue());
            item.setResultFlag(obx.getObx8_InterpretationCodes(0).getCwe1_Identifier().getValue());
            item.setObservationDateTime(obx.getObx14_DateTimeOfTheObservation().getTs1_Time().getValue());
            return item;
        } catch (Exception e) {
            log.warn("OBX段解析失败，跳过: {}", e.getMessage());
            return null;
        }
    }
}
