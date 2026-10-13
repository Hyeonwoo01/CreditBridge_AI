import type { IncomingMessage, ServerResponse } from 'node:http';
import Anthropic from '@anthropic-ai/sdk';
import { aiConfigured, evaluateWithClaude, extractWithClaude } from './extract';
import { buildEvaluationPrompt } from '../src/lib/aiMatch';
import { getUniversity } from '../src/data/catalog';
import type { MyCourse } from '../src/lib/types';

const MAX_BODY_BYTES = 2 * 1024 * 1024;

function send(res: ServerResponse, status: number, body: unknown) {
  res.statusCode = status;
  res.setHeader('Content-Type', 'application/json; charset=utf-8');
  res.end(JSON.stringify(body));
}

async function readJson(req: IncomingMessage): Promise<unknown> {
  const chunks: Buffer[] = [];
  let size = 0;
  for await (const chunk of req) {
    size += chunk.length;
    if (size > MAX_BODY_BYTES) throw new RangeError('too large');
    chunks.push(chunk as Buffer);
  }
  return JSON.parse(Buffer.concat(chunks).toString('utf8'));
}

/** /api/* 요청을 처리한다. Vite 개발 서버와 프로덕션 서버가 함께 사용한다. */
export async function handleApi(req: IncomingMessage, res: ServerResponse): Promise<void> {
  const url = new URL(req.url ?? '/', 'http://localhost');

  if (req.method === 'GET' && url.pathname === '/api/health') {
    return send(res, 200, { ai: aiConfigured() });
  }

  if (req.method === 'POST' && url.pathname === '/api/extract') {
    if (!aiConfigured()) return send(res, 503, { error: 'AI extraction is not configured.' });
    let text: unknown;
    try {
      text = ((await readJson(req)) as { text?: unknown }).text;
    } catch (err) {
      const tooLarge = err instanceof RangeError;
      return send(res, tooLarge ? 413 : 400, { error: tooLarge ? 'Syllabus is too large.' : 'Invalid JSON body.' });
    }
    if (typeof text !== 'string' || text.trim().length < 40) {
      return send(res, 400, { error: 'Syllabus text is missing or too short.' });
    }
    try {
      return send(res, 200, { syllabus: await extractWithClaude(text) });
    } catch (err) {
      if (err instanceof Anthropic.RateLimitError) return send(res, 429, { error: 'Rate limited. Try again shortly.' });
      if (err instanceof Anthropic.APIError) return send(res, 502, { error: `Claude API error (${err.status ?? 'network'}).` });
      return send(res, 502, { error: err instanceof Error ? err.message : 'Extraction failed.' });
    }
  }

  if (req.method === 'POST' && url.pathname === '/api/evaluate') {
    if (!aiConfigured()) return send(res, 503, { error: 'AI evaluation is not configured.' });
    let body: { schoolId?: unknown; course?: { rawText?: unknown; parsed?: unknown } };
    try {
      body = (await readJson(req)) as typeof body;
    } catch (err) {
      const tooLarge = err instanceof RangeError;
      return send(res, tooLarge ? 413 : 400, { error: tooLarge ? 'Syllabus is too large.' : 'Invalid JSON body.' });
    }
    const { schoolId, course } = body;
    if (typeof schoolId !== 'string' || typeof course?.rawText !== 'string' || typeof course.parsed !== 'object' || !course.parsed) {
      return send(res, 400, { error: 'schoolId and course are required.' });
    }
    const prompt = buildEvaluationPrompt(course as unknown as MyCourse, getUniversity(schoolId));
    try {
      return send(res, 200, { evaluation: await evaluateWithClaude(prompt) });
    } catch (err) {
      if (err instanceof Anthropic.RateLimitError) return send(res, 429, { error: 'Rate limited. Try again shortly.' });
      if (err instanceof Anthropic.APIError) return send(res, 502, { error: `Claude API error (${err.status ?? 'network'}).` });
      return send(res, 502, { error: err instanceof Error ? err.message : 'Evaluation failed.' });
    }
  }

  send(res, 404, { error: 'Not found' });
}
