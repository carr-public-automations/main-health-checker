import asyncio
import datetime
import os

import pandas as pd
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

async def main():

    pares_urls_respuesta = []

    async with Stealth().use_async(async_playwright()) as p:

        print("Arrancando webdriver de Chromium para simular navegación...")
        
        browser = await p.chromium.launch(headless=False)

        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )

        page = await browser.new_page()

        print("Webdriver operativo. Accediendo a https://www.carrefour.es...")

        await page.goto("https://www.carrefour.es/", wait_until="commit")

        try:
            # Esperamos a que la URL sea la definitiva o aparezca un elemento clave.
            # Cloudflare suele tardar entre 2 y 8 segundos en redirigir.
            print("Verificando paso por Cloudflare...")
            
            # Esperamos a que aparezca el selector del buscador o el logo
            # 'text="Aceptar todas"' suele ser el botón de cookies de Carrefour, buena señal de llegada.
            await page.wait_for_selector('input[type="search"], #search-input', timeout=45000)
            
            if "carrefour.es" in page.url:
                print(f"¡Éxito! URL actual: {page.url}")
                # Aquí tu lógica de empleado:
                # await page.click('text="Mi cuenta"')
            
        except Exception as e:
            print(f"Error o timeout: Posible bloqueo persistente. {e}")
            # Si se queda pillado, a veces un pantallazo ayuda a depurar:
            await page.screenshot(path="debug_cloudflare.png")

        # Usamos JavaScript para obtener todos los href de una vez.
        # Esto evita el error de "locator.get_attribute" al iterar.
        # O al menos debería...
        enlaces_datos = await page.evaluate("""() => 
            Array.from(document.querySelectorAll('a[href]'))
                .filter(a => a.href.startsWith('http') || a.getAttribute('href').startsWith('#'))
                .map(a => ({
                    url: a.href,
                    texto: a.innerText.trim() || "Sin texto visible"
                }))""")
        
        print(f"Capturadas {len(enlaces_datos)} URLs correctamente en https://www.carrefour.es. Accediendo a todas ellas...")

        for item in enlaces_datos:
            url = item['url']
            texto = item['texto']

            try:
                # Usamos un timeout corto y esperamos solo a que cargue el DOM inicial
                response = await page.goto(url, wait_until="domcontentloaded", timeout=15000)
                if response:
                    pares_urls_respuesta.append((texto, url, response.status))
                    print(f"[{response.status}] - {url}")
                else:
                    pares_urls_respuesta.append((texto, url, "SIN RESPUESTA (no es url nueva)"))
                    print(f"[SIN RESPUESTA (no es url nueva)] - {url}")
            except Exception as e:
                pares_urls_respuesta.append((texto, url, str(e)))
                print(f"[ERROR] en {url}: {str(e)}...")

        await browser.close()

    tabla_resultados = pd.DataFrame({"Texto clickable": [texto for texto, url, respuesta in pares_urls_respuesta],
                                     "URL": [url for texto, url, respuesta in pares_urls_respuesta],
                                     "Respuesta": [respuesta for texto, url, respuesta in pares_urls_respuesta]})

    fecha_y_hora = datetime.datetime.now().strftime("%Y_%m_%d-%H_%M_%S")
    nombre_archivo = f"{fecha_y_hora} Resultados scraping main carrefour.xlsx"
    tabla_resultados.to_excel(nombre_archivo, index=False)

    print(f"\n¡Terminado! El archivo {os.path.abspath(nombre_archivo)} tiene los resultados.")
    #_ = input("\nPulsa Enter para salir del programa")


asyncio.run(main())
