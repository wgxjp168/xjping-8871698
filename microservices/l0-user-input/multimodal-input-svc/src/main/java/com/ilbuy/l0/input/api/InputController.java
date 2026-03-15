package com.ilbuy.l0.input.api;

import com.ilbuy.common.core.result.Result;
import com.ilbuy.common.security.util.SecurityUtils;
import com.ilbuy.l0.input.domain.dto.InputRequest;
import com.ilbuy.l0.input.domain.dto.ParsedInput;
import com.ilbuy.l0.input.service.InputParserService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.security.SecurityRequirement;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.MediaType;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.*;

import java.util.List;

/**
 * 多模态输入解析 API
 *
 * <p>L0层对外暴露的核心接口，接收终端用户的四种输入模态，
 * 统一解析后向 L1 API 网关转发标准化结果。
 *
 * <p>与 L1 网关对接接口预留：
 * <ul>
 *   <li>L1 下行调用：L1 → GET /api/v0/input/profile/{userId} 获取用户画像辅助决策</li>
 *   <li>L1 上行接收：POST /api/v1/decision/start 接收 ParsedInput 启动决策流程</li>
 * </ul>
 *
 * @author ILbuy Team
 */
@Slf4j
@RestController
@RequestMapping("/api/v0/input")
@RequiredArgsConstructor
@Tag(name = "L0-多模态输入解析", description = "支持文本/图片/链接/语音四种输入模态解析")
@SecurityRequirement(name = "BearerAuth")
public class InputController {

    private final InputParserService inputParserService;

    /**
     * 单条输入解析
     *
     * <p>根据 inputType 自动选择对应解析器：
     * <ul>
     *   <li>text  → 文本语义解析（关键词提取 + 预算识别）</li>
     *   <li>image → 图像识别（标签提取）</li>
     *   <li>link  → 电商链接解析（7大平台，提取商品ID）</li>
     *   <li>voice → 语音转文本后语义解析</li>
     * </ul>
     */
    @PostMapping(value = "/parse", consumes = MediaType.APPLICATION_JSON_VALUE)
    @Operation(summary = "解析多模态输入", description = "根据inputType解析文本/图片/链接/语音输入")
    @PreAuthorize("isAuthenticated()")
    public Result<ParsedInput> parse(@Valid @RequestBody InputRequest request) {
        // 从JWT中注入userId（优先级高于请求体中的userId）
        Long userId = SecurityUtils.getCurrentUserId();
        request.setUserId(userId);

        log.info("[InputAPI] 收到解析请求: type={}, userId={}", request.getInputType(), userId);
        ParsedInput result = inputParserService.parse(request);
        return Result.success(result);
    }

    /**
     * 批量输入解析（最多10条）
     */
    @PostMapping(value = "/parse/batch", consumes = MediaType.APPLICATION_JSON_VALUE)
    @Operation(summary = "批量解析多模态输入", description = "最多支持10条并发解析")
    @PreAuthorize("isAuthenticated()")
    public Result<List<ParsedInput>> parseBatch(@Valid @RequestBody List<InputRequest> requests) {
        Long userId = SecurityUtils.getCurrentUserId();
        requests.forEach(r -> r.setUserId(userId));

        log.info("[InputAPI] 收到批量解析请求: count={}, userId={}", requests.size(), userId);
        List<ParsedInput> results = inputParserService.parseBatch(requests);
        return Result.success(results);
    }

    /**
     * 健康检查（对L1网关心跳探测使用）
     */
    @GetMapping("/health")
    @Operation(summary = "健康检查", description = "L1网关心跳探测接口，无需鉴权")
    public Result<String> health() {
        return Result.success("multimodal-input-svc:UP");
    }
}
