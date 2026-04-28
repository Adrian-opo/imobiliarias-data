"use client";

import { useEffect } from "react";

const ICON_DEFAULT = "/icon.svg";
const ICON_ACTIVE = "/icon-active.svg";

function ensureFaviconLink(): HTMLLinkElement | null {
  if (typeof document === "undefined") return null;

  let link = document.querySelector("link[data-animated-favicon='true']") as HTMLLinkElement | null;
  if (link) return link;

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
      link.href = `${icons[index]}?v=${Date.now()}`;
    }, 900);

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
