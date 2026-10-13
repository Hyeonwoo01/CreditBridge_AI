import Anthropic from '@anthropic-ai/sdk';
import { betaZodOutputFormat } from '@anthropic-ai/sdk/helpers/beta/zod';
import { z } from 'zod';

const SyllabusSchema = z.object({
  title: z.string(),
  code: z.string(),
  institution: z.string(),
  credits: z.number().nullable(),
  description: z.string(),
  outcomes: z.array(z.string()),
  weeks: z.array(z.object({ label: z.string(), topic: z.string() })),
  textbooks: z.array(z.string()),
  prerequisites: z.array(z.string()),
  assessments: z.array(z.string()),
  keyTopics: z.array(z.string()),
});

export type ExtractedSyllabus = z.infer<typeof SyllabusSchema>;

const SYSTEM = `You extract structured data from university course syllabi so that transfer-credit reviewers can compare courses between institutions.

Rules:
- Copy wording from the syllabus. Weekly topics and learning outcomes are shown to reviewers as highlighted evidence, so quote the original phrasing instead of paraphrasing. Translate to English only when the source is not in English.
- weeks: one entry per scheduled week/lecture block in order. label keeps the original numbering ("Week 3", "Weeks 3-4", "Lecture 5"); topic is the content covered.
- credits: the number of credit hours/units for the course, or null if the syllabus does not state it.
- keyTopics: 5-20 standard English names of the academic concepts the course actually teaches (e.g. "chain rule", "hypothesis testing", "linked lists"), as a reviewer would write them.
- Use an empty string or empty list for anything the syllabus does not contain. Never invent content.`;

let client: Anthropic | null = null;

export function aiConfigured(): boolean {
  return Boolean(process.env.ANTHROPIC_API_KEY || process.env.ANTHROPIC_AUTH_TOKEN);
}

export async function extractWithClaude(text: string): Promise<ExtractedSyllabus> {
  client ??= new Anthropic();
  const response = await client.beta.messages.parse({
    model: 'claude-opus-5-5',
    max_tokens: 16000,
    betas: ['server-side-fallback-2026-07-01'],
    fallbacks: 'default',
    output_config: {
      effort: 'low',
      format: betaZodOutputFormat(SyllabusSchema),
    },
    system: SYSTEM,
    messages: [{ role: 'user', content: `<syllabus>\n${text}\n</syllabus>` }],
  });

  if (response.stop_reason === 'refusal') {
    throw new Error('The model declined to process this syllabus.');
  }
  if (response.stop_reason === 'max_tokens' || !response.parsed_output) {
    throw new Error('Could not parse the syllabus into the expected structure.');
  }
  return response.parsed_output;
}

const EvaluationSchema = z.object({
  candidates: z.array(
    z.object({
      code: z.string(),
      level: z.enum(['same', 'lower', 'higher']),
      levelNote: z.string(),
      summary: z.string(),
      units: z.array(
        z.object({
          unit: z.string(),
          coverage: z.number(),
          evidence: z.array(z.object({ where: z.string(), quote: z.string() })),
          reason: z.string(),
        }),
      ),
    }),
  ),
});

/** 강의 내용 비교. 응답 검증(인용문 확인 등)은 클라이언트의 validateEvaluation이 맡는다. */
export async function evaluateWithClaude(prompt: string): Promise<z.infer<typeof EvaluationSchema>> {
  client ??= new Anthropic();
  const response = await client.beta.messages.parse({
    model: 'claude-opus-5-5',
    max_tokens: 16000,
    betas: ['server-side-fallback-2026-07-01'],
    fallbacks: 'default',
    output_config: {
      effort: 'medium',
      format: betaZodOutputFormat(EvaluationSchema),
    },
    messages: [{ role: 'user', content: prompt }],
  });

  if (response.stop_reason === 'refusal') {
    throw new Error('The model declined to evaluate this course.');
  }
  if (response.stop_reason === 'max_tokens' || !response.parsed_output) {
    throw new Error('Could not parse the evaluation.');
  }
  return response.parsed_output;
}
