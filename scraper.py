import httpx 
from bs4 import BeautifulSoup

async def extrair_texto_url(url:str) -> str: 
    headers = { 
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
    }

    async with httpx.AsyncClient(follow_redirects=True, timeout=15) as client: 
        response = await client.get(url, headers=headers)
        response.raise_for_status()

    soup = BeautifulSoup(response.text, 'html.parser')

    for tag in soup(['script', 'style', 'nav', 'footer', 'header']):
        tag.decompose()

    texto = soup.get_text(separator="\n")
    limpo = "\n".join(line.strip() for line in texto.splitlines() if line.strip())
    return limpo[:8000]

