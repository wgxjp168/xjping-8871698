'use strict';

/**
 * Integration-style tests for dialog-svc using Jest + Supertest.
 *
 * Redis (sessionStore) and the downstream intent/decision clients are mocked
 * so the tests run without any external infrastructure.
 */

const request = require('supertest');
const jwt = require('jsonwebtoken');

// ─── Mock dependencies BEFORE requiring the app ──────────────────────────────

// Mock sessionStore
jest.mock('../src/services/sessionStore', () => ({
  create: jest.fn(),
  get: jest.fn(),
  update: jest.fn(),
  delete: jest.fn(),
  expire: jest.fn(),
  getClient: jest.fn(() => ({
    quit: jest.fn().mockResolvedValue(undefined),
  })),
  setClient: jest.fn(),
}));

// Mock intentClient
jest.mock('../src/services/intentClient', () => ({
  recognize: jest.fn(),
  extractEntities: jest.fn(),
  detectBrand: jest.fn(),
}));

// Mock decisionClient
jest.mock('../src/services/decisionClient', () => ({
  analyze: jest.fn(),
  getReport: jest.fn(),
}));

// ─── Imports (after mocks are in place) ──────────────────────────────────────

const app = require('../src/app');
const sessionStore = require('../src/services/sessionStore');
const intentClient = require('../src/services/intentClient');

// ─── Helpers ──────────────────────────────────────────────────────────────────

const JWT_SECRET = 'ilbuy-dialog-svc-dev-secret';

function makeToken(payload = { sub: 'user-test-1', userId: 'user-test-1' }) {
  return jwt.sign(payload, JWT_SECRET, { expiresIn: '1h' });
}

function makeSession(overrides = {}) {
  return {
    sessionId: 'sess-abc-123',
    userId: 'user-test-1',
    state: 'COLLECTING',
    messages: [],
    context: {
      intent: null,
      entities: [],
      brandStatus: null,
      productParams: {},
    },
    turnCount: 0,
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
    ...overrides,
  };
}

// ─── Tests ────────────────────────────────────────────────────────────────────

describe('GET /health', () => {
  it('should return 200 with service info', async () => {
    const res = await request(app).get('/health');

    expect(res.status).toBe(200);
    expect(res.body).toMatchObject({
      status: 'ok',
      service: 'dialog-svc',
      version: '1.0.0',
    });
    expect(res.body.timestamp).toBeDefined();
  });
});

// ─── POST /dialog/session ─────────────────────────────────────────────────────

describe('POST /dialog/session', () => {
  beforeEach(() => {
    jest.clearAllMocks();

    // intentClient.recognize returns a basic intent result
    intentClient.recognize.mockResolvedValue({
      intent: 'search_product',
      confidence: 0.95,
    });

    // sessionStore.create & update succeed silently
    sessionStore.create.mockResolvedValue(undefined);
    sessionStore.update.mockResolvedValue(undefined);
  });

  it('should create a new session and return sessionId', async () => {
    const res = await request(app)
      .post('/dialog/session')
      .send({ userId: 'user-1', message: 'I am looking for a laptop' });

    expect(res.status).toBe(201);
    expect(res.body).toHaveProperty('sessionId');
    expect(res.body).toHaveProperty('message');
    expect(res.body).toHaveProperty('state');
    expect(res.body).toHaveProperty('suggestions');
    expect(res.body).toHaveProperty('requiresMoreInfo');
    expect(sessionStore.create).toHaveBeenCalledTimes(1);
  });

  it('should work without an explicit userId (auto-generate anon id)', async () => {
    const res = await request(app)
      .post('/dialog/session')
      .send({ message: 'Find me a smartphone' });

    expect(res.status).toBe(201);
    expect(res.body.sessionId).toBeDefined();
  });

  it('should return 400 when message is missing', async () => {
    const res = await request(app)
      .post('/dialog/session')
      .send({ userId: 'user-1' });

    expect(res.status).toBe(400);
    expect(res.body.code).toBe('INVALID_BODY');
  });

  it('should return 400 when message is an empty string', async () => {
    const res = await request(app)
      .post('/dialog/session')
      .send({ userId: 'user-1', message: '   ' });

    expect(res.status).toBe(400);
    expect(res.body.code).toBe('INVALID_BODY');
  });
});

// ─── POST /dialog/message ─────────────────────────────────────────────────────

describe('POST /dialog/message', () => {
  let token;

  beforeEach(() => {
    jest.clearAllMocks();
    token = makeToken();

    const session = makeSession();
    sessionStore.get.mockResolvedValue(session);
    sessionStore.update.mockResolvedValue(undefined);

    intentClient.recognize.mockResolvedValue({
      intent: 'refine_search',
      confidence: 0.88,
    });
    intentClient.extractEntities.mockResolvedValue({ entities: [] });
    intentClient.detectBrand.mockResolvedValue({ brands: [], status: 'none' });
  });

  it('should process a message and return dialog response', async () => {
    const res = await request(app)
      .post('/dialog/message')
      .set('Authorization', `Bearer ${token}`)
      .send({ sessionId: 'sess-abc-123', message: 'Under $1000 budget' });

    expect(res.status).toBe(200);
    expect(res.body).toHaveProperty('sessionId', 'sess-abc-123');
    expect(res.body).toHaveProperty('message');
    expect(res.body).toHaveProperty('state');
    expect(res.body).toHaveProperty('suggestions');
    expect(res.body).toHaveProperty('requiresMoreInfo');
  });

  it('should return 401 without Authorization header', async () => {
    const res = await request(app)
      .post('/dialog/message')
      .send({ sessionId: 'sess-abc-123', message: 'hello' });

    expect(res.status).toBe(401);
    expect(res.body.code).toBe('MISSING_TOKEN');
  });

  it('should return 401 with an invalid token', async () => {
    const res = await request(app)
      .post('/dialog/message')
      .set('Authorization', 'Bearer not.a.valid.token')
      .send({ sessionId: 'sess-abc-123', message: 'hello' });

    expect(res.status).toBe(401);
    expect(res.body.code).toBe('INVALID_TOKEN');
  });

  it('should return 400 when sessionId is missing', async () => {
    const res = await request(app)
      .post('/dialog/message')
      .set('Authorization', `Bearer ${token}`)
      .send({ message: 'hello' });

    expect(res.status).toBe(400);
    expect(res.body.code).toBe('INVALID_BODY');
  });

  it('should return 404 when session does not exist', async () => {
    sessionStore.get.mockResolvedValue(null);

    const res = await request(app)
      .post('/dialog/message')
      .set('Authorization', `Bearer ${token}`)
      .send({ sessionId: 'non-existent-session', message: 'hello' });

    expect(res.status).toBe(404);
  });
});

// ─── GET /dialog/session/:sessionId ──────────────────────────────────────────

describe('GET /dialog/session/:sessionId', () => {
  beforeEach(() => jest.clearAllMocks());

  it('should return the session object', async () => {
    const session = makeSession();
    sessionStore.get.mockResolvedValue(session);

    const res = await request(app).get('/dialog/session/sess-abc-123');

    expect(res.status).toBe(200);
    expect(res.body.sessionId).toBe('sess-abc-123');
    expect(res.body.state).toBe('COLLECTING');
  });

  it('should return 404 for unknown sessionId', async () => {
    sessionStore.get.mockResolvedValue(null);

    const res = await request(app).get('/dialog/session/unknown-id');

    expect(res.status).toBe(404);
    expect(res.body.code).toBe('SESSION_NOT_FOUND');
  });
});

// ─── DELETE /dialog/session/:sessionId ───────────────────────────────────────

describe('DELETE /dialog/session/:sessionId', () => {
  beforeEach(() => jest.clearAllMocks());

  it('should delete the session and return 204', async () => {
    const session = makeSession();
    sessionStore.get.mockResolvedValue(session);
    sessionStore.delete.mockResolvedValue(undefined);

    const res = await request(app).delete('/dialog/session/sess-abc-123');

    expect(res.status).toBe(204);
    expect(sessionStore.delete).toHaveBeenCalledWith('sess-abc-123');
  });

  it('should return 404 when session does not exist', async () => {
    sessionStore.get.mockResolvedValue(null);

    const res = await request(app).delete('/dialog/session/nonexistent');

    expect(res.status).toBe(404);
  });
});

// ─── GET /dialog/history/:sessionId ──────────────────────────────────────────

describe('GET /dialog/history/:sessionId', () => {
  beforeEach(() => jest.clearAllMocks());

  it('should return message history', async () => {
    const session = makeSession({
      messages: [
        { role: 'user', content: 'hello', timestamp: new Date().toISOString() },
        { role: 'assistant', content: 'Hi there!', timestamp: new Date().toISOString() },
      ],
      turnCount: 1,
    });
    sessionStore.get.mockResolvedValue(session);

    const res = await request(app).get('/dialog/history/sess-abc-123');

    expect(res.status).toBe(200);
    expect(res.body.sessionId).toBe('sess-abc-123');
    expect(res.body.messages).toHaveLength(2);
    expect(res.body.turnCount).toBe(1);
  });

  it('should return 404 for unknown session', async () => {
    sessionStore.get.mockResolvedValue(null);

    const res = await request(app).get('/dialog/history/unknown-id');

    expect(res.status).toBe(404);
  });
});

// ─── 404 catch-all ───────────────────────────────────────────────────────────

describe('Unknown routes', () => {
  it('should return 404 for an unregistered path', async () => {
    const res = await request(app).get('/no-such-route');

    expect(res.status).toBe(404);
    expect(res.body.code).toBe('NOT_FOUND');
  });
});
