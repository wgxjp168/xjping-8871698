-- Lua 脚本：根据 K8s namespace 自动注入 ilbuy_layer 标签
function add_ilbuy_layer(tag, timestamp, record)
    local ns = ""
    if record["kubernetes"] and record["kubernetes"]["namespace_name"] then
        ns = record["kubernetes"]["namespace_name"]
    end

    local layer_map = {
        ["ilbuy-l1"] = "L1-user-profile",
        ["ilbuy-l2"] = "L2-ai-decision",
        ["ilbuy-l3"] = "L3-data-process",
        ["ilbuy-l4"] = "L4-data-storage",
        ["ilbuy-l5"] = "L5-report-generation",
        ["ilbuy-l6"] = "L6-delivery",
        ["ilbuy-l7"] = "L7-monetization",
        ["ilbuy-l8"] = "L8-feedback-optimize",
        ["ilbuy-ops"] = "L9-ops",
        ["ilbuy-infra"] = "infrastructure",
    }

    local layer = layer_map[ns]
    if layer then
        record["ilbuy_layer"] = layer
    else
        record["ilbuy_layer"] = "unknown"
    end

    -- 标准化日志级别
    local level = record["level"] or record["log_level"] or record["severity"] or ""
    record["log_level_normalized"] = string.upper(level)

    -- 标记错误日志
    if level == "ERROR" or level == "CRITICAL" or level == "error" or level == "critical" then
        record["is_error"] = true
    end

    return 1, timestamp, record
end
