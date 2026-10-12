import os
import requests
from flask import Flask, render_template_string, request
from dotenv import load_dotenv
from openai import OpenAI

# Cargar variables de entorno desde .env
load_dotenv()

app = Flask(__name__)

# Cliente OpenAI (puede ser None si no hay clave válida)
api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key) if api_key and api_key.startswith("sk-") else None


HTML = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MusicIA</title>
    <style>
        body {
            margin: 0; font-family: Arial, sans-serif;
            background: #10101b; color: white;
            text-align: center; padding: 30px 18px;
        }
        h1 { font-size: 35px; color: #b69cff; }
        p { color: #b8b8c9; }
        .contenedor { max-width: 600px; margin: 45px auto; }
        input {
            box-sizing: border-box; width: 100%; padding: 16px;
            border: 1px solid #45455e; border-radius: 12px;
            background: #202033; color: white; font-size: 16px;
        }
        button {
            margin-top: 15px; padding: 15px 25px; width: 100%;
            border: none; border-radius: 12px;
            background: #8b5cf6; color: white;
            font-size: 16px; cursor: pointer;
        }
        button:hover { background: #7c4cf0; }
        .nota { margin-top: 35px; font-size: 13px; }
        .resultado {
            background: #1c1c2b; border-radius: 12px;
            padding: 15px; margin-top: 15px;
            display: flex; align-items: center; gap: 15px;
            text-align: left;
        }
        .resultado img { width: 60px; height: 60px; border-radius: 8px; }
        .resultado a { color: #b69cff; text-decoration: none; }
        .resultado h3 { margin: 0 0 5px 0; font-size: 16px; }
        .resultado p { margin: 0; font-size: 13px; }
        .interpretacion {
            background: #232336; border-radius: 10px;
            padding: 12px; margin-bottom: 20px;
            font-size: 14px; color: #cfcfe0;
        }
        .aviso {
            background: #3a1f1f; color: #ffb4b4;
            padding: 12px; border-radius: 10px;
            margin-bottom: 20px; font-size: 14px;
        }
    </style>
</head>
<body>
    <div class="contenedor">
        <h1>🎵 MusicIA</h1>
        <p>Encuentra esa canción que tienes en la cabeza.</p>

        {% if aviso %}
            <div class="aviso">⚠️ {{ aviso }}</div>
        {% endif %}

        <form action="/buscar" method="get">
            <input type="text" name="q"
                   placeholder="Describe la canción..."
                   value="{{ q or '' }}" required>
            <button type="submit">✨ Buscar canción</button>
        </form>

        {% if interpretacion %}
            <div class="interpretacion">
                <strong>🤖 Interpretación:</strong> {{ interpretacion }}
            </div>
        {% endif %}

        {% if resultados %}
            {% for r in resultados %}
                <div class="resultado">
                    <img src="{{ r.cover }}" alt="cover">
                    <div>
                        <h3>{{ r.titulo }}</h3>
                        <p>{{ r.artista }}</p>
                        <a href="{{ r.link }}" target="_blank">▶ Escuchar</a>
                    </div>
                </div>
            {% endfor %}
        {% elif resultados is not none and resultados|length == 0 %}
            <p>😔 No encontramos nada. Prueba con otra descripción.</p>
        {% endif %}

        <p class="nota">Tu próximo descubrimiento musical comienza aquí.</p>
    </div>
</body>
</html>
"""


def interpretar_con_ia(texto_usuario):
    """Usa GPT para convertir la descripción en una query de búsqueda."""
    if client is None:
        # Sin clave válida: usar el texto tal cual
        return texto_usuario
    try:
        respuesta = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content":
                    "Eres un asistente musical. El usuario describe una canción "
                    "que recuerda vagamente. Devuelve SOLO una consulta corta "
                    "(máximo 6 palabras) para buscar en una API de música. "
                    "No añadas explicaciones ni comillas."},
                {"role": "user", "content": texto_usuario}
            ],
            temperature=0.3,
            max_tokens=30,
        )
        return respuesta.choices[0].message.content.strip()
    except Exception as e:
        print("Error IA:", e)
        return texto_usuario


def buscar_en_deezer(query, limite=5):
    url = "https://api.deezer.com/search"
    try:
        r = requests.get(url, params={"q": query, "limit": limite}, timeout=10)
        data = r.json()
        return [
            {
                "titulo": item["title"],
                "artista": item["artist"]["name"],
                "cover": item["album"]["cover_medium"],
                "link": item["link"],
            }
            for item in data.get("data", [])
        ]
    except Exception as e:
        print("Error Deezer:", e)
        return []


@app.route("/")
def inicio():
    aviso = None
    if client is None:
        aviso = "No hay clave válida de OpenAI en .env — la búsqueda usará el texto directo."
    return render_template_string(
        HTML, resultados=[], q="", interpretacion=None, aviso=aviso
    )


@app.route("/buscar")
def buscar():
    q = request.args.get("q", "").strip()
    if not q:
        return render_template_string(
            HTML, resultados=[], q="", interpretacion=None, aviso=None
        )

    query_ia = interpretar_con_ia(q)
    resultados = buscar_en_deezer(query_ia)

    return render_template_string(
        HTML,
        resultados=resultados,
        q=q,
        interpretacion=query_ia,
        aviso=None,
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)