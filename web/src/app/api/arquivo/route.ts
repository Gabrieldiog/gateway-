import { NextRequest, NextResponse } from "next/server";

// alguns órgãos servem PDF como binary/octet-stream, no iOS isso vira aba
// em branco e no Android um download que o sistema não sabe abrir. Este
// proxy corrige o Content-Type pela extensão e dá um nome de arquivo
// amigável, aí o visualizador nativo dos dois assume.
// Allowlist rígida de hosts: proxy aberto é SSRF, só passa quem conhecemos.
const HOSTS_PERMITIDOS = new Set([
  "data.queridodiario.ok.org.br",
  "querido-diario.nyc3.cdn.digitaloceanspaces.com",
]);

const TIPOS: Record<string, string> = {
  pdf: "application/pdf",
  txt: "text/plain; charset=utf-8",
  csv: "text/csv; charset=utf-8",
};

export async function GET(req: NextRequest) {
  const alvo = req.nextUrl.searchParams.get("url") ?? "";
  const nome = (req.nextUrl.searchParams.get("nome") ?? "arquivo").replace(/[^\w.\-]/g, "-");

  let url: URL;
  try {
    url = new URL(alvo);
  } catch {
    return NextResponse.json({ erro: "url inválida" }, { status: 400 });
  }
  if (url.protocol !== "https:" || !HOSTS_PERMITIDOS.has(url.hostname)) {
    return NextResponse.json({ erro: "host não permitido" }, { status: 400 });
  }

  const upstream = await fetch(url, { cache: "no-store" });
  if (!upstream.ok || !upstream.body) {
    return NextResponse.json(
      { erro: "o arquivo não respondeu na fonte" },
      { status: 502 },
    );
  }

  const extensao = url.pathname.split(".").pop()?.toLowerCase() ?? "";
  const tipo = TIPOS[extensao] ?? upstream.headers.get("content-type") ?? "application/octet-stream";
  const headers = new Headers({
    "content-type": tipo,
    // inline abre no visualizador do celular; o filename orienta o "salvar"
    "content-disposition": `inline; filename="${nome}"`,
    "x-content-type-options": "nosniff",
    "cache-control": "public, max-age=3600",
  });
  const tamanho = upstream.headers.get("content-length");
  if (tamanho) headers.set("content-length", tamanho);

  return new NextResponse(upstream.body, { status: 200, headers });
}
