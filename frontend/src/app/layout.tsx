import type { Metadata } from "next";
import "./globals.css";
import Header from "@/components/Header";
import Footer from "@/components/Footer";
import AnimatedFavicon from "@/components/AnimatedFavicon";

export const metadata: Metadata = {
  title: {
    default: "Imóveis Ji-Paraná - Central de Imóveis",
    template: "%s | Imóveis Ji-Paraná",
  },
  description:
    "Central de imóveis de Ji-Paraná - Encontre o imóvel ideal na capital do café de Rondônia. Imóveis de várias imobiliárias em um só lugar.",
  openGraph: {
    title: "Imóveis Ji-Paraná",
    description:
      "Central de imóveis de Ji-Paraná - Encontre o imóvel ideal na capital do café de Rondônia.",
    locale: "pt_BR",
    type: "website",
  },
  icons: {
    icon: [
      { url: "/icon.svg", type: "image/svg+xml" },
      { url: "/favicon.ico" },
    ],
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="pt-BR">
      <body className="flex min-h-screen flex-col">
        <AnimatedFavicon />
        <Header />
        <main className="flex-1">{children}</main>
        <Footer />
      </body>
    </html>
  );
}
