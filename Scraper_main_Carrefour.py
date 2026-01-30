import asyncio
import datetime
import os

import pandas as pd
from playwright.async_api import async_playwright

async def main():

    pares_urls_respuesta = []

    async with async_playwright() as p:

        print("Arrancando webdriver de Chromium para simular navegación...")
        
        browser = await p.chromium.launch()
        page = await browser.new_page()

        print("Webdriver operativo. Accediendo a https://www.carrefour.es...")

        await page.goto("https://www.carrefour.es/")

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
    _ = input("\nPulsa Enter para salir del programa")


if __name__ == "__main__":
    asyncio.run(main())
