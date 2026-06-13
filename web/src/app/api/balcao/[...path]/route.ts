import { NextRequest, NextResponse } from "next/server";

const BALCAO = process.env.BALCAO_API_URL ?? "http://127.0.0.1:8000";

// proxy servidor-pra-servidor: o browser fala com o Next, o Next fala com o
// Balcao. assim nao tem CORS e a URL da API fica fora do bundle do cliente.
export async function GET(
  req: NextRequest,
  ctx: { params: Promise<{ path: string[] }> },
) {
  const { path } = await ctx.params;
  const url = `${BALCAO}/v1/${path.join("/")}${req.nextUrl.search}`;
  try {
    const upstream = await fetch(url, {
      headers: { Accept: "application/json" },
      cache: "no-store",
    });
    const corpo = await upstream.text();
    return new NextResponse(corpo, {
      status: upstream.status,
      headers: {
        "content-type":
          upstream.headers.get("content-type") ?? "application/json",
      },
    });
  } catch {
    return NextResponse.json(
      { erro: "o Balcão não respondeu — confira se a API está no ar" },
      { status: 502 },
    );
  }
}
