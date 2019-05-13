import pytest

import httpcore


@pytest.mark.asyncio
async def test_get(server):
    url = "http://127.0.0.1:8000/"
    async with httpcore.AsyncClient() as client:
        response = await client.get(url)
    assert response.status_code == 200
    assert response.text == "Hello, world!"


@pytest.mark.asyncio
async def test_post(server):
    url = "http://127.0.0.1:8000/"
    async with httpcore.AsyncClient() as client:
        response = await client.post(url, data=b"Hello, world!")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_stream_response(server):
    async with httpcore.AsyncClient() as client:
        response = await client.request("GET", "http://127.0.0.1:8000/", stream=True)
    assert response.status_code == 200
    body = await response.read()
    assert body == b"Hello, world!"
    assert response.content == b"Hello, world!"


@pytest.mark.asyncio
async def test_access_content_stream_response(server):
    async with httpcore.AsyncClient() as client:
        response = await client.request("GET", "http://127.0.0.1:8000/", stream=True)
    assert response.status_code == 200
    with pytest.raises(httpcore.ResponseNotRead):
        response.content


@pytest.mark.asyncio
async def test_stream_request(server):
    async def hello_world():
        yield b"Hello, "
        yield b"world!"

    async with httpcore.AsyncClient() as client:
        response = await client.request(
            "POST", "http://127.0.0.1:8000/", data=hello_world()
        )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_raise_for_status(server):
    async with httpcore.AsyncClient() as client:
        for status_code in (200, 400, 404, 500, 505):
            response = await client.request(
                "GET", f"http://127.0.0.1:8000/status/{status_code}"
            )

            if 400 <= status_code < 600:
                with pytest.raises(httpcore.exceptions.HttpError):
                    response.raise_for_status()
            else:
                assert response.raise_for_status() is None
