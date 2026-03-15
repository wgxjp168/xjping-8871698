package com.ilbuy.l0.input.service;

import com.ilbuy.l0.input.domain.dto.InputRequest;
import com.ilbuy.l0.input.domain.dto.ParsedInput;

import java.util.List;

/**
 * 输入解析编排服务接口
 *
 * <p>统一入口，根据 inputType 分发到对应的解析器（策略模式），
 * 并整合用户画像信息（budgetRange/场景偏好）对解析结果进行增强。
 *
 * @author ILbuy Team
 */
public interface InputParserService {

    /**
     * 解析单个多模态输入
     *
     * @param request 输入请求（含 inputType + 对应内容字段）
     * @return 标准化解析结果
     */
    ParsedInput parse(InputRequest request);

    /**
     * 批量解析（最多10条）
     *
     * @param requests 输入请求列表
     * @return 按顺序对应的解析结果列表
     */
    List<ParsedInput> parseBatch(List<InputRequest> requests);
}
