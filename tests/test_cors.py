async def test_cors_libera_origem_do_allowlist(api):
    resp = await api.get("/health", headers={"Origin": "http://localhost:3000"})
    assert resp.headers.get("access-control-allow-origin") == "http://localhost:3000"


async def test_cors_preflight_get_passa_sem_gastar_balde(api):
    # o preflight (OPTIONS) tem que ser respondido pelo CORS, liberando GET
    resp = await api.options(
        "/v1/notaparana/produtos",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert resp.status_code == 200
    assert resp.headers.get("access-control-allow-origin") == "http://localhost:3000"
    assert "GET" in resp.headers.get("access-control-allow-methods", "")


async def test_cors_ignora_origem_de_fora(api):
    resp = await api.get("/health", headers={"Origin": "https://site-qualquer.example"})
    assert "access-control-allow-origin" not in resp.headers
