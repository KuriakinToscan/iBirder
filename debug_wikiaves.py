from googlesearch import search
import time

def buscar_google_robusto(especie):
    print(f"--- [BUSCA GOOGLE: {especie}] ---")
    
    # Vamos simplificar a query para ser mais natural
    query = f'site:wikiaves.com.br "{especie}"'
    
    print(f"Query: {query}")
    print("Aguardando resposta do Google...")

    try:
        # user_agent: Faz o Google pensar que é um humano no Chrome
        # stop=5: Limita aos 5 primeiros
        # pause=2.0: Espera entre requisições para não ser banido
        resultados = search(
            query, 
            num_results=5, 
            sleep_interval=2, 
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        
        lista_links = list(resultados)
        
        if not lista_links:
            print("\n[!] O Google não retornou links. Tentando sem o operador 'site:'...")
            resultados = search(f'WikiAves {especie}', num_results=5)
            lista_links = list(resultados)

        print("\nResultados encontrados:")
        print("-" * 50)
        for i, url in enumerate(lista_links, 1):
            print(f"{i}. {url}")
            
    except Exception as e:
        print(f"\nErro: {e}")

if __name__ == "__main__":
    buscar_google_robusto("Furnarius rufus")