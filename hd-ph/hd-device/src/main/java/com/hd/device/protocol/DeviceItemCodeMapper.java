package com.hd.device.protocol;

import org.springframework.stereotype.Component;

import java.util.HashMap;
import java.util.Map;

/**
 * 检验设备项目编码映射器
 * 将各厂商设备的原始项目编码映射为公卫系统标准编码
 *
 * 覆盖设备：
 *   优利特 URIT-330/560 (尿常规)
 *   聚创 JCH-S480/BT-400L、迈瑞 BS330、万瑞 BS830 (生化)
 *   优利特 BH-5380CRP、聚创 BT-400L、迈瑞 BC2600/BC-760CS、理邦 DS-580i (血常规)
 *   雷诺华 LD-600 (糖化血红蛋白)
 */
@Component
public class DeviceItemCodeMapper {

    public static class ItemMapping {
        public final String standardCode;
        public final String standardName;
        public final String category; // BLOOD / BIOCHEM / URINE / HBA1C

        public ItemMapping(String standardCode, String standardName, String category) {
            this.standardCode = standardCode;
            this.standardName = standardName;
            this.category = category;
        }
    }

    private static final Map<String, ItemMapping> CODE_MAP = new HashMap<>();

    static {
        // ===================== 血常规 BLOOD (优利特/聚创/迈瑞/理邦) =====================
        add("WBC",     "XCR001", "白细胞计数",         "BLOOD");
        add("RBC",     "XCR002", "红细胞计数",         "BLOOD");
        add("HGB",     "XCR003", "血红蛋白",           "BLOOD");
        add("HCT",     "XCR004", "红细胞压积",         "BLOOD");
        add("MCV",     "XCR005", "平均红细胞体积",     "BLOOD");
        add("MCH",     "XCR006", "平均血红蛋白量",     "BLOOD");
        add("MCHC",    "XCR007", "平均血红蛋白浓度",   "BLOOD");
        add("PLT",     "XCR008", "血小板计数",         "BLOOD");
        add("NEUT%",   "XCR009", "中性粒细胞百分比",   "BLOOD");
        add("LYMPH%",  "XCR010", "淋巴细胞百分比",     "BLOOD");
        add("MONO%",   "XCR011", "单核细胞百分比",     "BLOOD");
        add("EO%",     "XCR012", "嗜酸性粒细胞百分比", "BLOOD");
        add("BASO%",   "XCR013", "嗜碱性粒细胞百分比", "BLOOD");
        add("NEUT#",   "XCR014", "中性粒细胞绝对值",   "BLOOD");
        add("LYMPH#",  "XCR015", "淋巴细胞绝对值",     "BLOOD");
        add("MONO#",   "XCR016", "单核细胞绝对值",     "BLOOD");
        add("EO#",     "XCR017", "嗜酸粒细胞绝对值",   "BLOOD");
        add("BASO#",   "XCR018", "嗜碱粒细胞绝对值",   "BLOOD");
        add("RDW-CV",  "XCR019", "红细胞分布宽度CV",   "BLOOD");
        add("RDW-SD",  "XCR020", "红细胞分布宽度SD",   "BLOOD");
        add("PDW",     "XCR021", "血小板分布宽度",     "BLOOD");
        add("MPV",     "XCR022", "平均血小板体积",     "BLOOD");
        add("PCT",     "XCR023", "血小板压积",         "BLOOD");
        add("CRP",     "XCR024", "C反应蛋白",          "BLOOD");
        // 迈瑞BC-760CS五分类别名
        add("GRAN%",   "XCR009", "中性粒细胞百分比",   "BLOOD");
        add("GRAN#",   "XCR014", "中性粒细胞绝对值",   "BLOOD");
        add("MID%",    "XCR011", "中间细胞百分比",     "BLOOD");
        add("MID#",    "XCR016", "中间细胞绝对值",     "BLOOD");

        // ===================== 生化 BIOCHEM (聚创/迈瑞/万瑞) =====================
        add("ALT",     "SH001",  "丙氨酸氨基转移酶",   "BIOCHEM");
        add("AST",     "SH002",  "天冬氨酸氨基转移酶", "BIOCHEM");
        add("ALP",     "SH003",  "碱性磷酸酶",         "BIOCHEM");
        add("GGT",     "SH004",  "γ-谷氨酰转肽酶",     "BIOCHEM");
        add("TP",      "SH005",  "总蛋白",             "BIOCHEM");
        add("ALB",     "SH006",  "白蛋白",             "BIOCHEM");
        add("GLO",     "SH007",  "球蛋白",             "BIOCHEM");
        add("AG",      "SH007a", "白球比值",           "BIOCHEM");
        add("TBIL",    "SH008",  "总胆红素",           "BIOCHEM");
        add("DBIL",    "SH009",  "直接胆红素",         "BIOCHEM");
        add("IBIL",    "SH010",  "间接胆红素",         "BIOCHEM");
        add("BUN",     "SH011",  "尿素氮",             "BIOCHEM");
        add("CREA",    "SH012",  "肌酐",               "BIOCHEM");
        add("UA",      "SH013",  "尿酸",               "BIOCHEM");
        add("GLU",     "SH014",  "葡萄糖（血糖）",     "BIOCHEM");
        add("TG",      "SH015",  "甘油三酯",           "BIOCHEM");
        add("TC",      "SH016",  "总胆固醇",           "BIOCHEM");
        add("CHOL",    "SH016",  "总胆固醇",           "BIOCHEM");
        add("HDL-C",   "SH017",  "高密度脂蛋白胆固醇", "BIOCHEM");
        add("LDL-C",   "SH018",  "低密度脂蛋白胆固醇", "BIOCHEM");
        add("HDL",     "SH017",  "高密度脂蛋白胆固醇", "BIOCHEM");
        add("LDL",     "SH018",  "低密度脂蛋白胆固醇", "BIOCHEM");
        add("VLDL",    "SH019",  "极低密度脂蛋白",     "BIOCHEM");
        add("Na",      "SH020",  "钠",                 "BIOCHEM");
        add("K",       "SH021",  "钾",                 "BIOCHEM");
        add("Cl",      "SH022",  "氯",                 "BIOCHEM");
        add("Ca",      "SH023",  "钙",                 "BIOCHEM");
        add("Mg",      "SH024",  "镁",                 "BIOCHEM");
        add("P",       "SH025",  "磷",                 "BIOCHEM");
        add("CO2",     "SH026",  "二氧化碳结合力",     "BIOCHEM");
        add("FE",      "SH027",  "血清铁",             "BIOCHEM");
        add("LDH",     "SH028",  "乳酸脱氢酶",         "BIOCHEM");
        add("CK",      "SH029",  "肌酸激酶",           "BIOCHEM");
        add("CK-MB",   "SH030",  "肌酸激酶同工酶",     "BIOCHEM");
        add("AMY",     "SH031",  "淀粉酶",             "BIOCHEM");
        add("HBDH",    "SH032",  "α-羟丁酸脱氢酶",    "BIOCHEM");
        add("UREA",    "SH011",  "尿素氮",             "BIOCHEM");
        add("CREA_S",  "SH012",  "肌酐",               "BIOCHEM");
        // 聚创JCH-S480别名
        add("GLUA",    "SH014",  "葡萄糖（血糖）",     "BIOCHEM");
        add("TBILI",   "SH008",  "总胆红素",           "BIOCHEM");
        add("DBILI",   "SH009",  "直接胆红素",         "BIOCHEM");

        // ===================== 尿常规 URINE (优利特URIT-330/560) =====================
        add("GLU-U",   "NC001",  "尿糖",               "URINE");
        add("PRO",     "NC002",  "尿蛋白",             "URINE");
        add("KET",     "NC003",  "酮体",               "URINE");
        add("BLD",     "NC004",  "隐血",               "URINE");
        add("LEU",     "NC005",  "白细胞酯酶",         "URINE");
        add("NIT",     "NC006",  "亚硝酸盐",           "URINE");
        add("URO",     "NC007",  "尿胆原",             "URINE");
        add("BIL",     "NC008",  "胆红素",             "URINE");
        add("SG",      "NC009",  "比重",               "URINE");
        add("PH",      "NC010",  "酸碱度",             "URINE");
        add("VC",      "NC011",  "维生素C",            "URINE");
        add("MA",      "NC012",  "微量白蛋白",         "URINE");
        add("CRE-U",   "NC013",  "尿肌酐",             "URINE");
        add("COL",     "NC014",  "颜色",               "URINE");
        add("CLA",     "NC015",  "透明度",             "URINE");
        // URIT别名
        add("GLUCOSE", "NC001",  "尿糖",               "URINE");
        add("PROTEIN", "NC002",  "尿蛋白",             "URINE");
        add("KETONE",  "NC003",  "酮体",               "URINE");
        add("BLOOD",   "NC004",  "隐血",               "URINE");
        add("WBC-U",   "NC005",  "白细胞酯酶",         "URINE");
        add("NITRITE", "NC006",  "亚硝酸盐",           "URINE");

        // ===================== 糖化血红蛋白 HBA1C (雷诺华LD-600) =====================
        add("HbA1c",   "TH001",  "糖化血红蛋白",       "HBA1C");
        add("HBA1C",   "TH001",  "糖化血红蛋白",       "HBA1C");
        add("A1C",     "TH001",  "糖化血红蛋白",       "HBA1C");
        add("GHB",     "TH001",  "糖化血红蛋白",       "HBA1C");
        add("HbA1",    "TH002",  "血红蛋白A1",         "HBA1C");
        add("HbA2",    "TH003",  "血红蛋白A2",         "HBA1C");
        add("HbF",     "TH004",  "胎儿血红蛋白",       "HBA1C");
    }

    private static void add(String deviceCode, String stdCode, String stdName, String category) {
        ItemMapping m = new ItemMapping(stdCode, stdName, category);
        CODE_MAP.put(deviceCode, m);
        CODE_MAP.put(deviceCode.toUpperCase(), m);
        CODE_MAP.put(deviceCode.toLowerCase(), m);
    }

    /**
     * 根据设备原始编码获取映射
     */
    public ItemMapping getMapping(String deviceCode) {
        if (deviceCode == null || deviceCode.trim().isEmpty()) return null;
        String key = deviceCode.trim();
        ItemMapping m = CODE_MAP.get(key);
        if (m != null) return m;
        m = CODE_MAP.get(key.toUpperCase());
        if (m != null) return m;
        // 去掉前后缀后再匹配（如 "^^^WBC" → "WBC"）
        if (key.contains("^")) {
            String[] parts = key.split("\\^");
            for (int i = parts.length - 1; i >= 0; i--) {
                if (!parts[i].isEmpty()) {
                    m = CODE_MAP.get(parts[i].trim().toUpperCase());
                    if (m != null) return m;
                }
            }
        }
        return null;
    }

    /**
     * 根据设备类型推断项目类别
     */
    public String inferCategory(String deviceType) {
        if (deviceType == null) return "BIOCHEM";
        switch (deviceType.toUpperCase()) {
            case "BLOOD": return "BLOOD";
            case "URINE": return "URINE";
            case "HBA1C": return "HBA1C";
            case "BIOCHEM": return "BIOCHEM";
            default: return "BIOCHEM";
        }
    }
}
