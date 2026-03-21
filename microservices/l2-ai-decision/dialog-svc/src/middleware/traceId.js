'use strict';

const { randomBytes } = require('crypto');

/**
 * TraceID 中间件
 *
 * 读取上游传入的 X-Trace-ID 请求头（由 L1 API Gateway 注入），
 * 若不存在则自动生成 32 位十六进制 ID。
 * 将 traceId 挂载到 req.traceId，并在响应头中回写 X-Trace-ID。
 *
 * @param {import('express').Request}  req
 * @param {import('express').Response} res
 * @param {import('express').NextFunction} next
 */
function traceIdMiddleware(req, res, next) {
  const traceId = req.headers['x-trace-id'] || randomBytes(16).toString('hex');
  req.traceId = traceId;
  res.setHeader('X-Trace-ID', traceId);
  next();
}

module.exports = traceIdMiddleware;
