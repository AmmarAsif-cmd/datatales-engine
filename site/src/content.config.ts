import { defineCollection } from 'astro:content';
import { glob } from 'astro/loaders';
import { z } from 'astro/zod';

/** Migrated Hashnode posts. Served at the site root: /<slug>. */
const posts = defineCollection({
  loader: glob({ pattern: '**/*.md', base: './src/content/posts' }),
  schema: z.object({
    title: z.string(),
    seoTitle: z.string().optional(),
    description: z.string(),
    date: z.coerce.date(),
    updated: z.coerce.date().optional(),
    cover: z.string().optional(),
    coverAlt: z.string().optional(),
    tags: z.array(z.string()).default([]),
    originalUrl: z.url().optional(),
    /** Source dataset URLs this post uses; stories from the same source link to it. */
    sources: z.array(z.url()).default([]),
  }),
});

const chartSpec = z.object({
  type: z.enum(['line', 'bar', 'dot', 'slope', 'map']),
  x: z.string(),
  y: z.string(),
  series: z.string().optional(),
  highlight: z.union([z.string(), z.array(z.string())]).optional(),
  annotation: z.string().optional(),
  title: z.string().optional(),
  yLabel: z.string().optional(),
  /** slope: periods compared (default first and last) */
  start: z.string().optional(),
  end: z.string().optional(),
  /** map: period shown (default last) */
  period: z.string().optional(),
});

const keyNumber = z.object({
  label: z.string(),
  value: z.string(),
  note: z.string().optional(),
  /** 'rank': a rank change such as "4th → 1st" (from a rank-shift finding). */
  kind: z.enum(['value', 'rank']).optional(),
});

/**
 * Pipeline stories. Written by worker/datatales/publish.py; served at /stories/<slug>.
 * Every number shown comes from these fields, which come from code.
 */
const stories = defineCollection({
  loader: glob({ pattern: '**/*.md', base: './src/content/stories' }),
  schema: z.object({
    title: z.string().max(90),
    description: z.string(),
    hook: z.string(),
    date: z.coerce.date(),
    updated: z.coerce.date().optional(),
    source: z.object({
      name: z.string(),
      publisher: z.string().optional(),
      url: z.url(),
      licence: z.string().optional(),
    }),
    fetchedAt: z.coerce.date(),
    recipeVersion: z.string(),
    datasetChecksum: z.string().optional(),
    period: z.string().optional(),
    keyNumbers: z.array(keyNumber).min(1).max(4),
    chart_spec: chartSpec,
    /** Up to two more charts of the same chart_data (e.g. a slope chart and a map). */
    more_charts: z.array(chartSpec).max(2).default([]),
    chart_data: z.array(z.record(z.string(), z.union([z.string(), z.number(), z.null()]))),
    numbers: z.record(z.string(), z.unknown()).default({}),
    /** Demo content with fake data. Never built in production. */
    sample: z.boolean().default(false),
  }),
});

export const collections = { posts, stories };
