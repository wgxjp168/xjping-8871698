package com.ilbuy.access.controller;

import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;
import reactor.core.publisher.Mono;

import java.util.Map;

@RestController
public class HealthController {

    @GetMapping(value = "/", produces = MediaType.TEXT_HTML_VALUE)
    public Mono<String> index() {
        return Mono.just("""
            <!DOCTYPE html>
            <html lang="zh-CN">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>我来购 ILbuy - AI智能体微服务平台</title>
                <style>
                    * { margin: 0; padding: 0; box-sizing: border-box; }
                    body { font-family: -apple-system, 'Segoe UI', sans-serif; background: linear-gradient(135deg, #0f0c29, #302b63, #24243e); color: #fff; min-height: 100vh; }
                    .container { max-width: 1100px; margin: 0 auto; padding: 30px 20px; }
                    h1 { text-align: center; font-size: 2.2em; margin-bottom: 8px; background: linear-gradient(90deg, #f7971e, #ffd200); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
                    .subtitle { text-align: center; color: #aaa; margin-bottom: 30px; font-size: 1.1em; }
                    .status-bar { background: rgba(255,255,255,0.05); border-radius: 12px; padding: 15px 25px; margin-bottom: 25px; display: flex; justify-content: space-between; align-items: center; border: 1px solid rgba(255,255,255,0.1); }
                    .status-dot { width: 12px; height: 12px; border-radius: 50%; background: #4caf50; display: inline-block; margin-right: 8px; animation: pulse 2s infinite; }
                    @keyframes pulse { 0%,100% { opacity: 1; } 50% { opacity: 0.4; } }
                    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 20px; }
                    .card { background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.1); border-radius: 14px; padding: 22px; transition: all 0.3s; }
                    .card:hover { transform: translateY(-3px); border-color: #ffd200; box-shadow: 0 8px 25px rgba(255,210,0,0.15); }
                    .card h3 { font-size: 1.15em; margin-bottom: 6px; color: #ffd200; }
                    .card p { color: #999; font-size: 0.9em; margin-bottom: 14px; }
                    .links a { display: inline-block; background: rgba(255,210,0,0.12); color: #ffd200; padding: 6px 14px; border-radius: 6px; text-decoration: none; font-size: 0.85em; margin: 3px 4px 3px 0; border: 1px solid rgba(255,210,0,0.2); transition: all 0.2s; }
                    .links a:hover { background: #ffd200; color: #000; }
                    .tag { display: inline-block; background: rgba(76,175,80,0.15); color: #4caf50; padding: 2px 10px; border-radius: 4px; font-size: 0.8em; margin-left: 8px; }
                    #result { background: rgba(0,0,0,0.3); border-radius: 10px; padding: 18px; margin-top: 25px; min-height: 80px; border: 1px solid rgba(255,255,255,0.08); white-space: pre-wrap; word-break: break-all; font-family: 'Courier New', monospace; font-size: 0.88em; color: #8f8; display: none; }
                    .copy-btn { float: right; background: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.2); color: #fff; padding: 4px 12px; border-radius: 5px; cursor: pointer; font-size: 0.8em; }
                </style>
            </head>
            <body>
            <div class="container">
                <h1>🛒 我来购 ILbuy</h1>
                <p class="subtitle">AI智能体微服务平台 · 统一网关入口 · 端口 8080</p>

                <div class="status-bar">
                    <span><span class="status-dot"></span> 平台运行中 · 6个模块已连接</span>
                    <span style="color:#666" id="time"></span>
                </div>

                <div class="grid">
                    <div class="card">
                        <h3>📡 接入层 · API 网关 <span class="tag">:8080</span></h3>
                        <p>统一入口，路由转发到所有微服务</p>
                        <div class="links">
                            <a href="#" onclick="api('/actuator/gateway/routes')">查看路由表</a>
                            <a href="#" onclick="api('/health')">健康检查</a>
                        </div>
                    </div>
                    <div class="card">
                        <h3>🧠 AI 决策中枢 <span class="tag">:8081</span></h3>
                        <p>商品推荐 · 智能定价 · 风控检测 · 用户分群</p>
                        <div class="links">
                            <a href="#" onclick="api('/api/ai/status')">服务状态</a>
                            <a href="#" onclick="api('/api/ai/recommendations/user001?limit=3')">AI推荐</a>
                            <a href="#" onclick="post('/api/ai/pricing',{productId:'P001',basePrice:1299,category:'electronics',stockQuantity:50,demandLevel:9})">智能定价</a>
                            <a href="#" onclick="post('/api/ai/decide',{decisionType:'fraud_detection',inputData:'order_check',userId:'u1'})">风控检测</a>
                        </div>
                    </div>
                    <div class="card">
                        <h3>💼 业务逻辑层 <span class="tag">:8082</span></h3>
                        <p>用户管理 · 商品目录 · 订单处理 · 购物车</p>
                        <div class="links">
                            <a href="#" onclick="api('/api/users')">用户列表</a>
                            <a href="#" onclick="api('/api/products')">全部商品</a>
                            <a href="#" onclick="api('/api/products?category=electronics')">电子产品</a>
                            <a href="#" onclick="post('/api/cart/U001/items',{productId:'P001',quantity:2})">加入购物车</a>
                            <a href="#" onclick="api('/api/cart/U001')">查看购物车</a>
                            <a href="#" onclick="post('/api/orders',{userId:'U001',shippingAddress:'北京市朝阳区',paymentMethod:'WECHAT',items:[{productId:'P002',quantity:1}]})">创建订单</a>
                        </div>
                    </div>
                    <div class="card">
                        <h3>💾 数据持久层 <span class="tag">:8083</span></h3>
                        <p>JPA实体 · H2数据库 · 数据访问服务</p>
                        <div class="links">
                            <a href="#" onclick="api('/api/data/status')">服务状态</a>
                            <a href="#" onclick="api('/api/data/stats')">数据统计</a>
                            <a href="#" onclick="api('/api/data/users')">DB用户</a>
                            <a href="#" onclick="api('/api/data/products')">DB商品</a>
                            <a href="#" onclick="api('/api/data/products/search?q=智能')">搜索:智能</a>
                        </div>
                    </div>
                    <div class="card">
                        <h3>🔧 支撑运维层 <span class="tag">:8084</span></h3>
                        <p>健康聚合 · 运维仪表盘 · 服务注册</p>
                        <div class="links">
                            <a href="#" onclick="api('/api/ops/dashboard')">运维仪表盘</a>
                            <a href="#" onclick="api('/api/ops/health/all')">健康总览</a>
                            <a href="#" onclick="api('/api/ops/services')">服务注册</a>
                        </div>
                    </div>
                    <div class="card">
                        <h3>⚙️ 配置中心 <span class="tag">config-repo</span></h3>
                        <p>12个YAML配置文件 · dev/prod多环境</p>
                        <div class="links">
                            <a href="#" onclick="api('/api/ops/status')">运维状态</a>
                        </div>
                    </div>
                </div>

                <div id="result"></div>
            </div>

            <script>
                document.getElementById('time').textContent = new Date().toLocaleString('zh-CN');
                setInterval(()=>document.getElementById('time').textContent=new Date().toLocaleString('zh-CN'),1000);

                async function api(path){
                    const el=document.getElementById('result'); el.style.display='block';
                    el.innerHTML='<span style="color:#ffd200">GET '+path+'</span>\\n加载中...';
                    try{
                        const r=await fetch(path); const j=await r.json();
                        el.innerHTML='<button class="copy-btn" onclick="navigator.clipboard.writeText(this.parentElement.dataset.raw)">复制</button><span style="color:#ffd200">GET '+path+'</span> <span style="color:#4caf50">'+r.status+'</span>\\n\\n'+JSON.stringify(j,null,2);
                        el.dataset.raw=JSON.stringify(j,null,2);
                    }catch(e){el.innerHTML='<span style="color:#f44">错误: '+e.message+'</span>';}
                }
                async function post(path,body){
                    const el=document.getElementById('result'); el.style.display='block';
                    el.innerHTML='<span style="color:#ffd200">POST '+path+'</span>\\n加载中...';
                    try{
                        const r=await fetch(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
                        const j=await r.json();
                        el.innerHTML='<button class="copy-btn" onclick="navigator.clipboard.writeText(this.parentElement.dataset.raw)">复制</button><span style="color:#ffd200">POST '+path+'</span> <span style="color:#4caf50">'+r.status+'</span>\\n\\n'+JSON.stringify(j,null,2);
                        el.dataset.raw=JSON.stringify(j,null,2);
                    }catch(e){el.innerHTML='<span style="color:#f44">错误: '+e.message+'</span>';}
                }
            </script>
            </body>
            </html>
            """);
    }

    @GetMapping("/health")
    public Mono<ResponseEntity<Map<String, String>>> health() {
        return Mono.just(ResponseEntity.ok(Map.of(
                "status", "UP",
                "service", "access-layer"
        )));
    }
}
