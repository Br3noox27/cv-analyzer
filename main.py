from dotenv import load_dotenv 
load_dotenv()

import os 
import json
import anthropic 
import fitz  # PyMuPDF

from fastapi import FastAPI, File, UploadFile, Form 
from prompts import PROMPT_TECNICO, PROMPT_RH, PROMPT_JUIZ
from scraper import extrair_texto_url

app = FastAPI()
client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get('/health')
def health():
    return {'Status': 200}

@app.post('/analisar')
async def analisar(
    cv_file : UploadFile = File(...),
    job_text: str = Form(...),
):

    # Valida se é PDF
    if cv_file.content_type != 'application/pdf':
        return {'erro': 'o arquivo enviado não é um pdf'}

    # Valida tamanho — máximo 5MB
    contents = await cv_file.read()
    if len(contents) > 5 * 1024 * 1024:
        return{"erro": "PDF muito grande. Limite é 5MB."}
    
    # Valida se forneceu vaga
    if not job_text.strip():
        return {"erro": "O texto da vaga não pode estar vazio."}
    
    
    doc = fitz.open(stream=contents, filetype='pdf')
    cv_text = ""

    for page in doc: 
        cv_text += page.get_text()
    doc.close()

    # agent 1 TÉCNICO

    msg_tecnico = client.messages.create(
        model='claude-sonnet-4-6',
        max_tokens=1500,
        messages=[{"role": "user", "content": PROMPT_TECNICO.format(cv_text=cv_text, job_text=job_text)}]
    )

    raw_tecnico = msg_tecnico.content[0].text.strip()

    if raw_tecnico.startswith("```"):
        raw_tecnico = raw_tecnico.split("```")[1]
        if raw_tecnico.startswith('json'):
            raw_tecnico = raw_tecnico[4:]
        parecer_tecnico = json.loads(raw_tecnico.strip())

    msg_rh = client.messages.create(
        model='claude-sonnet-4-6',
        max_tokens=1500,
        messages=[{"role": "user", "content": PROMPT_RH.format(cv_text=cv_text, job_text=job_text)}]
    )
    raw_rh = msg_rh.content[0].text.strip()
    if raw_rh.startswith("```"):
        raw_rh = raw_rh.split("```")[1]
        if raw_rh.startswith("json"):
            raw_rh = raw_rh[4:]
    parecer_rh = json.loads(raw_rh.strip())

    # Agente 3 — Juiz
    msg_juiz = client.messages.create(
        model='claude-sonnet-4-6',
        max_tokens=2000,
        messages=[{"role": "user", "content": PROMPT_JUIZ.format(
            parecer_tecnico=json.dumps(parecer_tecnico, ensure_ascii=False),
            parecer_rh=json.dumps(parecer_rh, ensure_ascii=False),
            job_text=job_text
        )}]
    )
    raw_juiz = msg_juiz.content[0].text.strip()
    if raw_juiz.startswith("```"):
        raw_juiz = raw_juiz.split("```")[1]
        if raw_juiz.startswith("json"):
            raw_juiz = raw_juiz[4:]
    parecer_juiz = json.loads(raw_juiz.strip())

    return {
        "tecnico": parecer_tecnico,
        "rh": parecer_rh,
        "juiz": parecer_juiz
    }

