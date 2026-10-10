"use client";

import { useEffect, useState } from "react";

import CopyButton from "@/components/CopyButton";
import { chartAlt, coverAlt, type ChartFacts, type Cover, type Row, type Spec } from "@/lib/graphics/alt.ts";
import { COVER_SIZE, coverSvg, type CoverFormat } from "@/lib/graphics/cover.ts";
import { parseFont } from "@/lib/graphics/font.ts";

type Props = {
  slug: string;
  headline: string;
  cover: Cover;
  specs: Spec[];
  data: Row[];
  source?: string;
  groupNoun?: string;
  facts?: ChartFacts;
};

const FORMATS: { format: CoverFormat; label: string; file: string }[] = [
  { format: "landscape", label: "Cover / OG card (1200 × 630)", file: "" },
  { format: "portrait", label: "Instagram / LinkedIn (1080 × 1350)", file: "-portrait" },
];

async function loadFont(path: string) {
  const res = await fetch(path);
  if (!res.ok) throw new Error(`could not load ${path}`);
  return parseFont(await res.arrayBuffer());
}

/** SVG string -> PNG blob at the SVG's own pixel size (text is outlined, so no font loading). */
function toPng(svg: string, w: number, h: number): Promise<Blob> {
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(new Blob([svg], { type: "image/svg+xml" }));
    const img = new Image();
    img.onload = () => {
      const canvas = document.createElement("canvas");
      canvas.width = w;
      canvas.height = h;
      canvas.getContext("2d")!.drawImage(img, 0, 0, w, h);
      URL.revokeObjectURL(url);
      canvas.toBlob((b) => (b ? resolve(b) : reject(new Error("PNG export failed"))), "image/png");
    };
    img.onerror = () => reject(new Error("could not render the SVG"));
    img.src = url;
  });
}

/**
 * Story covers rendered in the browser with the same code and fonts as the site build, so a
 * draft's graphics can be reviewed and downloaded before it is published.
 */
export default function CoverGraphics(props: Props) {
  const [svgs, setSvgs] = useState<Record<CoverFormat, string> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<CoverFormat | null>(null);

  useEffect(() => {
    let live = true;
    Promise.all([loadFont("/fonts/Inter-Regular.ttf"), loadFont("/fonts/Inter-Bold.ttf")])
      .then(([regular, bold]) => {
        const input = {
          headline: props.headline,
          cover: props.cover,
          spec: props.specs[0],
          data: props.data,
          source: props.source,
          groupNoun: props.groupNoun,
        };
        const fonts = { regular, bold };
        if (live) {
          setSvgs({ landscape: coverSvg(input, fonts, "landscape"), portrait: coverSvg(input, fonts, "portrait") });
        }
      })
      .catch((e: Error) => live && setError(e.message));
    return () => {
      live = false;
    };
  }, [props]);

  async function download(format: CoverFormat, suffix: string) {
    if (!svgs) return;
    setBusy(format);
    try {
      const { w, h } = COVER_SIZE[format];
      const blob = await toPng(svgs[format], w, h);
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = `datatales-${props.slug}${suffix}.png`;
      a.click();
      setTimeout(() => URL.revokeObjectURL(a.href), 1000);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(null);
    }
  }

  const imageAlt = coverAlt(props.headline, props.cover, props.specs[0], props.data);
  const chartAlts = props.specs.map((s) => chartAlt(s, props.data, s.title ?? props.headline, props.facts));

  if (error) return <p className="msg bad">Graphics: {error}</p>;
  if (!svgs) return <p className="muted">Rendering graphics…</p>;
  return (
    <div>
      <div className="cover-grid">
        {FORMATS.map(({ format, label, file }) => (
          <figure key={format} className="cover-item">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={`data:image/svg+xml;charset=utf-8,${encodeURIComponent(svgs[format])}`}
              alt={imageAlt}
              width={COVER_SIZE[format].w}
              height={COVER_SIZE[format].h}
            />
            <figcaption className="row">
              <span className="small muted">{label}</span>
              <button type="button" className="secondary" disabled={busy !== null} onClick={() => download(format, file)}>
                {busy === format ? "Exporting…" : "Download PNG"}
              </button>
            </figcaption>
          </figure>
        ))}
      </div>
      <h3>Alt text</h3>
      <p className="small">
        Image: {imageAlt} <CopyButton text={imageAlt} label="Copy" />
      </p>
      {chartAlts.map((alt, i) => (
        <p key={i} className="small">
          Chart {i + 1} ({props.specs[i].type}): {alt} <CopyButton text={alt} label="Copy" />
        </p>
      ))}
    </div>
  );
}
