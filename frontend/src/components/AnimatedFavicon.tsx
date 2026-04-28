"use client";

import { useEffect } from "react";

/**
 * Two SVG favicon variants as data URIs — no external files needed.
 *
 * - ICON_DEFAULT: solid green house
 * - ICON_ACTIVE:  green house with a subtle glow ring
 */
const ICON_DEFAULT = svgDataUri(
  `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">
    <rect width="32" height="32" rx="6" fill="#059669"/>
    <path d="M16 6 6 14v12h8v-8h4v8h8V14L16 6z" fill="#fff" opacity=".95"/>
    <rect x="13" y="18" width="6" height="8" fill="#059669"/>
  </svg>`
);

const ICON_ACTIVE = svgDataUri(
  `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">
    <defs>
      <radialGradient id="g" cx="50%" cy="50%" r="50%">
        <stop offset="0%" stop-color="#34d399" stop-opacity=".4"/>
        <stop offset="100%" stop-color="#059669" stop-opacity="1"/>
      </radialGradient>
    </defs>
    <rect width="32" height="32" rx="6" fill="url(#g)"/>
    <path d="M16 6 6 14v12h8v-8h4v8h8V14L16 6z" fill="#fff" opacity=".95"/>
    <rect x="13" y="18" width="6" height="8" fill="#059669"/>
    <circle cx="24" cy="8" r="6" fill="#34d399" opacity=".6"/>
    <circle cx="24" cy="8" r="3" fill="#6ee7b7" opacity=".8"/>
  </svg>`
);

function svgDataUri(svg: string): string {
  // Minify a little and encode as data URI
  return (
    "data:image/svg+xml," +
    encodeURIComponent(
      svg
        .replace(/>\s+</g, "><")
        .replace(/\s{2,}/g, " ")
        .trim()
    )
  );
}

function ensureFaviconLink(): HTMLLinkElement | null {
  if (typeof document === "undefined") return null;

  document
    .querySelectorAll('link[rel="icon"], link[rel="shortcut icon"]')
    .forEach((existing) => {
      if (!(existing as HTMLLinkElement).dataset.animatedFavicon) {
        existing.parentNode?.removeChild(existing);
      }
    });

  // Already ours — reuse it
  let link = document.querySelector(
    "link[data-animated-favicon='true']"
  ) as HTMLLinkElement | null;
  if (link) return link;

  // Reuse an existing <link rel="icon"> instead of creating a duplicate
  link = document.querySelector(
    'link[rel="icon"], link[rel="shortcut icon"]'
  ) as HTMLLinkElement | null;
  if (link) {
    link.setAttribute("data-animated-favicon", "true");
    link.type = "image/svg+xml";
    return link;
  }

  // Nothing exists — create fresh
  link = document.createElement("link");
  link.rel = "icon";
  link.type = "image/svg+xml";
  link.setAttribute("data-animated-favicon", "true");
  document.head.appendChild(link);
  return link;
}

export default function AnimatedFavicon() {
  useEffect(() => {
    const link = ensureFaviconLink();
    if (!link) return;

    const icons = [ICON_DEFAULT, ICON_ACTIVE];
    let index = 0;

    link.href = icons[index];

    const interval = window.setInterval(() => {
      index = (index + 1) % icons.length;
      link.href = `${icons[index]}#t=${Date.now()}`;
    }, 1500);

    const onVisibilityChange = () => {
      if (document.hidden) {
        link.href = ICON_DEFAULT;
      }
    };

    document.addEventListener("visibilitychange", onVisibilityChange);

    return () => {
      window.clearInterval(interval);
      document.removeEventListener("visibilitychange", onVisibilityChange);
      link.href = ICON_DEFAULT;
    };
  }, []);

  return null;
}
