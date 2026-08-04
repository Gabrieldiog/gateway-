# Publicar o Balcão

Tudo em plano **gratuito**. A arquitetura separa as duas metades:

```
  navegador
     │
     ▼
  Netlify  ──(proxy server-to-server, BALCAO_API_URL)──►  Render
  (front Next.js, web/)                                   (backend FastAPI, Dockerfile)
                                                              ▲
                                                    UptimeRobot bate /health
                                                    a cada 5 min (não deixa dormir)
```

O front nunca chama o backend direto do navegador: ele passa pelo proxy
`web/src/app/api/balcao/[...path]/route.ts`, que lê a env `BALCAO_API_URL`.
Por isso **não há CORS** entre os dois, e a URL do backend não precisa
ser pública/adivinhável.

---

## 1. Backend no Render (Blueprint)

O `render.yaml` na raiz já é o blueprint (runtime Docker, plano free,
healthcheck em `/health`).

1. Crie conta em <https://render.com> (não pede cartão no free).
2. **New +** → **Blueprint** → conecte o repositório `gateway-` → o Render
   lê o `render.yaml` sozinho e cria o serviço `balcao-api`.
3. As chaves opcionais ficam como *secret* (a aba mostra `sync: false`):
   `TRANSPARENCIA_API_KEY`, `BRAPI_TOKEN`, `DATAJUD_API_KEY`, `API_KEYS`.
   Pode deixar **todas em branco**, a app sobe sem nenhuma (as fontes que
   dependem de chave só ficam desligadas). Preencha depois se quiser.
4. Espere o primeiro build/deploy. Quando ficar **Live**, copie a URL,
   algo como `https://balcao-api.onrender.com`.
5. Teste: abra `https://<sua-url>/health` (deve responder ok) e
   `https://<sua-url>/scalar` (a referência interativa da API).

> **Cold start:** o free hiberna após ~15 min sem tráfego e leva ~50s pra
> acordar. O pinger do passo 3 resolve isso.

---

## 2. Frontend na Netlify

O `netlify.toml` na raiz já aponta `base = "web"`, Node 20, build com pnpm
e o runtime do Next.

1. Crie conta em <https://netlify.com>.
2. **Add new site** → **Import an existing project** → conecte o repo. Ela
   lê o `netlify.toml` e já sabe buildar de `web/`.
3. **Antes de publicar** (ou logo depois, e re-deploy): em
   **Site configuration → Environment variables**, adicione:
   - `BALCAO_API_URL` = a URL do Render do passo 1
     (ex.: `https://balcao-api.onrender.com`, **sem** barra no fim).
4. **Deploy**. Quando terminar, abra o site; cada caderno deve puxar dado
   real (o proxy → Render → API oficial).

> Se você configurar a env **depois** do primeiro deploy, dispare um
> **Trigger deploy → Deploy site** pra ela valer.

---

## 3. Pinger (mantém o backend acordado)

Sem isso, o backend do Render dorme e a primeira visita do dia trava ~50s.

1. Crie conta em <https://uptimerobot.com> (free).
2. **Add New Monitor** → tipo **HTTP(s)** → URL
   `https://<sua-url-do-render>/health` → intervalo **5 minutos**.
3. Pronto: ele bate de 5 em 5 min, o serviço nunca hiberna e o cache fica
   quente. Cabe folgado nas 750h/mês do free.

---

## Avisos honestos

- **Sem disco persistente no free.** Os conectores *file-backed* (Segurança
  ~35 MB, TSE) baixam o arquivo na primeira chamada e guardam em memória/tmp;
  a cada cold start, re-baixam. Segurança cabe (pico ~110 MB de RAM).
- **TSE é pesado** (zip de 390 MB a 1,4 GB, streaming pra disco): pode
  estourar o disco/RAM do Render free. Se for expor, restrinja ou deixe o
  conector `tse` desligado; as outras 32 fontes rodam de boa.
- **Segredos nunca no Git.** As chaves vão só nos painéis (Render secrets /
  Netlify env). O `.env` está no `.gitignore`.
- É um **projeto de portfólio**, servido "como está"; a página `/termos`
  deixa isso explícito.
