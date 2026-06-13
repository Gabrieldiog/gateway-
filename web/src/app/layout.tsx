import type { Metadata } from "next";
import { Fraunces, Public_Sans, Newsreader, Spline_Sans_Mono } from "next/font/google";
import "./globals.css";
import { Masthead } from "@/components/Masthead";
import { Indice } from "@/components/Indice";
import { IndiceMobile } from "@/components/IndiceMobile";

const fraunces = Fraunces({
  variable: "--font-fraunces",
  subsets: ["latin"],
  axes: ["opsz"],
});

const publicSans = Public_Sans({
  variable: "--font-public-sans",
  subsets: ["latin"],
});

const newsreader = Newsreader({
  variable: "--font-newsreader",
  subsets: ["latin"],
  style: ["normal", "italic"],
});

const splineMono = Spline_Sans_Mono({
  variable: "--font-spline-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Balcão — Diário de Dados Públicos",
  description:
    "Gateway que unifica APIs públicas brasileiras numa porta só: Câmara, Senado, Banco Central e IBGE, normalizados, com cache e busca unificada.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html
      lang="pt-BR"
      className={`${fraunces.variable} ${publicSans.variable} ${newsreader.variable} ${splineMono.variable}`}
    >
      <body className="min-h-dvh">
        <Masthead />
        <div className="mx-auto w-full max-w-310 px-4 md:px-6">
          <IndiceMobile />
          <div className="flex">
            <Indice />
            <main className="min-w-0 flex-1 py-6 md:py-10 md:pl-8">{children}</main>
          </div>
        </div>
      </body>
    </html>
  );
}
